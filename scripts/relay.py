"""Forward 127.0.0.1:<local_port> on the login node to <host>:<port> on a compute node,
so VS Code (or ssh -L) can show a demo running on a GPU node as http://localhost:<local_port>.

    python scripts/relay.py 7861 cn07 7860
"""

import socket
import sys
import threading


def pipe(src: socket.socket, dst: socket.socket) -> None:
    try:
        while data := src.recv(65536):
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for s in (src, dst):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def main() -> None:
    local_port, host, port = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", local_port))
    server.listen(64)
    print(f"relay 127.0.0.1:{local_port} -> {host}:{port}", flush=True)
    while True:
        client, _ = server.accept()
        try:
            upstream = socket.create_connection((host, port), timeout=10)
            upstream.settimeout(None)
        except OSError:
            client.close()
            continue
        threading.Thread(target=pipe, args=(client, upstream), daemon=True).start()
        threading.Thread(target=pipe, args=(upstream, client), daemon=True).start()


if __name__ == "__main__":
    main()
