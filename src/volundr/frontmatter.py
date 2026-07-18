"""Render a :class:`~volundr.models.Note` to markdown with canonical frontmatter.

Schema (see _docs/project-context.md "Frontmatter schema"). Deterministic fields
are filled in Stage 1; the LLM fields are the Stage-3 seam:

- ``tags`` / ``proposed_tags`` are always written as (possibly empty) lists — they
  are the load-bearing vocabulary hook Stage 3 fills.
- ``type`` / ``summary`` are omitted while empty (added later), like ``created``
  which is omitted when the source has no native date.

The note body is passed through verbatim — the pipeline never edits note content.
"""

from __future__ import annotations

import frontmatter

from volundr.models import Note

# Canonical key order for readable, diff-stable frontmatter.
_ORDER = [
    "title",
    "created",
    "processed",
    "source",
    "source_id",
    "context",
    "pipeline",
    "type",
    "tags",
    "proposed_tags",
    "summary",
]


def render_note(note: Note, processed: str, pipeline_stamp: str) -> str:
    """Return the full markdown text (frontmatter + body) for one note."""
    meta: dict[str, object] = {
        "title": note.title,
        "processed": processed,
        "source": note.source,
        "source_id": note.source_id,
        "context": note.context,
        "pipeline": pipeline_stamp,
        "tags": list(note.tags),
        "proposed_tags": list(note.proposed_tags),
    }
    if note.created:
        meta["created"] = note.created
    if note.type:
        meta["type"] = note.type
    if note.summary:
        meta["summary"] = note.summary

    ordered = {k: meta[k] for k in _ORDER if k in meta}
    post = frontmatter.Post(note.body, **ordered) #type: ignore
    # sort_keys=False preserves our canonical order instead of alphabetising.
    return frontmatter.dumps(post, sort_keys=False)
