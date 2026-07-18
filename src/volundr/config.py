"""Load and validate the single ``config.yaml``.

Per-run behaviour (``--source``, ``--dry-run``, ``--eval``) stays on the CLI.
Everything here is stable-per-config; its history is the git diff of ``config.yaml``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML

DEFAULT_CONFIG_PATH = Path("config.yaml")


@dataclass(frozen=True)
class Lengths:
    """Body-length thresholds (characters). Stage 1 only flags outliers."""

    min_chars: int
    max_chars: int


@dataclass(frozen=True)
class Config:
    vault_path: Path
    model: str
    ollama_endpoint: str
    length: Lengths
    prompt_file: str
    version: int

    @property
    def pipeline_stamp(self) -> str:
        """The value written to a note's ``pipeline:`` frontmatter field."""
        return f"v{self.version}"


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> Config:
    """Read ``config.yaml`` into a frozen :class:`Config`.

    Raises a clear error on a missing file or missing required key rather than
    silently falling back to defaults — config mistakes should be loud.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Config not found: {path}. Copy the template and set `vault_path`."
        )

    yaml = YAML(typ="safe")
    data = yaml.load(path.read_text(encoding="utf-8")) or {}

    try:
        length = data["length"]
        return Config(
            vault_path=Path(data["vault_path"]).expanduser(),
            model=data["model"],
            ollama_endpoint=data["ollama_endpoint"],
            length=Lengths(
                min_chars=int(length["min_chars"]),
                max_chars=int(length["max_chars"]),
            ),
            prompt_file=data["prompt_file"],
            version=int(data["version"]),
        )
    except KeyError as exc:
        raise KeyError(f"Missing required config key: {exc.args[0]}") from exc
