"""VÖLUNDR command-line interface (Typer).

Commands:
  run       process 0_INBOX/ drafts into the vault (Stage 1, deterministic)
  harvest   Stage 2 — tag-vocabulary bootstrap (not implemented yet)
  promote   Stage 5 — promote candidate tags (not implemented yet)
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import typer

from volundr.config import DEFAULT_CONFIG_PATH, load_config
from volundr import pipeline
from volundr.harvest import harvest_inbox

app = typer.Typer(
    add_completion=False,
    help="Enrich markdown drafts into an Obsidian vault (local, minimal-maintenance).",
)


# añado sources (tiene mas trabajo en sources folder)
class SourceName(str, Enum):
    notion = "notion"
    capacities = "capacities"
    keep = "keep"
    manual = "manual"


# runs pipeline passing configurations -
@app.command()
def run(
    source: SourceName = typer.Option(
        SourceName.manual, "--source", help="Which export the drafts came from."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print what would be created; write nothing."
    ),
    eval_mode: bool = typer.Option(
        False, "--eval", help="Write to _META/eval/runs/<version>/ instead of 1_NOTES/."
    ),
    config_path: Path = typer.Option(
        DEFAULT_CONFIG_PATH, "--config", help="Path to config.yaml."
    ),
) -> None:
    """Split & import every draft in 0_INBOX/ for the chosen source."""
    config = load_config(config_path)
    report = pipeline.run(config, source.value, dry_run=dry_run, eval_mode=eval_mode)

    if dry_run:
        typer.echo(report.to_markdown())
    typer.echo(report.console_summary())
    # TODO: error handling
    if report.errored:
        raise typer.Exit(code=1)


# ------ STAGE COMMANDS ------
@app.command()
def harvest(
    config_path: Path = typer.Option(
        DEFAULT_CONFIG_PATH, "--config", help="Path to config.yaml."
    ),
    source_filter: SourceName = typer.Option(
        None, "--source", help="Only harvest from a specific source folder (optional)."
    ),
) -> None:
    """Bootstrap the tag vocabulary from the corpus (Stage 2)."""
    config = load_config(config_path)
    from volundr import vault as vault_mod
    vault_mod.ensure_layout(config.vault_path)
    
    source_val = source_filter.value if source_filter else None
    harvest_inbox(config, source_val)


@app.command()
def promote(
    dry_run: bool = typer.Option(False, "--dry-run"),
    config_path: Path = typer.Option(DEFAULT_CONFIG_PATH, "--config"),
) -> None:
    """Promote candidate tags to approved and retro-apply them (Stage 5)."""
    typer.echo("promote: not implemented yet (Stage 5 — tag promotion).")
    raise typer.Exit(code=2)


if __name__ == "__main__":
    app()
