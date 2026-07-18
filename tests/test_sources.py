"""Source parsers: Notion id/title extraction, Capacities frontmatter + createdAt."""

from __future__ import annotations

import pytest

from volundr.sources import get_source
from volundr.sources.base import strip_notion_id
from volundr.sources.notion import NotionSource
from volundr.sources.capacities import CapacitiesSource


def test_notion_extracts_title_id_and_body(tmp_path):
    root = tmp_path
    name = "non linearity 1d6d59967d4280df8d20c10af9378e86.md"
    f = root / name
    f.write_text("# non linearity\n\nsome body text.\n", encoding="utf-8")

    page = NotionSource().parse(f, root)
    assert page.title == "non linearity"
    assert page.source_id == "1d6d59967d4280df8d20c10af9378e86"
    assert page.raw_body == "some body text."
    assert page.native_created is None


def test_notion_missing_id_is_loud_error(tmp_path):
    f = tmp_path / "no-id-here.md"
    f.write_text("# Title\n\nbody.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="No Notion id"):
        NotionSource().parse(f, tmp_path)


def test_notion_export_path_chain_strips_ids(tmp_path):
    sub = tmp_path / "to PKM" / "WORK GRANDVALIRA 27ed59967d4280fa89ebebee7f267fc5"
    sub.mkdir(parents=True)
    f = sub / "note 8e6d666cceec424c9cf3007ae78dc200.md"
    f.write_text("# N\n\nbody.\n", encoding="utf-8")
    page = NotionSource().parse(f, tmp_path)
    assert page.export_path == "to PKM > WORK GRANDVALIRA"


def test_capacities_reads_frontmatter_and_created(tmp_path):
    f = tmp_path / "notas pydantic.md"
    f.write_text(
        "---\n"
        "type: 'AtomicNote'\n"
        "title: notas pydantic\n"
        "tags: [DevStack]\n"
        "createdAt: 2025-03-08\n"
        "---\n\n"
        "# notas pydantic\n\n"
        "body about pydantic.\n",
        encoding="utf-8",
    )
    page = CapacitiesSource().parse(f, tmp_path)
    assert page.title == "notas pydantic"
    assert page.source_id == "notas pydantic"  # no native id -> filename stem
    assert page.native_created == "2025-03-08"
    assert page.raw_body == "body about pydantic."


def test_capacities_missing_date_is_none(tmp_path):
    f = tmp_path / "virtual machine.md"
    f.write_text(
        "---\ntype: 'Definition'\ntitle: virtual machine\ntags: []\n---\n\n"
        "# virtual machine\n\nVM is an emulation.\n",
        encoding="utf-8",
    )
    page = CapacitiesSource().parse(f, tmp_path)
    assert page.native_created is None


def test_registry_defaults_and_unknown():
    assert get_source("notion").name == "notion"
    assert get_source("manual").name == "manual"
    with pytest.raises(ValueError, match="Unknown source"):
        get_source("bogus")


def test_strip_notion_id_helper():
    assert strip_notion_id("GameDEV 94e97b2fa9fd45edb08bd3619939674d") == "GameDEV"
    assert strip_notion_id("no id") == "no id"
