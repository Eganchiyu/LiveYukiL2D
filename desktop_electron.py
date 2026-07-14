from __future__ import annotations

import os
import socket
import subprocess
import threading
import time
from pathlib import Path

from server import HOST, PORT, main as run_server

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend" / "minimal"


def is_server_running() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((HOST, PORT)) == 0


def start_server() -> None:
    run_server(handle_signals=False)


def ensure_server() -> None:
    if is_server_running():
        print(f"LiveYukiL2D server already running: http://{HOST}:{PORT}")
        return

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    for _ in range(30):
        if is_server_running():
            return
        time.sleep(0.1)

    raise RuntimeError(f"服务启动超时：http://{HOST}:{PORT}")


def main() -> None:
    ensure_server()
    npm = "npm.cmd" if os.name == "nt" else "npm"
    subprocess.run([npm, "run", "desktop"], cwd=FRONTEND_DIR, check=True)


if __name__ == "__main__":
    main()
