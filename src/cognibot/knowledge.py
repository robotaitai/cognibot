from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

KNOWLEDGE_FILE = "knowledge.md"

_TEMPLATE = """\
# cognibot knowledge

Persistent learnings accumulated by the AI across sessions.
The AI reads this at the start of every session and appends to it when it
discovers something valuable about this codebase.

## conventions
<!-- Coding patterns, naming conventions, repo-specific rules -->

## architecture notes
<!-- How subsystems connect, design decisions, why things are the way they are -->

## gotchas
<!-- Things that are surprising, non-obvious, or easy to get wrong -->

## debug notes
<!-- Past debugging sessions: what broke, how it was fixed, what to watch for -->

"""


def knowledge_path(out_dir: Path) -> Path:
    return out_dir / KNOWLEDGE_FILE


def ensure_knowledge(out_dir: Path) -> Path:
    """Create knowledge.md if it doesn't exist. Returns the path."""
    kp = knowledge_path(out_dir)
    if not kp.exists():
        kp.write_text(_TEMPLATE, encoding="utf-8")
    return kp


def append_knowledge(out_dir: Path, section: str, entry: str) -> None:
    """Append an entry under the given section heading."""
    kp = ensure_knowledge(out_dir)
    text = kp.read_text(encoding="utf-8")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    tagged_entry = f"- [{timestamp}] {entry}\n"

    marker = f"## {section}"
    if marker in text:
        idx = text.index(marker)
        # Find the end of the section header line
        line_end = text.index("\n", idx)
        # Skip past any HTML comment line
        rest = text[line_end + 1:]
        if rest.startswith("<!--"):
            comment_end = rest.index("-->") + 3
            insert_pos = line_end + 1 + comment_end + 1
        else:
            insert_pos = line_end + 1
        text = text[:insert_pos] + tagged_entry + text[insert_pos:]
    else:
        text += f"\n{marker}\n{tagged_entry}"

    kp.write_text(text, encoding="utf-8")
