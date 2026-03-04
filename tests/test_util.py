from pathlib import Path
from cognibot.util import (
    is_ignored_path,
    make_snapshot_id,
    resolve_out_dir,
    GitInfo,
    utc_now,
)


def test_is_ignored_path_git():
    assert is_ignored_path(Path(".git/config"))


def test_is_ignored_path_venv():
    assert is_ignored_path(Path("some/repo/.venv/lib/python3.11/site.py"))


def test_is_ignored_path_normal():
    assert not is_ignored_path(Path("src/my_pkg/node.py"))


def test_make_snapshot_id_clean():
    git = GitInfo(commit="abcdef1234567890", dirty=False)
    assert make_snapshot_id(git) == "abcdef12"


def test_make_snapshot_id_dirty():
    git = GitInfo(commit="abcdef1234567890", dirty=True)
    assert make_snapshot_id(git) == "abcdef12-dirty"


def test_make_snapshot_id_nogit():
    git = GitInfo(commit=None, dirty=False)
    assert make_snapshot_id(git) == "nogit"


def test_resolve_out_dir_default():
    repo = Path("/tmp/myrepo")
    assert resolve_out_dir(repo, None) == repo / ".cognibot"


def test_resolve_out_dir_explicit():
    repo = Path("/tmp/myrepo")
    custom = Path("/tmp/out")
    assert resolve_out_dir(repo, custom) == custom


def test_utc_now_is_aware():
    import datetime
    now = utc_now()
    assert now.tzinfo is not None
    assert now.tzinfo == datetime.timezone.utc
