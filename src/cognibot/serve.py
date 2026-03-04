from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
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


def serve_brain(out_dir: Path, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    out_dir = out_dir.resolve()

    def handler(*args, **kwargs):
        return BrainHandler(*args, directory=str(out_dir), **kwargs)

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