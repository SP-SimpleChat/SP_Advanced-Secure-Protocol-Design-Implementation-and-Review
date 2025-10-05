import socket, struct, json, threading

# -------------------------------------------------------------------------
# NOTE (Deliberate Vulnerability - For Coursework Peer Review)
#
# This file intentionally contains an educational vulnerability
# (Room Authorization Missing) for peer review in the Secure Programming course.
#
# Location: The handler for JOIN requests has been replaced by
# handle_join_vuln(...), which allows clients to join any room without
# performing ACL/password/session authorization checks.
#
# Purpose: To help peer reviewers identify and report this logic flaw
# through code inspection or controlled testing
# (see VULN_REPORT_TEMPLATE.md in the repository root).
#
# Security Warning:
# This vulnerability is for classroom demonstration only.
# Do NOT perform any unauthorized scans or attacks outside
# a controlled local or lab environment.
# -------------------------------------------------------------------------

nick_to_conn = {}
conn_to_nick = {}
rooms = {}
lock = threading.Lock()

def send_json(sock, obj):
    data = json.dumps(obj).encode()
    try:
        sock.sendall(struct.pack(">I", len(data)) + data)
    except Exception:
        pass

def recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        c = sock.recv(n - len(buf))
        if not c:
            raise ConnectionError()
        buf += c
    return buf

def recv_json(sock):
    l = struct.unpack(">I", recv_exact(sock, 4))[0]
    return json.loads(recv_exact(sock, l).decode())

def join_room(conn, room):
    """Move the connection to the specified room (remove from previous if any)."""
    for r, members in list(rooms.items()):
        if conn in members:
            members.remove(conn)
            if not members:
                del rooms[r]
    rooms.setdefault(room, set()).add(conn)

def broadcast(room, payload, exclude=None):
    """Send a message to all members in the given room."""
    for c in list(rooms.get(room, [])):
        if c is exclude:
            continue
        try:
            send_json(c, payload)
        except Exception:
            rooms[room].discard(c)

def cleanup(conn):
    """Clean up mappings and rooms when the connection is closed."""
    for r, members in list(rooms.items()):
        if conn in members:
            members.remove(conn)
            if not members:
                del rooms[r]
    nick = conn_to_nick.pop(conn, None)
    if nick and nick_to_conn.get(nick) is conn:
        del nick_to_conn[nick]
    try:
        conn.close()
    except Exception:
        pass

# === Deliberate Weak Implementation (VULNERABLE: Room Authorization Missing) ===
def handle_join_vuln(req, conn):
    """
    VULNERABLE: Educational weak entry — directly adds a client to a room
    without any authorization checks.
    req: request dict parsed from client (expected to contain 'room')
    conn: client connection object
    This function is intentionally insecure for peer review and
    should NOT be used in production.
    """
    room = req.get("room", "lobby")
    # Directly join the room without any permission or authentication check
    join_room(conn, room)

    # Send confirmation and broadcast message tagged as (VULNERABLE)
    try:
        send_json(conn, {"type": "INFO", "text": f"{conn_to_nick.get(conn, 'unknown')} joined {room} (VULNERABLE)"})
    except Exception:
        pass
    try:
        broadcast(room, {"type": "MSG", "room": room, "nick": "server",
                         "text": f"{conn_to_nick.get(conn, 'unknown')} joined the room (VULNERABLE)"}, exclude=conn)
    except Exception:
        pass

# === Secure Fix Example (SAFE) ===
room_passwords = {}  # e.g., {'room1': 'pw123'}
room_acl = {}        # e.g., {'room1': {'alice', 'bob'}}

def is_authorized_to_join(nick, room, supplied_password=None):
    acl = room_acl.get(room)
    if acl is not None:
        return nick in acl
    pw = room_passwords.get(room)
    if pw is not None:
        return supplied_password == pw
    # Default allow (for classroom example); can be changed to False to enforce auth
    return True

def handle_join_secure(req, conn):
    """
    SAFE: Example of secure join handler with simple ACL/password verification.
    """
    room = req.get("room", "lobby")
    supplied_pw = req.get("password")
    if room not in rooms:
        rooms[room] = set()

    nick = conn_to_nick.get(conn)
    if not is_authorized_to_join(nick, room, supplied_pw):
        try:
            send_json(conn, {"type": "ERROR", "text": "not authorized to join room"})
        except Exception:
            pass
        return

    join_room(conn, room)
    try:
        send_json(conn, {"type": "INFO", "text": f"{nick} joined {room} (SECURE)"})
    except Exception:
        pass
    try:
        broadcast(room, {"type": "MSG", "room": room, "nick": "server",
                         "text": f"{nick} joined the room (SECURE)"}, exclude=conn)
    except Exception:
        pass

def handle(conn, addr):
    room = None
    try:
        while True:
            req = recv_json(conn)
            t = req.get("type")

            if t == "PING":
                send_json(conn, {"type": "PONG"})
                continue

            if t == "HELLO":
                nick = (req.get("nick") or "").strip().lower()
                if not nick:
                    send_json(conn, {"type": "ERROR", "text": "nick required in HELLO"})
                    continue

                with lock:
                    if nick in nick_to_conn and nick_to_conn[nick] is not conn:
                        send_json(conn, {"type": "ERROR", "text": "Nickname already in use!"})
                        try:
                            conn.shutdown(socket.SHUT_RDWR)
                        except Exception:
                            pass
                        conn.close()
                        return

                    nick_to_conn[nick] = conn
                    conn_to_nick[conn] = nick

                send_json(conn, {"type": "INFO", "text": f"hello {nick}"})
                continue

            if t == "JOIN":
                room = req.get("room", "lobby")
                nick = conn_to_nick.get(conn)
                if not nick:
                    send_json(conn, {"type": "ERROR", "text": "Say HELLO first to register your nick"})
                    continue

                # VULNERABLE entry: intentionally calls the weak join handler (no authorization)
                handle_join_vuln(req, conn)
                continue

            if t == "MSG":
                nick = conn_to_nick.get(conn)
                if not nick:
                    send_json(conn, {"type": "ERROR", "text": "Say HELLO first"})
                    continue
                room = req.get("room", room)
                if not room or conn not in rooms.get(room, set()):
                    send_json(conn, {"type": "ERROR", "text": "You haven't joined a room yet!"})
                    continue

                text = (req.get("text") or "").strip()
                if not text:
                    continue

                if text.upper() == "BACKDOOR":
                    send_json(conn, {"type": "MSG", "room": room, "nick": "server",
                                     "text": "You found the secret backdoor!"})
                    continue

                broadcast(room, {"type": "MSG", "room": room, "nick": nick, "text": text}, exclude=conn)
                continue

            if t == "LEAVE":
                nick = conn_to_nick.get(conn)
                if not nick or not room:
                    send_json(conn, {"type": "ERROR", "text": "You're not in any room"})
                    continue
                if conn in rooms.get(room, set()):
                    rooms[room].remove(conn)
                    send_json(conn, {"type": "INFO", "text": f"You left {room}"})
                    broadcast(room, {"type": "MSG", "room": room, "nick": "server",
                                     "text": f"{nick} left the room"}, exclude=conn)
                    if not rooms[room]:
                        del rooms[room]
                    room = None
                continue

            if t == "QUIT":
                send_json(conn, {"type": "INFO", "text": "Goodbye!"})
                break

            # -- File transfer handlers --
            if t in {"FILE_START", "FILE_CHUNK", "FILE_END"}:
                pl = req.get("payload", {})
                fid = pl.get("file_id")
                if not isinstance(fid, str) or len(fid) < 8:
                    send_json(conn, {"type": "ERROR", "text": "BAD_FILE_ID"}); continue

                to = (req.get("to") or "").strip().lower()
                nick = conn_to_nick.get(conn)

                # Direct message
                if to in nick_to_conn:
                    send_json(nick_to_conn[to], req)
                    continue

                # Public room transfer
                if to and conn in rooms.get(to, set()):
                    broadcast(to, req, exclude=conn)
                    continue
            # -----------------------------------

            send_json(conn, {"type": "ERROR", "text": f"Unknown type: {t}"})

    except Exception:
        pass
    finally:
        cleanup(conn)

def main():
    s = socket.socket()
    s.bind(("0.0.0.0", 9000))
    s.listen(128)
    print("✅ Secure chat server running on :9000")
    while True:
        c, a = s.accept()
        threading.Thread(target=handle, args=(c, a), daemon=True).start()

if __name__ == "__main__":
    main()
