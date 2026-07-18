"""Per-source atomicity and end-to-end pipeline behaviour on a fake vault."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from volundr import pipeline, vault as vault_mod
from volundr.vault import write_notes_atomic


# --- vault.write_notes_atomic: all-or-nothing -------------------------------

def test_atomic_write_rolls_back_and_leaves_no_temps(tmp_path):
    notes_dir = tmp_path / "1_NOTES"
    notes_dir.mkdir()
    # Pre-existing note that will make the SECOND write refuse (append-only).
    (notes_dir / "B.md").write_text("original B, must survive.", encoding="utf-8")

    with pytest.raises(FileExistsError):
        write_notes_atomic(notes_dir, [("A.md", "new A"), ("B.md", "new B")])

    # A must NOT have been committed, B untouched, no leftover temp files.
    assert not (notes_dir / "A.md").exists()
    assert (notes_dir / "B.md").read_text(encoding="utf-8") == "original B, must survive."
    assert list(notes_dir.glob(".*tmp")) == []
    assert [p.name for p in notes_dir.iterdir()] == ["B.md"]


def test_atomic_write_commits_all_on_success(tmp_path):
    notes_dir = tmp_path / "1_NOTES"
    written = write_notes_atomic(notes_dir, [("A.md", "a"), ("B.md", "b")])
    assert {p.name for p in written} == {"A.md", "B.md"}
    assert (notes_dir / "A.md").read_text() == "a"


# --- pipeline end-to-end ----------------------------------------------------

def _fake_vault(tmp_path: Path, config) -> tuple[object, Path]:
    vault = tmp_path / "VAULT"
    vault_mod.ensure_layout(vault)
    cfg = replace(config, vault_path=vault)
    return cfg, vault


def test_dry_run_writes_nothing(tmp_path, config):
    cfg, vault = _fake_vault(tmp_path, config)
    draft = vault / "0_INBOX" / "idea a1b2c3d4e5f60718293a4b5c6d7e8f90.md"
    draft.write_text("# Big Idea\n\nthe body of the idea.\n", encoding="utf-8")

    report = pipeline.run(cfg, "notion", dry_run=True)

    assert report.notes_written == 1
    assert list((vault / "1_NOTES").glob("*.md")) == []  # nothing written
    assert draft.exists()  # draft not moved
    assert list((vault / "_META/logs").glob("*.md")) == []  # no report file


def test_real_run_writes_notes_moves_draft_and_reports(tmp_path, config):
    cfg, vault = _fake_vault(tmp_path, config)
    draft = vault / "0_INBOX" / "idea a1b2c3d4e5f60718293a4b5c6d7e8f90.md"
    draft.write_text(
        "# Big Idea\n\nintro body.\n\n## Sub\n\nsub body here.\n", encoding="utf-8"
    )
    # A non-md sibling must be counted, never touched.
    (vault / "0_INBOX" / "diagram.png").write_bytes(b"\x89PNG")

    report = pipeline.run(cfg, "notion", dry_run=False)

    notes = sorted(p.name for p in (vault / "1_NOTES").glob("*.md"))
    assert notes == ["Big Idea.md", "Sub.md"]
    assert not draft.exists()  # moved out of inbox
    assert (vault / "0_INBOX/_done" / draft.name).exists()
    assert report.non_md_count == 1
    assert (vault / "0_INBOX" / "diagram.png").exists()  # untouched
    assert list((vault / "_META/logs").glob("run-*.md"))  # report written


def test_rerun_is_safe_and_appends_without_clobber(tmp_path, config):
    cfg, vault = _fake_vault(tmp_path, config)
    for i in (1, 2):
        draft = vault / "0_INBOX" / f"idea a1b2c3d4e5f60718293a4b5c6d7e8f9{i}.md"
        draft.write_text("# Same Title\n\nbody version.\n", encoding="utf-8")
        pipeline.run(cfg, "notion", dry_run=False)

    names = sorted(p.name for p in (vault / "1_NOTES").glob("*.md"))
    assert names == ["Same Title 2.md", "Same Title.md"]


def test_parse_error_is_isolated_not_fatal(tmp_path, config):
    cfg, vault = _fake_vault(tmp_path, config)
    # Notion parser requires an id in the filename; this one lacks it -> error.
    bad = vault / "0_INBOX" / "no-id.md"
    bad.write_text("# X\n\nbody.\n", encoding="utf-8")
    good = vault / "0_INBOX" / "ok a1b2c3d4e5f60718293a4b5c6d7e8f90.md"
    good.write_text("# Good\n\nbody.\n", encoding="utf-8")

    report = pipeline.run(cfg, "notion", dry_run=False)

    assert len(report.errored) == 1
    assert len(report.ok) == 1
    assert (vault / "1_NOTES" / "Good.md").exists()
    assert bad.exists()  # failed draft stays in inbox
