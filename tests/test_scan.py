import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from cognibot.scan import scan_repo


def _make_pkg(root: Path, name: str, build_type: str | None = None, depends: list[str] | None = None) -> None:
    pkg_dir = root / name
    pkg_dir.mkdir(parents=True, exist_ok=True)
    export = ""
    if build_type:
        export = f"<export><build_type>{build_type}</build_type></export>"
    dep_tags = "".join(f"<depend>{d}</depend>" for d in (depends or []))
    (pkg_dir / "package.xml").write_text(
        f'<?xml version="1.0"?>'
        f'<package format="3"><name>{name}</name>{dep_tags}{export}</package>',
        encoding="utf-8",
    )


def test_scan_empty_repo(tmp_path: Path):
    out_dir = scan_repo(tmp_path, tmp_path / "out")
    assert (out_dir / "index.json").exists()
    idx = json.loads((out_dir / "index.json").read_text())
    sid = idx["latest_snapshot_id"]
    snap = json.loads((out_dir / "snapshots" / sid / "snapshot.json").read_text())
    assert snap["packages"] == []
    assert snap["launch_files"] == []


def test_scan_finds_packages(tmp_path: Path):
    _make_pkg(tmp_path, "alpha", build_type="ament_cmake", depends=["rclcpp"])
    _make_pkg(tmp_path, "beta")
    out_dir = scan_repo(tmp_path, tmp_path / "out")
    idx = json.loads((out_dir / "index.json").read_text())
    snap = json.loads((out_dir / "snapshots" / idx["latest_snapshot_id"] / "snapshot.json").read_text())
    names = [p["name"] for p in snap["packages"]]
    assert "alpha" in names
    assert "beta" in names


def test_scan_ignores_dotgit(tmp_path: Path):
    _make_pkg(tmp_path / ".git", "hidden_pkg")
    out_dir = scan_repo(tmp_path, tmp_path / "out")
    idx = json.loads((out_dir / "index.json").read_text())
    snap = json.loads((out_dir / "snapshots" / idx["latest_snapshot_id"] / "snapshot.json").read_text())
    assert snap["packages"] == []


def test_scan_brain_md_created(tmp_path: Path):
    _make_pkg(tmp_path, "mypkg")
    out_dir = scan_repo(tmp_path, tmp_path / "out")
    idx = json.loads((out_dir / "index.json").read_text())
    brain = (out_dir / "snapshots" / idx["latest_snapshot_id"] / "brain.md").read_text()
    assert "# cognibot brain" in brain
    assert "mypkg" in brain


def test_scan_finds_launch_files(tmp_path: Path):
    launch_dir = tmp_path / "my_pkg" / "launch"
    launch_dir.mkdir(parents=True)
    (launch_dir / "bringup.launch.py").write_text("# launch", encoding="utf-8")
    out_dir = scan_repo(tmp_path, tmp_path / "out")
    idx = json.loads((out_dir / "index.json").read_text())
    snap = json.loads((out_dir / "snapshots" / idx["latest_snapshot_id"] / "snapshot.json").read_text())
    assert any("bringup.launch.py" in f for f in snap["launch_files"])
