"""Run-report accumulation and rendering.

Every run produces one report: per source ok/skipped/error (+ reason), outlier
flags, the count of non-markdown files seen (counted, never touched), and totals.
It doubles as the iteration-review tool. ``--dry-run`` prints the same summary and
writes no file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from volundr.models import SourceResult


@dataclass
class RunReport:
    source: str
    dry_run: bool
    started: datetime = field(default_factory=datetime.now)
    results: list[SourceResult] = field(default_factory=list)
    non_md_count: int = 0

    def add(self, result: SourceResult) -> None:
        self.results.append(result)

    # --- totals ---
    @property
    def ok(self) -> list[SourceResult]:
        return [r for r in self.results if r.status == "ok"]

    @property
    def skipped(self) -> list[SourceResult]:
        return [r for r in self.results if r.status == "skipped"]

    @property
    def errored(self) -> list[SourceResult]:
        return [r for r in self.results if r.status == "error"]

    @property
    def notes_written(self) -> int:
        return sum(len(r.notes) for r in self.ok)

    @property
    def outliers(self) -> list[tuple[str, str]]:
        """(note title, flag) pairs across all OK results, for the report."""
        out: list[tuple[str, str]] = []
        for r in self.ok:
            for note in r.notes:
                if note.too_short:
                    out.append((note.title, "too_short"))
                if note.too_long:
                    out.append((note.title, "too_long"))
        return out

    def to_markdown(self) -> str:
        mode = "DRY RUN — nothing written" if self.dry_run else "write"
        stamp = self.started.strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"# VÖLUNDR run report — {stamp}",
            "",
            f"- source: `{self.source}`",
            f"- mode: {mode}",
            f"- pages: {len(self.results)} "
            f"(ok {len(self.ok)}, skipped {len(self.skipped)}, error {len(self.errored)})",
            f"- notes {'would be ' if self.dry_run else ''}written: {self.notes_written}",
            f"- non-markdown files seen (untouched): {self.non_md_count}",
            "",
            "## Per source",
            "",
        ]
        for r in self.results:
            head = f"- **{r.status}** — `{r.page.path.name}`"
            if r.reason:
                head += f" — {r.reason}"
            lines.append(head)
            for note in r.notes:
                flags = [f for f, on in
                         (("too_short", note.too_short), ("too_long", note.too_long)) if on]
                suffix = f"  _({', '.join(flags)})_" if flags else ""
                lines.append(f"    - {note.title}{suffix}")

        if self.outliers:
            lines += ["", "## Length outliers", ""]
            lines += [f"- {title} — {flag}" for title, flag in self.outliers]

        return "\n".join(lines) + "\n"

    def console_summary(self) -> str:
        verb = "would write" if self.dry_run else "wrote"
        return (
            f"{self.source}: {len(self.ok)} ok / {len(self.skipped)} skipped / "
            f"{len(self.errored)} error — {verb} {self.notes_written} notes "
            f"({self.non_md_count} non-md files untouched)"
        )

    def write(self, logs_dir: Path) -> Path:
        """Persist the report to ``_META/logs/run-<timestamp>.md`` and return its path."""
        logs_dir.mkdir(parents=True, exist_ok=True)
        path = logs_dir / f"run-{self.started.strftime('%Y%m%d-%H%M%S')}.md"
        path.write_text(self.to_markdown(), encoding="utf-8")
        return path
