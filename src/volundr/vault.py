"""Vault layout and per-source atomic writes.

Guarantees (see _docs/project-context.md "Migration robustness"):

- **Append-only**: import never edits or deletes existing notes.
- **Per-source atomicity**: the N notes from one page are written all-or-nothing
  (temp files, then rename-commit); on any error nothing lands and the draft stays
  in ``0_INBOX/``. Interrupted runs resume by re-running.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

INBOX = "0_INBOX"
DONE = "0_INBOX/_done"
NOTES = "1_NOTES"
ATTACHMENTS = "_ATTACHMENTS"
META = "_META"
_SUBDIRS = [
    INBOX,
    DONE,
    NOTES,
    ATTACHMENTS,
    "_META/logs",
    "_META/harvest",
    "_META/eval",
]


def ensure_layout(vault: Path) -> None:
    """Create the vault folder skeleton if missing (idempotent)."""
    for sub in _SUBDIRS:
        (vault / sub).mkdir(parents=True, exist_ok=True)


def existing_stems(notes_dir: Path) -> set[str]:
    """Lower-cased filename stems already in ``1_NOTES/`` — the collision baseline."""
    if not notes_dir.exists():
        return set()
    # TODO : how does this work
    return {p.stem.lower() for p in notes_dir.glob("*.md")}


def write_notes_atomic(notes_dir: Path, rendered: list[tuple[str, str]]) -> list[Path]:
    """Write ``(filename, text)`` pairs all-or-nothing into ``notes_dir``.

    Every file is written to a temp sibling first; only once all temps exist are
    they rename-committed into place. Any failure removes the temps and raises,
    leaving ``notes_dir`` untouched. Refuses to overwrite an existing note
    (append-only) — callers must resolve filename collisions beforehand.
    """
    notes_dir.mkdir(parents=True, exist_ok=True)
    tmp_paths: list[Path] = []
    finals: list[Path] = []
    try:
        for filename, text in rendered:
            final = notes_dir / filename
            if final.exists():
                raise FileExistsError(
                    f"Refusing to overwrite existing note: {final.name}"
                )
            tmp = notes_dir / f".{filename}.{uuid.uuid4().hex}.tmp"
            tmp.write_text(text, encoding="utf-8")
            tmp_paths.append(tmp)
            finals.append(final)

        for tmp, final in zip(tmp_paths, finals):
            os.replace(tmp, final)
        return finals
    except BaseException:
        for tmp in tmp_paths:
            tmp.unlink(missing_ok=True)
        raise


def move_draft_to_done(draft: Path, done_dir: Path) -> Path:
    """Move a processed draft into ``0_INBOX/_done/`` (deletion stays manual).

    On name collision in ``_done/``, append a numeric suffix rather than clobber.
    """
    done_dir.mkdir(parents=True, exist_ok=True)
    target = done_dir / draft.name
    counter = 1
    while target.exists():
        counter += 1
        target = done_dir / f"{draft.stem} {counter}{draft.suffix}"
    os.replace(draft, target)
    return target
