from pathlib import Path
from cognibot.scan import scan_repo
from cognibot.stats import show_stats


def test_stats_keys(tmp_path: Path):
    out_dir = scan_repo(tmp_path, tmp_path / "out")
    result = show_stats(out_dir)
    for key in ("snapshot_id", "brain_bytes", "brain_words", "brain_tokens_proxy",
                "packages", "launch_files", "param_files", "msg", "srv", "action"):
        assert key in result


def test_stats_counts_are_ints(tmp_path: Path):
    out_dir = scan_repo(tmp_path, tmp_path / "out")
    result = show_stats(out_dir)
    for key in ("brain_bytes", "brain_words", "brain_tokens_proxy",
                "packages", "launch_files", "param_files"):
        assert isinstance(result[key], int)


def test_stats_token_proxy_is_larger_than_words(tmp_path: Path):
    out_dir = scan_repo(tmp_path, tmp_path / "out")
    result = show_stats(out_dir)
    assert result["brain_tokens_proxy"] >= result["brain_words"]
