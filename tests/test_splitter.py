"""Splitter: the direct-text rule, context chains, no-heading pages, code fences."""

from __future__ import annotations

from volundr.models import SourcePage
from volundr.splitter import split_page


def _page(body: str, title="Page", export_path="Export > Folder") -> SourcePage:
    return SourcePage(
        path=None,
        source="manual",
        source_id="p.md",
        export_path=export_path,
        title=title,
        raw_body=body,
    )


def test_heading_less_page_is_one_note(config):
    notes = split_page(_page("just some prose, no headings at all here."), config)
    assert len(notes) == 1
    assert notes[0].title == "Page"
    assert notes[0].context == "Export > Folder > Page"
    assert notes[0].body == "just some prose, no headings at all here."


def test_heading_with_no_direct_text_emits_no_note_but_extends_context(config):
    body = "\n".join(["# Parent", "## Child", "child body text goes here."])
    notes = split_page(_page(body), config)
    # Parent has no direct text -> no note; Child does.
    assert [n.title for n in notes] == ["Child"]
    assert notes[0].context == "Export > Folder > Page > Parent > Child"


def test_parent_intro_text_becomes_its_own_note(config):
    body = "\n".join(["# Parent", "intro under parent.", "## Child", "child text."])
    notes = split_page(_page(body), config)
    titles = [n.title for n in notes]
    assert titles == ["Parent", "Child"]
    assert notes[0].body == "intro under parent."
    assert notes[0].context == "Export > Folder > Page > Parent"


def test_intro_before_first_heading_is_attributed_to_page_root(config):
    body = "\n".join(["page-level intro.", "# Section", "section body."])
    notes = split_page(_page(body), config)
    assert notes[0].title == "Page"
    assert notes[0].body == "page-level intro."
    assert notes[0].context == "Export > Folder > Page"
    assert notes[1].title == "Section"


def test_siblings_at_same_level_are_separate_notes(config):
    body = "\n".join(["# A", "a body.", "# B", "b body."])
    notes = split_page(_page(body), config)
    assert [n.title for n in notes] == ["A", "B"]
    assert all(n.context == f"Export > Folder > Page > {n.title}" for n in notes)


def test_hash_inside_code_fence_is_not_a_heading(config):
    body = "\n".join(
        ["# Real", "before code.", "```python", "# this is a comment", "x = 1", "```"]
    )
    notes = split_page(_page(body), config)
    assert [n.title for n in notes] == ["Real"]
    assert "# this is a comment" in notes[0].body


def test_length_flags_do_not_change_split(config):
    # min=20, max=200 from the fixture.
    short = split_page(_page("tiny."), config)[0]
    assert short.too_short and not short.too_long
    big = split_page(_page("x" * 300), config)[0]
    assert big.too_long and not big.too_short


def test_empty_page_yields_no_notes(config):
    assert split_page(_page("   \n  \n"), config) == []


def test_export_path_empty_is_dropped_from_context(config):
    notes = split_page(_page("body.", export_path=""), config)
    assert notes[0].context == "Page"
