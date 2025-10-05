
import threading
import time
from typing import Callable, Optional

class Heartbeat:
    """A lightweight heartbeat helper that periodically calls send_ping()
    and tracks the last_pong timestamp. If timeout exceeded, fires on_timeout.
    """
    def __init__(
        self,
        send_ping: Callable[[], None],
        get_now: Callable[[], float] = time.time,
        interval: float = 10.0,
        timeout: float = 25.0,
        on_timeout: Optional[Callable[[], None]] = None,
    ):
        self._send_ping = send_ping
        self._now = get_now
        self.interval = interval
        self.timeout = timeout
        self.on_timeout = on_timeout
        self._last_pong = self._now()
        self._thr: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def mark_pong(self):
        self._last_pong = self._now()

    def start(self):
        if self._thr and self._thr.is_alive():
            return
        self._stop.clear()
        self._thr = threading.Thread(target=self._run, daemon=True)
        self._thr.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        next_tick = self._now()
        while not self._stop.is_set():
            now = self._now()
            if now >= next_tick:
                try:
                    self._send_ping()
                except Exception:
                    # Let connection manager handle actual exceptions/logging
                    pass
                next_tick = now + self.interval
            # timeout check
            if (now - self._last_pong) > self.timeout:
                if self.on_timeout:
                    try:
                        self.on_timeout()
                    finally:
                        # Avoid storm; wait a bit before re-check
                        self._last_pong = now
                else:
                    self._last_pong = now
            self._stop.wait(0.2)
