"""Source parser protocol and shared helpers.

A ``Source`` knows how to (1) discover draft files under a root and (2) parse one
file into a :class:`~volundr.models.SourcePage`. Concrete parsers live alongside
this module (``notion.py``, ``capacities.py``); the registry is in ``__init__.py``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Protocol

from volundr.models import SourcePage

# Notion appends a 32-hex-char id to file and folder names, e.g.
# "WORK GRANDVALIRA 27ed59967d4280fa89ebebee7f267fc5.md".
_NOTION_ID = re.compile(r"\s+([0-9a-f]{32})$", re.IGNORECASE)

# Folder marking already-processed drafts; never re-discovered.
DONE_DIRNAME = "_done"


class Source(Protocol):
    """Interface every source parser implements."""

    name: str

    def discover(self, root: Path) -> Iterable[Path]:
        """Yield ``.md`` draft paths under ``root`` (recursive), skipping ``_done/``."""
        ...

    def parse(self, path: Path, root: Path) -> SourcePage:
        """Parse one draft file into a :class:`SourcePage`."""
        ...


def discover_markdown(root: Path) -> list[Path]:
    """Recursively find ``.md`` files under ``root``, skipping the ``_done/`` folder.

    Shared by all parsers — discovery is identical across sources; only parsing
    differs. Returns a sorted list for deterministic run ordering.
    """
    return sorted(
        p for p in root.rglob("*.md") if DONE_DIRNAME not in p.relative_to(root).parts
    )


# TODO: why not in notion source?
def strip_notion_id(name: str) -> str:
    """Remove a trailing 32-hex Notion id from a file/folder stem."""
    return _NOTION_ID.sub("", name).strip()


def extract_notion_id(stem: str) -> str | None:
    """Return the trailing 32-hex Notion id from a filename stem, or None."""
    match = _NOTION_ID.search(stem)
    return match.group(1) if match else None


def export_path_chain(path: Path, root: Path) -> str:
    """Human-readable provenance of the parent folders relative to ``root``.

    Notion ids are stripped from each folder component so the chain reads cleanly
    (e.g. ``"to PKM > WORK GRANDVALIRA"``). Returns ``""`` for a file directly
    under ``root``.
    """
    parts = path.relative_to(root).parent.parts
    cleaned = [strip_notion_id(part) for part in parts]
    return " > ".join(p for p in cleaned if p)
