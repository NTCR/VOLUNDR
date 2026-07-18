"""Shared test fixtures."""

from __future__ import annotations

import pytest

from volundr.config import Config, Lengths


@pytest.fixture
def config() -> Config:
    """A Config with small thresholds so tests can exercise outlier flags."""
    return Config(
        vault_path="/tmp/does-not-matter",
        model="test",
        ollama_endpoint="http://localhost:11434",
        length=Lengths(min_chars=20, max_chars=200),
        prompt_file="prompts/enrich.txt",
        version=1,
    )
