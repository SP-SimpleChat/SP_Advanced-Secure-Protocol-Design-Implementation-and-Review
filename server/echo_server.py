import socket, struct, json, threading

def send_json(sock, obj):
    data = json.dumps(obj).encode()
    sock.sendall(struct.pack(">I", len(data)) + data)

def recv_exact(sock, n):
    buf=b""
    while len(buf)<n:
        c=sock.recv(n-len(buf))
        if not c: raise ConnectionError()
        buf+=c
    return buf

def recv_json(sock):
    l = struct.unpack(">I", recv_exact(sock,4))[0]
    return json.loads(recv_exact(sock,l).decode())

def handle(conn, addr):
    try:
        while True:
            req = recv_json(conn)
            if req.get("type")=="PING":
                send_json(conn, {"type":"PONG"})
            elif req.get("type")=="HELLO":
                send_json(conn, {"type":"INFO","text":f"hello {req.get('nick')}"})
            elif req.get("type")=="MSG":
                send_json(conn, {"type":"MSG","room":req.get("room","lobby"),
                                 "nick":"server-echo","text":req.get("text","")})
            elif req.get("type")=="QUIT":
                break
            else:
                send_json(conn, {"type":"INFO","text":str(req)})
    except Exception:
        pass
    finally:
        conn.close()

def main():
    s=socket.socket()
    s.bind(("0.0.0.0",9000))
    s.listen(5)
    print("echo server on :9000")
    while True:
        c,a=s.accept()
        threading.Thread(target=handle,args=(c,a),daemon=True).start()

if __name__=="__main__":
    main()
