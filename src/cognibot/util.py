from __future__ import annotations
from pathlib import Path
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone

IGNORE_DIRS = {".git", ".cognibot", "build", "install", "log", ".venv", "venv", "__pycache__"}

@dataclass(frozen=True)
class GitInfo:
    commit: str | None
    dirty: bool

def utc_now():
    return datetime.now(timezone.utc)

def is_ignored_path(p: Path) -> bool:
    parts = set(p.parts)
    return any(d in parts for d in IGNORE_DIRS)

def get_git_info(repo: Path) -> GitInfo:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo).decode().strip()
        dirty = subprocess.call(["git", "diff", "--quiet"], cwd=repo) != 0
        return GitInfo(commit=commit, dirty=dirty)
    except Exception:
        return GitInfo(commit=None, dirty=False)

def make_snapshot_id(git: GitInfo) -> str:
    if git.commit:
        sid = git.commit[:8]
    else:
        sid = "nogit"
    if git.dirty:
        sid += "-dirty"
    return sid

def resolve_out_dir(repo: Path, out: Path | None) -> Path:
    return out if out is not None else (repo / ".cognibot")
