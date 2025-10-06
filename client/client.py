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
                    total = ingest_start(msg, "./downloads")
                    self._recv_pbar = tqdm(total=total, unit="B", unit_scale=True, desc="receiving")
                    print("[info] Ready to receive file")
                elif mtype == "FILE_CHUNK":
                    try:
                        n = ingest_chunk(msg)
                        if hasattr(self, "_recv_pbar") and self._recv_pbar:
                            self._recv_pbar.update(n)
                    except Exception as e:
                        print(f"[error] file chunk error: {e}")
                elif mtype == "FILE_END":
                    try:
                        path = ingest_end(msg)
                        if hasattr(self, "_recv_pbar") and self._recv_pbar:
                            self._recv_pbar.close()
                            self._recv_pbar = None
                        print(f"[info] file saved to {path}")
                    except Exception as e:
                        print(f"[error] file finalize error: {e}")
                else:
                    print(f"[debug] {msg}")
        except Exception as e:
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
                print("[info] file transfer finished (sent)")
            except Exception as e:
                print(f"[error] File sending failed: {e}")
        else:
            print("Available: /join <room> | /who | /msg <text> | /send <path> | /send dm:<nick> <path> | /leave | /quit")

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
    args = parser.parse_args()

    client = ChatClient(args.host, args.port, args.nick)
    client.run()
