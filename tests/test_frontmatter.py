"""Frontmatter writer: canonical fields present, LLM fields empty, created omitted."""

from __future__ import annotations

import frontmatter

from volundr.models import Note
from volundr.frontmatter import render_note


def _note(**kw) -> Note:
    base = dict(
        title="A Note",
        context="Export > Page > A Note",
        source="notion",
        source_id="abc123",
        body="the body, untouched.",
    )
    base.update(kw)
    return Note(**base)


def test_deterministic_fields_and_empty_llm_seam():
    text = render_note(_note(), processed="2026-07-11", pipeline_stamp="v1")
    post = frontmatter.loads(text)
    assert post["title"] == "A Note"
    assert post["processed"] == "2026-07-11"
    assert post["source"] == "notion"
    assert post["source_id"] == "abc123"
    assert post["context"] == "Export > Page > A Note"
    assert post["pipeline"] == "v1"
    # Stage-3 seam: vocabulary lists present but empty; type/summary absent.
    assert post["tags"] == []
    assert post["proposed_tags"] == []
    assert "type" not in post.metadata
    assert "summary" not in post.metadata
    assert post.content == "the body, untouched."


def test_created_omitted_when_absent_but_present_when_set():
    without = frontmatter.loads(render_note(_note(created=None), "2026-07-11", "v1"))
    assert "created" not in without.metadata

    with_date = frontmatter.loads(
        render_note(_note(created="2025-03-08"), "2026-07-11", "v1")
    )
    assert with_date["created"] == "2025-03-08"


def test_body_is_passed_through_verbatim():
    body = "line 1\n\n## a subheading kept in body\n\n- bullet"
    text = render_note(_note(body=body), "2026-07-11", "v1")
    assert frontmatter.loads(text).content == body
