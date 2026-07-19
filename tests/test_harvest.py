"""Tests for Stage 2 tag harvesting, normalisation, and extraction logic."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from volundr.harvest import (
    STOP_WORDS,
    _singularize_word,
    detect_and_parse,
    extract_from_headings,
    extract_tfidf,
    normalize_tag,
    query_ollama_for_tags,
)
from volundr.models import SourcePage


def test_normalize_tag():
    assert normalize_tag("GameDEV") == "gamedev"
    assert normalize_tag("Obsidian-Setup!") == "obsidian-setup"
    assert normalize_tag("Routing Rules") == "routing-rule"
    assert normalize_tag("dependencies") == "dependency"
    assert normalize_tag("categories") == "category"
    assert normalize_tag("classes") == "class"
    assert normalize_tag("analyses") == "analysis"
    assert normalize_tag("MESES") == "mes"
    assert normalize_tag("actrices") == "actriz"
    assert normalize_tag("motores") == "motor"
    assert normalize_tag("   ") == ""


def test_singularize_word():
    # Exceptions
    assert _singularize_word("kubernetes") == "kubernetes"
    assert _singularize_word("css") == "css"
    assert _singularize_word("alias") == "alias"
    assert _singularize_word("postgres") == "postgres"
    
    # Spanish singularization
    assert _singularize_word("ciudades") == "ciudad"
    assert _singularize_word("sociales") == "sociale"
    assert _singularize_word("actrices") == "actriz"
    assert _singularize_word("papeles") == "papele"
    
    # English/General singularization
    assert _singularize_word("dependencies") == "dependency"
    assert _singularize_word("processes") == "process"
    assert _singularize_word("boxes") == "box"
    assert _singularize_word("runs") == "run"


def test_extract_from_headings():
    page = SourcePage(
        path=Path("dummy.md"),
        source="manual",
        source_id="dummy",
        export_path="",
        title="Python Development Notes",
        raw_body=(
            "Some introductory text.\n\n"
            "# FastAPI Routing\n\n"
            "FastAPI handles routing nicely.\n\n"
            "## Code Examples\n\n"
            "Here is a code block."
        ),
    )
    
    candidates = extract_from_headings(page)
    
    # Title words: "python", "development"
    # Heading 1 phrase: "fastapi-routing"
    # Heading 1 words: "fastapi", "routing"
    # Heading 2 words: "code", "example"
    # Check that they exist in candidates
    assert "python" in candidates
    assert "development" in candidates
    assert "fastapi-routing" in candidates
    assert "fastapi" in candidates
    assert "routing" in candidates
    assert "code" in candidates
    assert "example" in candidates
    
    # Verify stop words or metadata words are filtered out (like "notes" -> "note")
    assert "note" not in candidates


def test_extract_tfidf():
    page1 = SourcePage(
        path=Path("p1.md"),
        source="manual",
        source_id="p1",
        export_path="",
        title="Python coding",
        raw_body="python python python code code logic.",
    )
    page2 = SourcePage(
        path=Path("p2.md"),
        source="manual",
        source_id="p2",
        export_path="",
        title="FastAPI project",
        raw_body="fastapi routing web app api.",
    )
    
    results = extract_tfidf([page1, page2], top_k=2)
    
    # "python" is in page1 but not page2, so its IDF and TF should make it top candidate
    assert "python" in results[page1.path]
    # "fastapi" is in page2 but not page1
    assert "fastapi" in results[page2.path]


def test_query_ollama_for_tags_success():
    mock_response = MagicMock()
    # Mocking response as a JSON string with format-compliant structure
    mock_response.read.return_value = b'{"message": {"content": "{\\"tags\\": [\\"python\\", \\"unit-testing\\"]}"}}'
    mock_response.__enter__.return_value = mock_response
    
    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        tags = query_ollama_for_tags(
            "http://localhost:11434", "llama3.1", "Test Title", "Test content"
        )
        assert tags == ["python", "unit-testing"]
        mock_urlopen.assert_called_once()


def test_query_ollama_for_tags_connection_error():
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        with pytest.raises(ConnectionError, match="Ollama connection failed"):
            query_ollama_for_tags(
                "http://localhost:11434", "llama3.1", "Test Title", "Test content"
            )


def test_detect_and_parse(tmp_path):
    # Notion file
    notion_file = tmp_path / "notion file 1d6d59967d4280df8d20c10af9378e86.md"
    notion_file.write_text("# Notion Title\n\nbody.", encoding="utf-8")
    
    page = detect_and_parse(notion_file, tmp_path)
    assert page.source == "notion"
    assert page.source_id == "1d6d59967d4280df8d20c10af9378e86"
    
    # Capacities file
    cap_dir = tmp_path / "capacities"
    cap_dir.mkdir()
    cap_file = cap_dir / "cap file.md"
    cap_file.write_text(
        "---\ntype: 'AtomicNote'\ntitle: Cap Title\ntags: [tag1]\n---\n\n# Cap Title\n\nbody.",
        encoding="utf-8"
    )
    page_cap = detect_and_parse(cap_file, tmp_path)
    assert page_cap.source == "capacities"
    assert page_cap.tags == ["tag1"]
    
    # Manual file without frontmatter
    man_file = tmp_path / "manual file.md"
    man_file.write_text("# Manual Title\n\nbody.", encoding="utf-8")
    page_man = detect_and_parse(man_file, tmp_path)
    assert page_man.source == "manual"
    assert page_man.tags == []
