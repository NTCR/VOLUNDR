"""Filename sanitisation and collision handling for notes written to ``1_NOTES/``.

Filenames are the (sanitised) English note title. Collisions get a numeric suffix,
checked against everything already in ``1_NOTES/`` plus the current batch — never
just the current batch — so re-runs and multi-page batches don't overwrite.
"""

from __future__ import annotations

import re

# Characters that break Obsidian links or filesystems. Stripped from titles.
_FORBIDDEN = re.compile(r"[/\\:#^\[\]|]")
_WHITESPACE = re.compile(r"\s+")

_MAX_STEM = 80  # cap the base filename length (before any collision suffix)


def sanitize_filename(title: str) -> str:
    """Turn a note title into a safe filename stem (no extension).

    Strips ``/ \\ : # ^ [ ] |``, collapses whitespace, trims trailing dots/spaces,
    and caps length. Falls back to ``"untitled"`` if nothing survives.
    """
    stem = _FORBIDDEN.sub("", title)
    stem = _WHITESPACE.sub(" ", stem).strip()
    stem = stem[:_MAX_STEM].strip().rstrip(".")
    return stem or "untitled"


def unique_filename(title: str, taken: set[str]) -> str:
    """Return a ``.md`` filename unique against ``taken`` (a set of lower-cased stems).

    On collision, append `` 2``, `` 3`` ... to the stem. ``taken`` is mutated to
    include the chosen stem, so callers can thread it across a whole batch to keep
    names unique against both the vault and earlier notes in the same run.
    """
    base = sanitize_filename(title)
    stem = base
    counter = 1
    while stem.lower() in taken:
        counter += 1
        stem = f"{base} {counter}"
    taken.add(stem.lower())
    return f"{stem}.md"
