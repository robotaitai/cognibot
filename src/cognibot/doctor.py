from __future__ import annotations
from pathlib import Path

from .scan import scan_repo
from .util import resolve_out_dir

def doctor(repo: Path, out: Path | None = None) -> list[str]:
    repo = repo.resolve()
    out_dir = resolve_out_dir(repo, out)

    notes: list[str] = []
    if not repo.exists():
        return [f"repo path does not exist: {repo}"]

    pkg_xml = list(repo.rglob("package.xml"))
    notes.append(f"found package.xml: {len([p for p in pkg_xml if p.is_file()])}")

    out_dir = scan_repo(repo, out_dir)
    notes.append(f"wrote: {out_dir}")

    idx = out_dir / "index.json"
    if not idx.exists():
        notes.append("ERROR: index.json missing")
        return notes

    notes.append("ok: index.json present")
    notes.append("next: open the UI: .cognibot/ui/brain.html (inside scanned repo)")
    return notes
