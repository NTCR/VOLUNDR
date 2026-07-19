# Walkthrough: Stage 2 Implementation (Tag Vocabulary Harvest)

We have successfully implemented and verified **Stage 2** (Vocabulary Harvest) of the VÖLUNDR pipeline. The new `harvest` command allows bootstrapping the tag vocabulary from the unprocessed drafts in the `0_INBOX/` folder.

## Changes Made

### 1. Source Parsers & Models
- **[models.py](file:///Users/naito/0_repos/VOLUNDR/src/volundr/models.py)**: Added the `tags` list field to the `SourcePage` model.
- **[capacities.py](file:///Users/naito/0_repos/VOLUNDR/src/volundr/sources/capacities.py)**: Updated to parse frontmatter metadata `tags` and assign them to the parsed `SourcePage`.
- **[notion.py](file:///Users/naito/0_repos/VOLUNDR/src/volundr/sources/notion.py)**:
  - Updated `ManualSource.parse` to check if a manual note starts with frontmatter. If so, it parses the metadata/tags using `frontmatter.loads`; otherwise, it uses the standard header-splitting fallback.
  - Initialised `tags=[]` by default for the vintage `NotionSource` exports.

### 2. Core Extraction & CLI Integration
- **[harvest.py](file:///Users/naito/0_repos/VOLUNDR/src/volundr/harvest.py)**: Created the harvest logic combining:
  1. **Human Tags Extractor**: Frontmatter tags.
  2. **Headings/Title Extractor**: Individual normalised words + short heading phrases (1-2 words).
  3. **TF-IDF Keyword Extractor**: Statistical term-frequency extraction over the corpus.
  4. **Ollama LLM Extractor**: Queries Ollama via structured JSON outputs (`format` payload) for up to 5 suggested tags in English.
  - Implemented tag normalisation (lowercase, kebab-case, singularisation) and stop words filtering for both English and Spanish text.
- **[cli.py](file:///Users/naito/0_repos/VOLUNDR/src/volundr/cli.py)**: Wired the CLI command `volundr harvest` to accept config file path and optional source filtering.

---

## Verification Results

### 1. Automated Tests
We created a new test suite in **[test_harvest.py](file:///Users/naito/0_repos/VOLUNDR/tests/test_harvest.py)** that verifies:
- Accent removal, kebab-casing, and correct English/Spanish singularisation.
- Exclusions list logic (e.g. `kubernetes`, `css`, `basis` remain unchanged).
- Heading word and phrase candidate generation.
- Term frequency calculations and top TF-IDF selection.
- Mocked Ollama API payloads and connection/socket error handling.

All 39 tests in the pytest suite are passing successfully:
```bash
poetry run pytest
============================== 39 passed in 0.10s ==============================
```

### 2. Manual Verification
We ran `poetry run volundr harvest` against the active Obsidian vault (`~/1_PKM/NaitoPKM`). It successfully parsed all 103 drafts in the inbox and generated the markdown table at `_META/harvest/tags_frequency.md`.

Here is a snippet of the top 10 tags harvested from the inbox corpus:

| Rank | Tag Candidate | Total Freq | Human Tags | Headings/Title | TF-IDF | LLM Suggested |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `python` | 42 | 0 | 18 | 3 | 21 |
| 2 | `http` | 16 | 0 | 10 | 2 | 4 |
| 3 | `soap` | 16 | 0 | 13 | 2 | 1 |
| 4 | `devop` | 14 | 0 | 7 | 1 | 6 |
| 5 | `software` | 13 | 0 | 11 | 1 | 1 |
| 6 | `interaccion` | 13 | 0 | 10 | 3 | 0 |
| 7 | `servicio` | 13 | 0 | 11 | 2 | 0 |
| 8 | `opengl` | 12 | 0 | 6 | 2 | 4 |
| 9 | `computer-graphic` | 11 | 0 | 0 | 0 | 11 |
| 10 | `api` | 11 | 0 | 7 | 1 | 3 |

### 3. Resilience Testing
We pointed `ollama_endpoint` to a non-existent port (`http://localhost:9999`) in `config.yaml` and ran the harvest. The tool logged a warning and successfully executed the harvest using the remaining 3 extractors in under 1 second:
```
[WARNING] Ollama server not reachable at http://localhost:9999.
Skipping Extractor 4 (LLM free-tagging) and harvesting with the remaining 3 extractors.
```
This guarantees the command is robust and won't crash when Ollama is unavailable.
