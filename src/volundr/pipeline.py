"""End-to-end deterministic pipeline: inbox drafts -> atomic notes in the vault.

    discover -> parse -> split -> sanitise+collision -> frontmatter -> atomic write
    -> move draft to _done -> run report

No LLM. Each source page is processed independently and atomically: one bad page
is recorded as an error and never poisons the batch.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from volundr.config import Config
from volundr.frontmatter import render_note
from volundr.models import SourcePage, SourceResult
from volundr.naming import unique_filename
from volundr.report import RunReport
from volundr.splitter import split_page
from volundr.sources import get_source
from volundr import vault as vault_mod


def run(
    config: Config,
    source_name: str,
    dry_run: bool = False,
    eval_mode: bool = False,
) -> RunReport:
    """Process every draft in ``0_INBOX/`` for the given source. Returns the report."""
    vault = config.vault_path
    vault_mod.ensure_layout(vault)
    # setup folders
    inbox = vault / vault_mod.INBOX
    done_dir = vault / vault_mod.DONE
    logs_dir = vault / "_META/logs"
    if eval_mode:
        notes_dir = vault / "_META/eval/runs" / config.pipeline_stamp
    else:
        notes_dir = vault / vault_mod.NOTES
    # TODO: source trae historia
    source = get_source(source_name)
    processed = date.today().isoformat()
    # log
    report = RunReport(source=source_name, dry_run=dry_run)
    report.non_md_count = _count_non_md(inbox)
    # stems en el vault (para luego calcular nuevos filename)
    taken = vault_mod.existing_stems(notes_dir)

    for path in source.discover(inbox):
        report.add(
            _process_page(
                path=path,
                root=inbox,
                source=source,
                config=config,
                processed=processed,
                notes_dir=notes_dir,
                done_dir=done_dir,
                taken=taken,
                dry_run=dry_run,
                eval_mode=eval_mode,
            )
        )

    if not dry_run:
        report.write(logs_dir)
    return report


def _process_page(
    *,
    path: Path,
    root: Path,
    source,
    config: Config,
    processed: str,
    notes_dir: Path,
    done_dir: Path,
    taken: set[str],
    dry_run: bool,
    eval_mode: bool,
) -> SourceResult:
    """Parse, split, and (unless dry-run) atomically write one page's notes."""
    try:
        page: SourcePage = source.parse(path, root)
    except Exception as exc:  # parse failure = per-source error, batch continues
        return SourceResult(
            page=_stub_page(path, source.name),
            status="error",
            reason=f"parse failed: {exc}",
        )

    notes = split_page(page, config)
    if not notes:
        return SourceResult(page=page, status="skipped", reason="no content to split")

    # Resolve filenames against the vault + this batch, tracking what we reserve so
    # a write failure can release the names.
    reserved: list[str] = []
    rendered: list[tuple[str, str]] = []
    for note in notes:
        filename = unique_filename(note.title, taken)
        # TODO: path(filename).stem.lower()  -> more readable
        reserved.append(filename[:-3].lower())  # stem, matching `taken` entries
        rendered.append((filename, render_note(note, processed, config.pipeline_stamp)))

    if dry_run:
        # Release reservations: nothing was written, names stay free for a real run.
        for stem in reserved:
            taken.discard(stem)
        return SourceResult(page=page, status="ok", notes=notes)

    try:
        written = vault_mod.write_notes_atomic(notes_dir, rendered)
    except Exception as exc:
        for stem in reserved:
            taken.discard(stem)
        return SourceResult(page=page, status="error", reason=f"write failed: {exc}")

    if not eval_mode:
        vault_mod.move_draft_to_done(path, done_dir)
    return SourceResult(page=page, status="ok", notes=notes, written_paths=written)


def _count_non_md(inbox: Path) -> int:
    """Count non-markdown files under the inbox (excluding ``_done/``). Never touched."""
    if not inbox.exists():
        return 0
    count = 0
    for p in inbox.rglob("*"):
        if not p.is_file() or p.suffix.lower() == ".md":
            continue
        if "_done" in p.relative_to(inbox).parts:
            continue
        count += 1
    return count


def _stub_page(path: Path, source_name: str) -> SourcePage:
    """Minimal SourcePage so a parse failure still has something to report."""
    return SourcePage(
        path=path,
        source=source_name,
        source_id=path.name,
        export_path="",
        title=path.stem,
        raw_body="",
    )
