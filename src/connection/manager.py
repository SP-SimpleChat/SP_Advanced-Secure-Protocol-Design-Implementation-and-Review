
import socket
import threading
import time
from typing import Callable, Optional, Any
from .protocol import encode_message, try_decode_from_buffer, ProtocolError
from .heartbeat import Heartbeat

class ConnectionManager:
    """TCP + length-prefixed JSON transport with heartbeat & auto-reconnect.

    Public callbacks (set as attributes or via constructor):
      - on_connect(): called after successful HELLO handshake send
      - on_message(msg: dict): called for every received server message
      - on_disconnect(reason: str): called when connection drops
      - on_error(err: Exception): called for unexpected exceptions

    Usage:
        cm = ConnectionManager(host, port, nickname, on_message=print)
        cm.connect()
        cm.start_heartbeat()
        cm.join_room("lobby")
        cm.send_text("hi")

    Threading model:
      - A single background thread reads from the socket and decodes messages.
      - Heartbeat runs in another background thread.
      - All callbacks are invoked on the receiver thread context.
    """

    def __init__(
        self,
        host: str,
        port: int,
        nickname: str,
        *,
        on_connect: Optional[Callable[[], None]] = None,
        on_message: Optional[Callable[[dict], None]] = None,
        on_disconnect: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        socket_timeout: float = 20.0,
        reconnect: bool = True,
        reconnect_backoff: tuple = (1, 2, 4, 8, 15),
        heartbeat_interval: float = 10.0,
        heartbeat_timeout: float = 25.0,
    ):
        self.host = host
        self.port = port
        self.nickname = nickname
        self.on_connect = on_connect
        self.on_message = on_message
        self.on_disconnect = on_disconnect
        self.on_error = on_error

        self._sock: Optional[socket.socket] = None
        self._recv_thr: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._buffer = bytearray()
        self._lock = threading.Lock()

        self._socket_timeout = socket_timeout
        self._reconnect_enabled = reconnect
        self._backoff = reconnect_backoff

        # heartbeat
        self._hb = Heartbeat(
            send_ping=self._send_ping,
            interval=heartbeat_interval,
            timeout=heartbeat_timeout,
            on_timeout=self._on_heartbeat_timeout,
        )

    # ===== high-level API =====
    def connect(self):
        """Open socket, send HELLO handshake, start receiver thread."""
        self._open_socket()
        self._running.set()
        self._recv_thr = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thr.start()
        # HELLO handshake
        self.send_json({"type": "HELLO", "nickname": self.nickname})
        if self.on_connect:
            try:
                self.on_connect()
            except Exception as e:
                self._report_error(e)

    def start_heartbeat(self):
        self._hb.start()

    def stop(self):
        """Graceful shutdown."""
        self._hb.stop()
        self._running.clear()
        with self._lock:
            if self._sock:
                try:
                    self._sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    self._sock.close()
                finally:
                    self._sock = None
        if self._recv_thr and self._recv_thr.is_alive():
            self._recv_thr.join(timeout=0.5)

    # Convenience protocol helpers
    def join_room(self, room: str):
        self.send_json({"type": "JOIN", "room": room})

    def leave_room(self, room: Optional[str] = None):
        payload = {"type": "LEAVE"}
        if room:
            payload["room"] = room
        self.send_json(payload)

    def send_text(self, content: str, room: Optional[str] = None):
        payload = {"type": "MSG", "content": content}
        if room:
            payload["room"] = room
        self.send_json(payload)

    def send_json(self, data: dict):
        """Thread-safe send."""
        blob = encode_message(data)
        with self._lock:
            if not self._sock:
                raise ConnectionError("Socket is not connected")
            self._sock.sendall(blob)

    # ===== internals =====
    def _open_socket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self._socket_timeout)
        s.connect((self.host, self.port))
        # Optional: disable Nagle for lower latency chat
        try:
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except Exception:
            pass
        self._sock = s

    def _recv_loop(self):
        reason = "remote-closed"
        try:
            while self._running.is_set():
                try:
                    chunk = self._sock.recv(4096) if self._sock else b""
                except socket.timeout:
                    # timeout is fine; loop will continue to allow heartbeat
                    continue
                except Exception as e:
                    reason = f"socket-error: {e}"
                    break

                if not chunk:
                    # peer closed
                    break

                self._buffer.extend(chunk)
                while True:
                    try:
                        msg = try_decode_from_buffer(self._buffer)
                    except ProtocolError as e:
                        self._report_error(e)
                        reason = f"protocol-error: {e}"
                        self._running.clear()
                        break
                    if msg is None:
                        break
                    self._dispatch_message(msg)
                # continue outer loop
        finally:
            self._running.clear()
            self._hb.stop()
            self._cleanup_socket()
            if self.on_disconnect:
                try:
                    self.on_disconnect(reason)
                except Exception as e:
                    self._report_error(e)
            # auto-reconnect
            if self._reconnect_enabled:
                self._reconnect_loop()

    def _cleanup_socket(self):
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                finally:
                    self._sock = None

    def _dispatch_message(self, msg: dict):
        mtype = msg.get("type")
        if mtype == "PONG" or mtype == "PING":
            # accept server PING as well; reply with PONG if needed
            if mtype == "PING":
                try:
                    self.send_json({"type": "PONG"})
                except Exception as e:
                    self._report_error(e)
            self._hb.mark_pong()
            return
        if self.on_message:
            try:
                self.on_message(msg)
            except Exception as e:
                self._report_error(e)

    def _send_ping(self):
        try:
            self.send_json({"type": "PING"})
        except Exception as e:
            self._report_error(e)

    def _on_heartbeat_timeout(self):
        # If heartbeat times out, force-close to trigger reconnect.
        self._running.clear()
        self._cleanup_socket()

    def _reconnect_loop(self):
        for delay in self._backoff:
            try:
                time.sleep(delay)
                self._open_socket()
                self._running.set()
                self._hb.start()
                # new thread for receiving
                self._recv_thr = threading.Thread(target=self._recv_loop, daemon=True)
                self._recv_thr.start()
                # re-send HELLO (server should re-auth us)
                self.send_json({"type": "HELLO", "nickname": self.nickname})
                if self.on_connect:
                    try:
                        self.on_connect()
                    except Exception as e:
                        self._report_error(e)
                return
            except Exception as e:
                self._report_error(e)
                continue
        # give up
        if self.on_disconnect:
            try:
                self.on_disconnect("reconnect-failed")
            except Exception as e:
                self._report_error(e)

    def _report_error(self, e: Exception):
        if self.on_error:
            try:
                self.on_error(e)
            except Exception:
                pass
