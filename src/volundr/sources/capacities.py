"""Capacities export parser.

Capacities writes YAML frontmatter (``type``, ``title``, ``tags``, ``createdAt``,
...) followed by ``# title`` and the body. These exports carry no native object id,
so the note filename stem is used as ``source_id`` (dedup stays queryable by it).
The created date comes from ``createdAt`` when present. Existing human ``tags`` are
read but NOT emitted in Stage 1 — they are a Stage-2 harvest input.
"""

from __future__ import annotations

from pathlib import Path

import frontmatter

from volundr.models import SourcePage
from volundr.sources.base import discover_markdown, export_path_chain


class CapacitiesSource:
    name = "capacities"

    def discover(self, root: Path):
        return discover_markdown(root)

    def parse(self, path: Path, root: Path) -> SourcePage:
        post = frontmatter.loads(path.read_text(encoding="utf-8"))
        meta = post.metadata

        title = str(meta.get("title") or path.stem).strip()
        created = _clean_date(meta.get("createdAt") or meta.get("date"))
        body = _strip_leading_title(post.content, title)
        tags = [str(t).strip() for t in (meta.get("tags") or [])]

        return SourcePage(
            path=path,
            source=self.name,
            source_id=path.stem,  # no native id in these exports; filename is stable
            export_path=export_path_chain(path, root),
            title=title,
            raw_body=body,
            tags=tags,
            native_created=created,
        )


def _clean_date(value) -> str | None:
    """Normalise a frontmatter date to a plain string, or None when absent/null."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _strip_leading_title(content: str, title: str) -> str:
    """Drop the leading ``# ...`` heading that duplicates the frontmatter title."""
    lines = content.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    if idx < len(lines) and lines[idx].lstrip().startswith("# "):
        return "\n".join(lines[idx + 1 :]).strip("\n")
    return content.strip("\n")
