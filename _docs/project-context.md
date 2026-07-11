# VÖLUNDR — project context for coding agents

> Snapshot for AI context, distilled from the Notion page "VÖLUNDR (pkm)"
> (source of truth: https://www.notion.so/V-LUNDR-pkm-399d59967d4280699c4edfcdbc3499ec).
> If this file and Notion disagree, **Notion wins** — this is a cache, refreshed
> manually when decisions change. Naming: always `VOLUNDR` in code/files/folders
> (never `VÖLUNDR`, to avoid encoding issues).

## What this is

A personal PKM pipeline: durable storage of the user's knowledge in Obsidian,
made accessible/visualizable without re-reading everything, able to surface
new connections.

Two components:
1. **Processing flow** — Python CLI + Ollama (local LLM) that enriches `.md`
   drafts with frontmatter.
2. **Obsidian** — third-party plugins for visualization/retrieval (no custom
   tooling built where a plugin already solves it).

**Constraints:** minimal maintenance · local LLM processing (Ollama) · don't
build what a plugin already solves · pipeline output (tags) in English.

**Phases:** Phase 1 = iterative migration of real Notion/Capacities exports,
inspect results in Obsidian, refine. Phase X (later, not built yet) = daily
workflow automation, Drive export, non-md files, wikilink expansion, tag
suggestions.

## Vault layout (script contract)

```
VAULT/
├── 0_INBOX/           # pending drafts (manual + migration input, nested OK)
│   └── _done/         # processed, awaiting manual verification & deletion
├── 1_NOTES/           # processed notes, flat
├── _ATTACHMENTS/      # images/files
├── _META/
│   ├── tags.yaml      # vocabulary: approved + candidates
│   ├── logs/          # run reports
│   ├── harvest/       # harvest pass output
│   └── eval/          # eval sample drafts + score sheets
```

- Reads `0_INBOX/` recursively, `.md` only. Non-md files are counted in the
  run report, never touched.
- Writes to `1_NOTES/`, flat, append-only (import never edits/deletes
  existing notes).
- Success → draft moves to `0_INBOX/_done/` (deletion stays manual).
- Failure → draft stays in place, per-source rollback (temp → move pattern).
- Filenames: sanitized English titles (strip `/ \ : # ^ [ ] |`, cap ~80
  chars), numeric suffix on collision (checked against all of `1_NOTES/`,
  not just the current batch).
- Folders encode **workflow state only**. Topics live in tags, dates in
  frontmatter. No topic folders, no by-source/by-year subdivision, no
  zettel-style filename prefixes.

## Splitting (1 source page → N notes)

Deterministic, heading-based. **No LLM in splitting.**

- One note per heading with *direct* body text (text before its first
  subheading). Headings with no direct text emit no note — they only extend
  the context chain. Heading-less page = whole page is one note.
- Title = heading, verbatim, deterministic (no LLM).
- Granularity is authored by the human via headings at write time — the
  script never second-guesses it.
- Length never alters the split — it only flags outliers (too long / too
  short) in the run report. Fix loop: user edits headings, re-runs.
- Short notes (below min threshold): `summary` is skipped entirely
  (deterministic). Still get tags via the context chain.
- Both length thresholds are tuned on the eval harness sample, not guessed.

## Frontmatter schema (canonical)

```yaml
---
title: <heading verbatim>            # deterministic
created: <native export date>        # deterministic — omitted if export has none
processed: <run date>                # deterministic
source: notion | keep | capacities | manual   # deterministic, from --source flag
source_id: <native ID; draft filename for manual>  # deterministic
context: "Export path > Page title > H1 > H2"      # deterministic, single string
pipeline: v1                         # deterministic, from config.yaml version
type: atomic-note | reflection | quote | definition | comparison  # LLM
tags: []                             # LLM, validated against tags.yaml
proposed_tags: []                    # validator output (unknown tags)
summary: "1-2 lines"                 # LLM — skipped below min length threshold
---
```

- `context` is plain text, **never wikilinks** — provenance + prompt input,
  not navigation.
- `created`: no file-mtime fallback. Missing native date = field omitted.
- `type` is cheap metadata only — nothing is built on top of it (no
  per-type Bases views, no hub/MOC notes).

## Linking / retrieval model

Topic-centric: **tags + human-made wikilinks + Smart Connections**.
Frontmatter-only — no linking machinery gets built. This makes the tag
vocabulary the load-bearing piece of the whole system.

## Tag vocabulary

- Flat controlled vocabulary in `_META/tags.yaml`: `approved` (canonical +
  aliases) and `candidates` (waiting room, with counters).
- **Script enforces it, not the prompt.** Per note: tag in approved → ok;
  tag is alias → mapped to canonical; unknown → appended to `candidates`
  (counter++) and written to the note's `proposed_tags` (never into `tags`,
  never dropped).
- `promote` is an explicit, separate, dry-runnable command: updates
  `tags.yaml`, then retro-applies newly approved tags to notes whose
  `proposed_tags` contain them. Frontmatter-only, preserves everything else
  verbatim.
- Conventions: English, lowercase, singular, kebab-case. 1–5 tags per note,
  target 3 — never force a count.
- Bootstrap (harvest pass, writes no notes): 4 sources — human tags in
  exports, headings/titles, deterministic keyword extraction (TF-IDF/YAKE),
  LLM free-tagging. Aggregate by frequency, review top ~50 → vocabulary v1.

## LLM call contract

One call per note → `type` + `tags` + `summary`, JSON via **Ollama
structured outputs** (schema-enforced, not regex-parsed). On failure
(timeout, invalid values, empty output): 1 retry, then the whole source
page rolls back (draft stays in `0_INBOX/`, reason logged). One prompt for
all types — no per-type prompt variants (revisit only if eval scores show
one type consistently failing).

## Ingestion

Source is **declared, never guessed**: `--source notion|capacities|keep`
per run, default `manual`. `source_id` = native ID (Notion UUID, Capacities
object ID) or draft filename for manual. Missing expected ID = loud
per-source error, never a silent fallback. Phase 1 explicitly accepts
broken attachment/wikilinks in migrated bodies (pass-through) — link
fixing is Phase X.

## Migration robustness

- **Append-only vault**: import never edits/deletes existing notes; note
  *content* is never touched by any command; frontmatter maintenance only
  via separate, explicit, dry-runnable commands (e.g. `promote`).
- **Per-source atomicity**: all-or-nothing per source page (temp → move),
  rollback on error, resumable by re-running.
- **Run report** per run in `_META/logs/`: per source, ok/skipped/error +
  reason, plus totals.
- **`--dry-run`**: prints what would be created, writes nothing.
- **`pipeline: vN`** stamped in every note, ties back to `config.yaml`
  version.
- Dedup is **not** pre-checked — detectable on demand via a `source_id`
  group-by query if suspected, not a cost paid on every run.

## Config

Single `config.yaml`: vault path, model name, Ollama endpoint, length
thresholds, prompt file path, `version`. Per-run behavior
(`--source`, `--dry-run`, `--eval`, `promote`) stays on the CLI. Config
history = git diffs. `version` bumped by hand when prompt/model/thresholds
change meaningfully.

## Quality evaluation

Fixed ~20-page eval harness (diverse: long/short, ES/EN, with/without
headings, junk intros, heading-less long pages). `--eval` mode writes to
`_META/eval/runs/<pipeline-version>/`, **never** `1_NOTES/`. Checklist per
note: tags findable? summary useful? (✅/❌, N/A for skipped summaries).
Models are chosen by score on this harness, not reputation — run 2–3 Ollama
candidates, pick by score.

## Obsidian setup (Phase 1)

Core **Bases** + **Smart Connections** only — Dataview deliberately
deferred (adopt only if a needed query outgrows Bases). Starter Bases
views: recent imports (by `processed`), notes by tag, dedup check (group by
`source_id`, count > 1), `proposed_tags` review.

## Build order (one-off, not the daily flow)

`harvest → vocabulary v1 → eval harness → bulk migration`. Each step needs
the previous one.

**Suggested implementation stages:**

1. **Stage 0 — Scaffolding**: repo layout, `config.yaml`, CLI skeleton
   (`run`, `harvest`, `promote`, `--source`, `--dry-run`, `--eval`), vault
   folders, run-report writer stub, install Smart Connections + 4 Bases
   views.
2. **Stage 1 — Deterministic core (no LLM)**: Notion/Capacities parsers,
   heading-based splitter + context chain, filename sanitizer/collision
   check, deterministic frontmatter writer, per-source atomicity,
   `--dry-run`, run report. *Milestone: dry-run over a slice of real Notion
   export produces correct notes with empty LLM fields.*
3. **Stage 2 — Harvest → vocabulary v1**: 4 extractors → frequency table in
   `_META/harvest/`, manual review of top ~50 → `tags.yaml` v1. First
   Ollama touchpoint.
4. **Stage 3 — Enrichment + validation**: single LLM call w/ structured
   outputs, retry+rollback, tag validator, length thresholds, `pipeline`
   stamping. *Milestone: end-to-end run on the same slice, notes land in
   `1_NOTES/`, drafts move to `_done/`.*
5. **Stage 4 — Eval harness**: curate ~20-page sample, `--eval` mode,
   scoresheet format, run/score 2–3 Ollama models. *Gate: don't proceed
   until scores satisfy you.*
6. **Stage 5 — Bulk migration**: per source, `--dry-run` → review → real
   run → inspect via Bases → delete verified drafts. Notion first, then
   Capacities. Build `promote` here (no consumer until this point).

Stage 1 is deliberately the heavy one (zero LLM iteration needed). Freeze
the eval sample from Stage 4 on so later prompt tweaks stay comparable.

## Repo layout

```
VOLUNDR/                       # project root (flattened — this IS the git repo)
├── CLAUDE.md                  # entry-point instructions for the coding agent
├── _docs/
│   └── project-context.md     # this file
├── pyproject.toml             # poetry
├── src/volundr/                # package code
├── tests/
├── notion-exports/            # raw input data, gitignored
├── capacities-exports/        # raw input data, gitignored
└── decisions-digest-to-elaborate.md   # early scratch notes, superseded by Notion
```

## User profile (conditions every suggestion)

- **Efficiency first**: no prior Obsidian experience — if a plugin/library
  already solves something, suggest it before proposing custom code.
- **Minimal maintenance**: manual execution is a deliberate decision, not a
  gap. Automation deferred to Phase X.
- **Privacy**: local-first (Ollama). Prefer alternatives that reduce dev
  complexity over anything that breaks local-first.
- **Level**: junior developer, comfortable with Python and growing —
  explain Obsidian/plugin concepts, don't assume them.
- **Goal**: automate processing/tagging to free time for creative work,
  idea association, and reflection.
