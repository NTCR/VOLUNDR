"""Deterministic, heading-based splitting of one source page into atomic notes.

No LLM is involved. Granularity is authored by the human via headings at write
time; the splitter never second-guesses it.

Rules (see _docs/project-context.md "Splitting"):

- The page title acts as the root (an implicit level-0 heading) and is the
  ancestor of every content heading, regardless of that heading's markdown level.
- A note is emitted for every heading that has **direct body text**: the lines
  after the heading, up to the next heading of any level. Headings with no direct
  text emit no note but still extend the context chain of their descendants.
- A heading-less page emits exactly one note (title = page title, body = whole page).
- ``title`` is the heading verbatim; ``context`` is the plain-text chain
  ``"Export path > Page title > H1 > H2"`` (never wikilinks).
- Length never changes the split — it only sets report-only outlier flags.

``#`` lines inside fenced code blocks (``` or ~~~) are NOT treated as headings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from volundr.config import Config
from volundr.models import Note, SourcePage

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")

_ROOT_LEVEL = 0  # the page title sits above every real (level >=1) heading


@dataclass
class _Section:
    level: int
    title: str
    lines: list[str] = field(default_factory=list)  # direct text under this heading
    ancestors: list[str] = field(default_factory=list)


def split_page(page: SourcePage, config: Config) -> list[Note]:
    """Split ``page`` into atomic notes."""
    sections = _parse_sections(page.title, page.raw_body)
    _assign_ancestors(sections)

    notes: list[Note] = []
    for section in sections:
        body = "\n".join(section.lines).strip()
        if not body:
            # No direct text: extends context for descendants, emits no note.
            continue
        chain = [page.export_path, *section.ancestors, section.title]
        context = " > ".join(part for part in chain if part)
        length = len(body)
        notes.append(
            Note(
                title=section.title,
                context=context,
                source=page.source,
                source_id=page.source_id,
                body=body,
                created=page.native_created,
                too_short=length < config.length.min_chars,
                too_long=length > config.length.max_chars,
            )
        )
    return notes


# TODO: interesting parsing code
def _parse_sections(page_title: str, body: str) -> list[_Section]:
    """Walk the body into a flat, ordered list of sections (root first).

    ``#`` lines inside fenced code blocks are body content, not headings.
    """
    sections = [_Section(level=_ROOT_LEVEL, title=page_title)]
    current = sections[0]
    in_fence = False

    for line in body.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
            current.lines.append(line)
            continue

        match = None if in_fence else _HEADING.match(line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            section = _Section(level=level, title=title)
            sections.append(section)
            current = section
        else:
            current.lines.append(line)

    return sections


def _assign_ancestors(sections: list[_Section]) -> None:
    """Populate each section's ancestor-title chain from heading nesting."""
    stack: list[_Section] = []
    for section in sections:
        while stack and stack[-1].level >= section.level:
            stack.pop()
        section.ancestors = [s.title for s in stack]
        stack.append(section)
