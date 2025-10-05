from __future__ import annotations
import base64, hashlib, os, time, uuid 
from pathlib import Path 
from typing import Callable, Dict, Optional
import hmac
from Crypto.Cipher import AES 

CHUNK_SIZE = 32 * 1024 # 32Kib plaintext per chunk 
AEAD_NAME = "AES-256-EAX" #authenticared encryption 
KDF_NAME = "HKDF-SHA256" #per file encryption key 

# in memory transfer state
_SEND: Dict[str, dict] = {} 
_RECV: Dict[str, dict] = {}

# Unix timestamp 
def _ts_ms() -> int:
    return int(time.time() * 1000 )

# convert raw bytes into URL-safe base 64 
def _b64url_nopad(b: bytes) -> str: 
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")

# converts the base64 text back to original bytes   
def _b64url_to_bytes(s: str) -> bytes:
    pad = (-len(s)) % 4
    return base64.urlsafe_b64decode(s+ ("=" * pad))

# Making sure the file is safe 
def _sanitize_name(name: str) -> str: 
    name = name.replace("\\", "/").split("/")[-1]
    bad = set('<>:"|?*')
    s = "".join(c for c in name if 32 <= ord(c) != 127 and c not in bad).strip()
    return (s or "file")[:255]

#Reads file and computes its SHA-256 hash 
def _sha256_file(path: Path) -> str: 
    h = hashlib.sha256()
    with path.open("rb") as f :
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest() 

# New secret key using HKDF-based key derivation function with SHA-256 
def _hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, out_len: int) -> bytes:
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    okm = b""
    t = b""
    counter = 1
    while len(okm) < out_len:
        t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
        okm += t 
        counter += 1
    return okm[:out_len]

# --- Sender --- 

# Gets file info, creates and announces a new file transfer 
def start_send(
        path: str,
        to: str,
        mode: str,
        send_json: Callable[[dict], None],
        from_user: str,
        session_key: bytes | None = None,
        signer: Optional[Callable[[dict], str]] = None, 
) -> str:
    
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(path)
    
    file_id = str(uuid.uuid4())
    size = p.stat().st_size
    sha_hex = _sha256_file(p)
    file_nonce = os.urandom(16)

    _SEND[file_id] = {
        "path": str(p),
        "fh": p.open("rb"),
        "size":size,
        "name":p.name,
        "sha256": sha_hex,
        "index": 0,
        "to":to,
        "mode":mode,
        "from": from_user,
        "file_nonce": file_nonce,
        "session_key": session_key,
    }

    start_msg = {
        "type": "FILE_START",
        "from": from_user,
        "to": to,
        "ts": _ts_ms(),
        "payload": {
            "file_id": file_id,
            "name": p.name,
            "size": size,
            "sha256": sha_hex,
            "mode": mode,
            "aead": AEAD_NAME,
            "kdf" : KDF_NAME,
            "file_nonce_b64": _b64url_nopad(file_nonce),
        },
        "sig": "",
    }
    if signer:
        start_msg["sig"] = signer(start_msg)

    
    send_json(start_msg)
    return file_id

# The file are cut done into smaller parts so this function is just for 
# reading the next chunk and encrupts it and return a FILE_CHUNK message 
def next_chunk(file_id: str) -> tuple[dict, int] | None:
    st = _SEND.get(file_id)
    if not st: 
        return None
    data = st["fh"].read(CHUNK_SIZE)
    if not data:
        return None 
    n = len(data)
    
    idx = st["index"]; st["index"] += 1
    sess = st["session_key"] or b"\x00" * 32 
    file_key = _hkdf_sha256(sess, st["file_nonce"], b"file-key", 32)
    nonce = _hkdf_sha256(file_key, st["file_nonce"], f"chunk-nonce:{idx}".encode(), 16)

    cipher = AES.new(file_key, AES.MODE_EAX, nonce=nonce)
    ct = cipher.encrypt(data)
    tag = cipher.digest()

    return {
        "type": "FILE_CHUNK",
        "from": st["from"],
        "to": st["to"],
        "ts": _ts_ms(),
        "payload": {
            "file_id": file_id,
            "index": idx,
            "nonce_b64": _b64url_nopad(nonce),
            "ciphertext": _b64url_nopad(ct),
            "tag_b64": _b64url_nopad(tag),
        }, 
        "sig": "",
    }, n 

# sends the end signal for a file transfer 
def finish_send(file_id: str) -> dict:
    st = _SEND.pop(file_id, None)
    if not st:
        raise KeyError(f"Unknown file_id {file_id}")
    try:
        st["fh"].close()
    except Exception:
        pass
    return{
        "type": "FILE_END",
        "from": st["from"],
        "to": st["to"],
        "ts": _ts_ms(),
        "payload": {"file_id": file_id},
        "sig": "", 
    }

# -- For Receiver -- 

#Getting receiver ready for the incoming file 
def ingest_start(msg: dict, save_dir: str) -> int:
    pl = msg.get("payload", {})
    fid = pl["file_id"]
    name = _sanitize_name(pl.get("name","file"))
    size = int(pl.get("size", 0))
    sha_hex = (pl.get("sha256") or "").lower()

    file_nonce_b64 = pl.get("file_nonce_b64", "")
    pad = (-len(file_nonce_b64)) % 4
    file_nonce = base64.urlsafe_b64decode(file_nonce_b64 + ("=" * pad ))
    session_key = b"\x00" * 32  # This need to be replace 

    Path(save_dir).mkdir(parents=True, exist_ok=True)
    tmp = Path(save_dir) / f"{fid}_{name}.part"
    fh = tmp.open("wb")

    _RECV[fid] = {
        "path_tmp": str(tmp),
        "path_final": str(Path(save_dir) / name),
        "fh": fh,
        "size": size,
        "sha256": sha_hex,
        "seen": 0,
        "expected_index": 0, 

        "hasher" : hashlib.sha256(),
        "file_nonce": file_nonce,
        "session_key": session_key,
    }
    return size

# breaking the file into chunk including decodes, decrypts and verifies 
def ingest_chunk(msg: dict) -> int:
    pl = msg.get("payload", {})
    fid = pl["file_id"]
    st = _RECV.get(fid)
    if not st:
        return 0
    
    idx = int(pl["index"])
    if idx != st["expected_index"]:
        return 0
    
    sess = st.get("session_key", b"\x00" * 32)
    file_nonce = st.get("file_nonce")
    if file_nonce is None:
        pass

    file_key = _hkdf_sha256(sess, file_nonce, b"file-key", 32)
    nonce = _b64url_to_bytes(pl["nonce_b64"])
    ct = _b64url_to_bytes(pl["ciphertext"])
    tag = _b64url_to_bytes(pl["tag_b64"])

    cipher = AES.new(file_key, AES.MODE_EAX, nonce=nonce)
    try:
        pt = cipher.decrypt_and_verify(ct, tag)
    except ValueError:
        raise ValueError("INTEGRITY_FAIL: per-chunk tag is mismatch")
    
    st["fh"].write(pt)
    st["seen"] += len(pt)
    st["hasher"].update(pt) if "hasher" in st else None 
    st["expected_index"] += 1 
    return len(pt)

# Finalise the recieved file and show the file save path 
def ingest_end(msg: dict) -> str:
    pl = msg.get("payload", {})
    fid = pl["file_id"]
    st = _RECV.pop(fid, None)
    if not st: 
        raise KeyError(f"Unknown file_id: {fid}")
    try:
        st["fh"].flush(); st["fh"].close()
    finally:
        pass

    if st["seen"] != st["size"]:
        raise ValueError(f"TRUNCATED_TRANSFER: expected {st['size']} got {st['seen']}")
    
    if "hasher" not in st:
        st["hasher"] = hashlib.sha256(Path(st["path_tmp"]).read_bytes())
    if st["hasher"].hexdigest().lower() != st["sha256"]:
        raise ValueError ("INTEGRITY_FAIL: file sha256 mismatch")
    
    tmp = Path(st["path_tmp"]); final = Path(st["path_final"])
    if final.exists():
        stem, ext = final.stem, final.suffix
        final = final.with_name(f"{stem}.{uuid.uuid4().hex[:6]}{ext}")
    tmp.rename(final)
    return str(final)

__all__ = ["start_send", "ingest_start", "next_chunk", "ingest_chunk", "finish_send", "ingest_end"]

