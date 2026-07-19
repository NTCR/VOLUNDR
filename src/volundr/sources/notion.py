"""Notion export parser.

Notion (this export vintage) writes ``# Title`` as the first line, then a
nested-heading markdown body, with no YAML frontmatter and no created date.
The 32-hex id in the filename is the ``source_id``.
"""

from __future__ import annotations

from pathlib import Path

import frontmatter

from volundr.models import SourcePage
from volundr.sources.base import (
    discover_markdown,
    export_path_chain,
    extract_notion_id,
    strip_notion_id,
)
from volundr.sources.capacities import _clean_date, _strip_leading_title


class NotionSource:
    name = "notion"

    def discover(self, root: Path):
        return discover_markdown(root)

    def parse(self, path: Path, root: Path) -> SourcePage:
        text = path.read_text(encoding="utf-8")
        title, body = _split_title(text, fallback=strip_notion_id(path.stem))
        source_id = extract_notion_id(path.stem)
        if source_id is None:
            # A Notion export file is expected to carry its id; missing = loud.
            raise ValueError(
                f"No Notion id in filename: {path.name}. "
                "Is this really a Notion export? Use --source manual otherwise."
            )
        return SourcePage(
            path=path,
            source=self.name,
            source_id=source_id,
            export_path=export_path_chain(path, root),
            title=title,
            raw_body=body,
            tags=[],
            native_created=None,  # this export vintage has no date; no mtime fallback
        )


# TODO: why is manual here
class ManualSource(NotionSource):
    """Plain markdown drafts authored by hand. Same shape as Notion but the
    ``source_id`` is the draft filename (there is no native id to require)."""

    name = "manual"

    def parse(self, path: Path, root: Path) -> SourcePage:
        text = path.read_text(encoding="utf-8")
        if text.startswith("---"):
            post = frontmatter.loads(text)
            meta = post.metadata
            title = str(meta.get("title") or path.stem).strip()
            created = _clean_date(meta.get("createdAt") or meta.get("date") or meta.get("created"))
            body = _strip_leading_title(post.content, title)
            tags = [str(t).strip() for t in (meta.get("tags") or [])]
            return SourcePage(
                path=path,
                source=self.name,
                source_id=path.name,
                export_path=export_path_chain(path, root),
                title=title,
                raw_body=body,
                tags=tags,
                native_created=created,
            )
        else:
            title, body = _split_title(text, fallback=path.stem)
            return SourcePage(
                path=path,
                source=self.name,
                source_id=path.name,
                export_path=export_path_chain(path, root),
                title=title,
                raw_body=body,
                tags=[],
                native_created=None,
            )


# TODO: same as _strip_leading_title in capacities
def _split_title(text: str, fallback: str) -> tuple[str, str]:
    """Peel a leading ``# Title`` line off the body.

    If the first non-blank line is a level-1 heading, it becomes the title and is
    removed from the body. Otherwise the ``fallback`` (the cleaned filename) is the
    title and the whole text is the body — the splitter treats subsequent headings
    as content.
    """
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    if idx < len(lines) and lines[idx].lstrip().startswith("# "):
        title = lines[idx].lstrip()[2:].strip()
        body = "\n".join(lines[idx + 1 :]).strip("\n")
        return title, body
    return fallback, text.strip("\n")
