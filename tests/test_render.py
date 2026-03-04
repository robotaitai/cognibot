from pathlib import Path
from cognibot.scan import scan_repo
from cognibot.render import render_ui


def test_render_creates_html(tmp_path: Path):
    out_dir = scan_repo(tmp_path, tmp_path / "out")
    html_path = render_ui(out_dir)
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")
    assert "<!doctype html>" in content
    assert "cognibot" in content


def test_render_html_in_ui_subdir(tmp_path: Path):
    out_dir = scan_repo(tmp_path, tmp_path / "out")
    html_path = render_ui(out_dir)
    assert html_path.parent.name == "ui"
