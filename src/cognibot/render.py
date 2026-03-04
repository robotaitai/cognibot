from __future__ import annotations
from pathlib import Path
import importlib.resources as pkg_resources

def render_ui(out_dir: Path) -> Path:
    out_dir = out_dir.resolve()
    ui_dir = out_dir / "ui"
    ui_dir.mkdir(parents=True, exist_ok=True)

    html = pkg_resources.files("cognibot.templates").joinpath("brain.html").read_text(encoding="utf-8")
    dest = ui_dir / "brain.html"
    dest.write_text(html, encoding="utf-8")
    return dest
