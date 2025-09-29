import socket
import struct
import json
import threading
import time
from datetime import datetime
import argparse

# --- 编解码函数 ---
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


# --- 客户端类 ---
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
        # 登录
        send_json(self.sock, {"type": "HELLO", "nick": self.nick})
        print(f"[info] connected to {self.host}:{self.port} as '{self.nick}'")

    def close(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass

    # 接收线程
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
                else:
                    print(f"[debug] {msg}")
        except Exception as e:
            if self.running:
                print(f"[warn] connection lost: {e}")
            self.running = False

    # 心跳线程
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

    # 命令处理
    def handle_command(self, line: str):
        if line.startswith("/join "):
            room = line.split(" ", 1)[1].strip()
            send_json(self.sock, {"type": "JOIN", "room": room})
            self.room = room
        elif line.startswith("/msg "):
            text = line.split(" ", 1)[1]
            if not self.room:
                print("[error] 请先 /join <room>")
                return
            send_json(self.sock, {"type": "MSG", "room": self.room, "text": text})
        elif line.strip() == "/leave":
            send_json(self.sock, {"type": "LEAVE"})
            self.room = None
        elif line.strip() == "/quit":
            send_json(self.sock, {"type": "QUIT"})
            self.close()
            print("Bye!")
        else:
            print("可用命令：/join <room> | /msg <text> | /leave | /quit")

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


# --- 启动入口 ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SimpleChat Client")
    parser.add_argument("--host", default="127.0.0.1", help="服务器地址")
    parser.add_argument("--port", type=int, default=9000, help="服务器端口")
    parser.add_argument("--nick", default="hsk", help="客户端昵称")
    args = parser.parse_args()

    client = ChatClient(args.host, args.port, args.nick)
    client.run()
