import socket
import struct
import json
import threading
import time
from datetime import datetime
import argparse
import sys, os 
import shlex
from tqdm import tqdm  # pip install pycryptodome tqdm

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.connection.manager import ConnectionManager
from src.file_transfer import start_send, next_chunk, finish_send, ingest_start, ingest_chunk, ingest_end

# --- Encoding / decoding helpers ---
def send_json(sock: socket.socket, obj: dict):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    header = struct.pack(">I", len(data))
    sock.sendall(header + data)

def recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("server closed")
        buf += chunk
    return buf

def recv_json(sock: socket.socket) -> dict:
    raw_len = recv_exact(sock, 4)
    (length,) = struct.unpack(">I", raw_len)
    body = recv_exact(sock, length)
    return json.loads(body.decode("utf-8"))

class ChatClient:
    def __init__(self, host, port, nickname, heartbeat_interval=20):
        self.host = host
        self.port = port
        self.nick = nickname
        # -- This is for preventing auto download of file 
        self.auto_accept = False 
        self.download_dir = "./downloads"
        os.makedirs(self.download_dir, exist_ok=True)
        self.__pending_files = {} 
        self.__chunk_buf = {} 
        self.__end_msg_buf = {}  
        self._active_files = set()
        self._recv_pbar = None
        self.sock = None
        self.running = False
        self.room = None
        self.last_pong = time.time()
        self.heartbeat_interval = heartbeat_interval


    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.running = True
        send_json(self.sock, {"type": "HELLO", "nick": self.nick})
        print(f"[info] connected to {self.host}:{self.port} as '{self.nick}'")

    def close(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass

    def receiver_loop(self):
        try:
            while self.running:
                msg = recv_json(self.sock)
                mtype = msg.get("type")
                if mtype == "MSG":
                    room = msg.get("room", "?")
                    nick = msg.get("nick", "?")
                    text = msg.get("text", "")
                    ts = datetime.now().strftime("%H:%M:%S")
                    print(f"[{room}] {ts} {nick}: {text}")
                elif mtype == "INFO":
                    print(f"[info] {msg.get('text','')}")
                elif mtype == "ERROR":
                    print(f"[error] {msg.get('code','')} {msg.get('text','')}")
                elif mtype == "PONG":
                    self.last_pong = time.time()

                # ---- NEW: WHO response ----
                elif mtype == "WHO_LIST":
                    r = msg.get("room", self.room or "?")
                    members = msg.get("members", [])
                    print(f"[info] Online members in '{r}': {', '.join(members) if members else '(empty)'}")
                # ---------------------------

                # --- File transfer receive path ---
                elif mtype == "FILE_START":
                    fid = msg.get("payload", {}).get("file_id")
                    if not fid:
                        print("[warn] FILE_START without file_id - ignored")
                        continue
                    total = int(msg.get("payload", {}).get("size", 0) or 0)
                    if self.auto_accept:
                        os.makedirs(self.download_dir, exist_ok=True)
                        total = ingest_start(msg, self.download_dir )
                        self._active_files.add(fid)
                        if self._recv_pbar: self._recv_pbar.close(); self._recv_pbar = None
                        self._recv_pbar = tqdm(total=total, unit="B", unit_scale=True, desc="receiving")
                        print(f"[info] Ready to receive file (auto-accepted) id={fid}")
                    else:
                        self.__pending_files[fid] = msg
                        print(f"[info] Incoming file id={fid}, size={total}B. Use /accept {fid} or /reject {fid}")
                elif mtype == "FILE_CHUNK":
                    fid = msg.get("payload", {}).get("file_id")
                    if fid in self._active_files: #this will ignore the chunks as unaccepted transfer 
                        n = ingest_chunk(msg)
                    if fid in self._active_files:
                        n = ingest_chunk(msg)
                        if self._recv_pbar:self._recv_pbar.update(n)
                    elif fid in self.__pending_files:
                        self.__chunk_buf.setdefault(fid, []).append(msg)
                elif mtype == "FILE_END":
                    fid = msg.get("payload", {}).get("file_id")
                    if fid not in self._active_files:
                        if fid in self.__pending_files:
                            self.__end_msg_buf[fid] = msg 
                        continue
                    path = ingest_end(msg)

                    if self._recv_pbar:
                        self._recv_pbar.close(); self._recv_pbar = None
                    self._active_files.discard(fid)
                    self.__pending_files.pop(fid, None)
                    print(f"[info] file saved to {path}")
        except Exception as e:
            if getattr(self, "_recv_pbar", None):
                self._recv_pbar.close()
                self._recv_pbar = None
            if self.running:
                print(f"[warn] connection lost: {e}")
            self.running = False

    def heartbeat_loop(self):
        try:
            while self.running:
                time.sleep(self.heartbeat_interval)
                try:
                    send_json(self.sock, {"type": "PING"})
                except Exception:
                    print("[warn] heartbeat send failed; disconnect")
                    self.running = False
                    break
                if time.time() - self.last_pong > 60:
                    print("[warn] heartbeat timeout; disconnect")
                    self.running = False
                    break
        except Exception:
            pass

    def handle_command(self, line: str):
        if line.startswith("/join "):
            room = line.split(" ", 1)[1].strip()
            send_json(self.sock, {"type": "JOIN", "room": room})
            self.room = room
        elif line.startswith("/msg "):
            text = line.split(" ", 1)[1]
            if not self.room:
                print("[error] Please enter a room using:  /join <room>")
                return
            send_json(self.sock, {"type": "MSG", "room": self.room, "text": text})
        elif line.strip() == "/who":
            # ask server for current room members
            send_json(self.sock, {"type": "WHO", "room": self.room})
        elif line.strip() == "/leave":
            send_json(self.sock, {"type": "LEAVE"})
            self.room = None
        elif line.strip() == "/quit":
            send_json(self.sock, {"type": "QUIT"})
            self.close()
            print("Bye!")
        # ---- File sending path ----
        elif line.startswith("/send"):
            try:
                args = shlex.split(line)
                if len(args) < 2:
                    print("[error] usage: /send <path> | /send dm:<nick> <path>")
                    return
                if len(args) >= 3 and args[1].startswith("dm:"):
                    to = args[1][3:]; mode = "dm"; path = args[2]
                else:
                    if not self.room:
                        print("[error] Please use /join to join a room or use dm:<nick>")
                        return
                    to = self.room; mode = "public"; path = args[1]
                fid = start_send(
                    path=path,
                    to=to,
                    mode=mode,
                    send_json=lambda obj: send_json(self.sock, obj),
                    from_user=self.nick,
                    session_key=None
                )
                sent = 0
                pbar = tqdm(total=os.path.getsize(path), unit="B", unit_scale=True, desc="sending")
                time.sleep(getattr(self, "send_wait", 2.0)) 
                while True:
                    nxt = next_chunk(fid)
                    if nxt is None:
                        break
                    chunk_msg, nbytes = nxt
                    send_json(self.sock, chunk_msg)
                    sent += nbytes
                    pbar.update(nbytes)
                pbar.close()
                send_json(self.sock, finish_send(fid))
                print(f"[info] file transfer finished (sent {sent} bytes)")
            except Exception as e:
                print(f"[error] File sending failed: {e}")

        # ----- NEW update for the /accept command because auto save a file was not a good idea 
        elif line.startswith("/accept"):
            fid = line[7:].strip()
            msg = self.__pending_files.pop(fid, None)
            if not msg:
                print("[error] Unknown file_id"); return
            if int(msg.get("payload", {}).get("size", 0)) > 25 * 1024 * 1024 : #25MB 
                print("[warn] Too large, reject or start with --auto-accept to override"); return 
            os.makedirs(self.download_dir, exist_ok=True)  
            total = ingest_start(msg, self.download_dir)
            self._active_files.add(fid)
            self._recv_pbar = tqdm(total=total, unit="B", unit_scale=True, desc="receiving")
            
            for ch in self.__chunk_buf.pop(fid, []):
                n = ingest_chunk(ch)
                if self._recv_pbar: self._recv_pbar.update(n)
            
            end_msg = self.__end_msg_buf.pop(fid, None)

             # if END already arrived, finalize now
            if end_msg:
                path = ingest_end(end_msg)
                if self._recv_pbar:
                    self._recv_pbar.close(); self._recv_pbar = None
                self._active_files.discard(fid)
                print(f"[info] file saved to {path}")
                return

            print(f"[info] Accepted file {fid}")
        
        elif line.startswith("/reject"):
            fid = line[7:].strip()
            self.__pending_files.pop(fid, None)
            print(f"[info] Rejected file {fid}")
        else:
            print("Available: /join <room> | /who | /msg <text> | /send <path> | /accept <file_id> | /reject <file_id> | /leave | /quit")

    def run(self):
        try:
            self.connect()
            rt = threading.Thread(target=self.receiver_loop, daemon=True)
            ht = threading.Thread(target=self.heartbeat_loop, daemon=True)
            rt.start(); ht.start()

            while self.running:
                try:
                    line = input().strip()
                except (EOFError, KeyboardInterrupt):
                    line = "/quit"
                if not self.running:
                    break
                self.handle_command(line)
        finally:
            self.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SimpleChat Client")
    parser.add_argument("--host", default="127.0.0.1", help="Server IP address")
    parser.add_argument("--port", type=int, default=9000, help="Server port")
    parser.add_argument("--nick", default="hsk", help="Client nickname")
    parser.add_argument("--auto-accept", action="store_true", help="Auto-accept incoming files (unsafe; off by default)")
    parser.add_argument("--send-wait", type=float, default=2.0, help="Seconds to wait after FILE_START before sending chunks")
    args = parser.parse_args()

    client = ChatClient(args.host, args.port, args.nick)
    client.auto_accept = args.auto_accept 
    client.send_wait = args.send_wait 
    client.run()
