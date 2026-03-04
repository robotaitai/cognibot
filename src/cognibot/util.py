from __future__ import annotations

from pathlib import Path
import os
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
    sid = git.commit[:8] if git.commit else "nogit"
    if git.dirty:
        sid += "-dirty"
    return sid


def detect_repo_root(start: Path) -> Path:
    """
    Try to behave like "Cursor knows my workspace":
    - if CURSOR_PROJECT_DIR is set, use it
    - else if in a git repo, use git toplevel
    - else use the provided path
    """
    env_root = os.environ.get("CURSOR_PROJECT_DIR") or os.environ.get("COGNIBOT_REPO")
    if env_root:
        p = Path(env_root).expanduser().resolve()
        if p.exists():
            return p

    start = start.expanduser().resolve()

    # git root if possible
    try:
        root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=start).decode().strip()
        p = Path(root).resolve()
        if p.exists():
            return p
    except Exception:
        pass

    return start


def resolve_out_dir(repo: Path, out: Path | None) -> Path:
    return out if out is not None else (repo / ".cognibot")