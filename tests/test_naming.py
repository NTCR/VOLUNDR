"""Filename sanitisation and collision suffixing."""

from __future__ import annotations

from volundr.naming import sanitize_filename, unique_filename


def test_strips_forbidden_characters():
    assert sanitize_filename("a/b:c#d^e[f]g|h") == "abcdefgh"


def test_collapses_whitespace_and_trims():
    assert sanitize_filename("  hello   world  ") == "hello world"


def test_caps_length_to_80():
    assert len(sanitize_filename("x" * 200)) == 80


def test_empty_title_falls_back():
    assert sanitize_filename("///") == "untitled"


def test_unique_filename_suffixes_on_collision():
    taken: set[str] = set()
    assert unique_filename("Note", taken) == "Note.md"
    assert unique_filename("Note", taken) == "Note 2.md"
    assert unique_filename("Note", taken) == "Note 3.md"


def test_unique_filename_collision_is_case_insensitive():
    taken = {"note"}
    assert unique_filename("Note", taken) == "Note 2.md"


def test_unique_filename_checks_against_existing_vault_stems():
    # Simulates 1_NOTES already containing "idea".
    taken = {"idea"}
    assert unique_filename("idea", taken) == "idea 2.md"
