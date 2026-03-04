from __future__ import annotations
from pathlib import Path
import json

def show_stats(out_dir: Path) -> dict:
    out_dir = out_dir.resolve()
    idx = json.loads((out_dir / "index.json").read_text(encoding="utf-8"))
    sid = idx["latest_snapshot_id"]
    snap_dir = out_dir / "snapshots" / sid

    brain = (snap_dir / "brain.md").read_text(encoding="utf-8")
    snapshot = json.loads((snap_dir / "snapshot.json").read_text(encoding="utf-8"))

    bytes_len = len(brain.encode("utf-8"))
    words = len(brain.split())
    est_tokens = int(words * 1.3)  # rough proxy

    iface = snapshot.get("interfaces", {})
    result = {
        "snapshot_id": sid,
        "brain_bytes": bytes_len,
        "brain_words": words,
        "brain_tokens_proxy": est_tokens,
        "packages": len(snapshot.get("packages", [])),
        "launch_files": len(snapshot.get("launch_files", [])),
        "param_files": len(snapshot.get("param_files", [])),
        "msg": len(iface.get("msg", [])),
        "srv": len(iface.get("srv", [])),
        "action": len(iface.get("action", [])),
    }
    return result
