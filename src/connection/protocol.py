
import json
import struct
from typing import Tuple, Optional, List

HEADER_FMT = "!I"  # 4-byte big-endian unsigned int
HEADER_SIZE = struct.calcsize(HEADER_FMT)

class ProtocolError(Exception):
    pass

def encode_message(message: dict) -> bytes:
    """Encode a dict as length-prefixed JSON bytes."""
    try:
        raw = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as e:
        raise ProtocolError(f"JSON encode failed: {e}") from e
    length = struct.pack(HEADER_FMT, len(raw))
    return length + raw

def try_decode_from_buffer(buffer: bytearray) -> Optional[dict]:
    """Try decoding a single message from the buffer.
    Returns the decoded dict and mutates the buffer to drop consumed bytes.
    If not enough data, returns None and leaves buffer intact.
    """
    if len(buffer) < HEADER_SIZE:
        return None
    msg_len = struct.unpack(HEADER_FMT, buffer[:HEADER_SIZE])[0]
    if len(buffer) < HEADER_SIZE + msg_len:
        return None
    payload = bytes(buffer[HEADER_SIZE:HEADER_SIZE+msg_len])
    del buffer[:HEADER_SIZE+msg_len]
    try:
        return json.loads(payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ProtocolError(f"JSON decode failed: {e}") from e
