from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import signal
import socket
import threading
import webbrowser


class BrainHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # Route root to the UI dashboard
        if self.path in ("/", "/index.html"):
            self.path = "/ui/index.html"
        return super().do_GET()

    def end_headers(self):
        # Disable caching so refresh shows new scans immediately
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


def _kill_port(port: int) -> bool:
    """Kill any process currently listening on *port*. Returns True if something was killed."""
    try:
        import subprocess
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True
        )
        pids = result.stdout.strip().split()
        if not pids:
            return False
        for pid in pids:
            try:
                os.kill(int(pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        return True
    except Exception:
        return False


def serve_brain(out_dir: Path, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    out_dir = out_dir.resolve()

    def handler(*args, **kwargs):
        return BrainHandler(*args, directory=str(out_dir), **kwargs)

    # If the port is already in use, kill the old server and retry once.
    try:
        httpd = ThreadingHTTPServer((host, port), handler)
    except OSError as exc:
        if exc.errno != 98:  # 98 = EADDRINUSE
            raise
        print(f"[cognibot] Port {port} in use — killing old server and retrying…")
        _kill_port(port)
        import time; time.sleep(0.5)
        httpd = ThreadingHTTPServer((host, port), handler)

    local_url = f"http://localhost:{port}/"
    print(f"\n[cognibot] Brain Studio running:")
    print(f"  Local: {local_url}")
    if host == "0.0.0.0":
        print(f"  LAN:   http://<jetson-ip>:{port}/")

    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(local_url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass