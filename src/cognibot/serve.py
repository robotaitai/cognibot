from __future__ import annotations

from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import webbrowser


def serve_dir(out_dir: Path, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    out_dir = out_dir.resolve()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(out_dir), **kwargs)

        # no-cache so refresh always shows latest
        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

    httpd = ThreadingHTTPServer((host, port), Handler)

    # URL hint
    if host == "0.0.0.0":
        url = f"http://localhost:{port}/ui/brain.html"
        print(f"[cognibot] serving on 0.0.0.0:{port} (LAN). open from another PC: http://<jetson-ip>:{port}/ui/brain.html")
    else:
        url = f"http://{host}:{port}/ui/brain.html"
        print(f"[cognibot] serving: {url}")

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass