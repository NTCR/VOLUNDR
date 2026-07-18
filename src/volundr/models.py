"""Core dataclasses passed between pipeline stages.

The flow is: a source file on disk -> :class:`SourcePage` (parsed) ->
one or more :class:`Note` (split) -> written to the vault, with the outcome
captured in a :class:`SourceResult` for the run report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SourcePage:
    """One source file (a Notion/Capacities page) after parsing, before splitting."""

    path: Path            # the draft file inside 0_INBOX/
    source: str           # notion | capacities | keep | manual
    source_id: str        # native ID (Notion UUID, Capacities object id) or filename
    export_path: str      # path relative to the export root, for the context chain
    title: str            # page title (verbatim)
    raw_body: str         # markdown body below the title (frontmatter/title stripped)
    native_created: str | None = None  # source-native date, or None when absent


@dataclass
class Note:
    """One atomic note produced by the splitter, ready for the frontmatter writer.

    Deterministic fields are filled in Stage 1. The LLM fields
    (``type``/``tags``/``proposed_tags``/``summary``) stay empty here — Stage 3
    fills them. ``too_long`` / ``too_short`` are report-only flags; they never
    change how the page was split.
    """

    title: str                      # heading verbatim (deterministic)
    context: str                    # "Export path > Page title > H1 > H2" (plain text)
    source: str
    source_id: str
    body: str
    created: str | None = None

    # --- Stage 3 seam: intentionally empty in Stage 1 ---
    type: str | None = None
    tags: list[str] = field(default_factory=list)
    proposed_tags: list[str] = field(default_factory=list)
    summary: str | None = None

    # --- report-only outlier flags (do not affect splitting) ---
    too_long: bool = False
    too_short: bool = False


@dataclass
class SourceResult:
    """Outcome of processing one source page — the unit of the run report."""

    page: SourcePage
    status: str                     # "ok" | "skipped" | "error"
    notes: list[Note] = field(default_factory=list)
    reason: str | None = None       # populated for skipped / error
    written_paths: list[Path] = field(default_factory=list)
