# TO ELABORATE — Decisions digest (2026-07-10)

## 1. Atomic note splitting (1→N)

✅ **Decided:** deterministic, heading-based split. No LLM involved in splitting.
**Usage note:** input is divided by headings — the user must use headings to separate ideas and concepts.
**Discarded:** LLM-driven and hybrid splitting — non-reproducible, hard to debug in bulk. LLM stays confined to enrichment.
🔄 **Open (algorithm design session):** nesting rules (leaf vs. parent headings, what happens to parent intro text), heading-as-title + parent chain in frontmatter, no-headings case (whole page = one note), minimum-length rule.

## 2. "Object" concept

✅ **Decided:** discarded as a visualization/retrieval feature. Retrieval is topic-centric: tags + wikilinks + Smart Connections.
`type` survives only as a pipeline-internal hint (picks the enrichment prompt/structure); stays in frontmatter as cheap metadata, but nothing is built on top of it.
**Discarded:** object convention via `type` + one Bases view per type — answers a question ("show me all notes of type X") I don't ask. My question is "show me all artifacts related to a topic".

## 3. Vault structure

✅ **Decided:** minimal layout —

```
VAULT/
├── 0_INBOX/         # drafts to process (manual + migration input)
├── 1_NOTES/         # processed notes, flat
├── _ATTACHMENTS/    # images/files
├── _META/           # tags.yaml, templates, logs — anything the script reads/writes
```

Folders encode workflow state only; topics live in tags. Filenames = descriptive English titles, numeric suffix on collision.
Script contract: read `0_INBOX/`, write `1_NOTES/`, on failure leave the draft in place.
**Discarded:** topic folders (duplicate the tag system), by-source/by-year subdivision (redundant with frontmatter), date/zettel filename prefixes (dates live in frontmatter).
🔄 **Open (Phase X):** attachment handling — copy into vault + rewrite links?

## 4. Tag vocabulary

✅ **Decided:** flat controlled list in a file (`_META/tags.yaml`). The script validates LLM output against it — tags outside the list are dropped/mapped. The prompt alone is never trusted.
**Pressure valve:** the LLM picks 3–5 tags from the list and may propose 1 candidate → goes to `proposed_tags` / review file, never into `tags`. Periodic manual promotion.
**Bootstrap:** harvest pass over the real corpus (free-tag into candidates only, count frequencies, consolidate top ~50 once) → vocabulary v1. Then the real import runs against it.
**Conventions:** English, lowercase, singular, kebab-case. Flat — nesting can be retrofitted.
**Discarded:** open tagging + curate later (cleaning thousands of notes after the fact); nested taxonomy upfront (forces premature design).

## 5. Quality evaluation

✅ **Decided:** body pass-through — the LLM only adds metadata, never touches note content. Lost/invented content becomes structurally impossible.
**Eval harness:** fixed diverse sample (~20 real drafts: long/short, ES/EN, with/without headings). ✅/❌ checklist per output: tags findable? summary useful? Re-run the same sample per pipeline config (model × prompt) and compare scores.
Model choice is decided on the harness, not in the abstract.

## 6. Maintenance tension

✅ **Decided:** manual execution is a decision, not a gap. Maintenance ≠ operation — automation is what adds maintenance (daemons, watchers, silent failures). Deferred to Phase X, when daily-flow friction is known.
**Candidate paths, ranked by maintenance cost:** hotkey/alias → `launchd`/cron on schedule → folder watcher (last resort).
Prerequisite for any automation: point 8 safety.

## 7. Language handling

✅ **Decided:** English metadata over original-language content. Body untouched (Spanish stays Spanish); everything the pipeline generates (tags, summary, split titles, vocabulary) is English. Retrieval always happens in English.
**Discarded:** translating content — reintroduces the content manipulation eliminated in point 5.

## 8. Migration robustness

✅ **Decided:**

- **Append-only vault:** the script never edits or deletes existing notes.
- **Per-source atomicity:** the N notes from one source page are written all-or-nothing (temp → move); any error rolls the page back and leaves its draft in `0_INBOX`. One bad page can't poison a batch; interrupted runs resume by re-running.
- **Run report:** per-run log in `_META/logs/` — per source: ok / skipped / error + reason, plus totals. Doubles as the iteration review tool.
- **`--dry-run`:** prints what would be created without writing.
- **`pipeline: v1` frontmatter field:** records which prompt/config produced each note. Enables "re-process everything from v1" as a query, and later per-task model routing (light model for summaries, stronger where it matters).

**Dedup demoted to detectability:** no pre-checks, no `--force`, re-import is not a fatal error. `source_id` (already in frontmatter) makes duplicates queryable (group by `source_id`, count > 1) if human error is ever suspected. Original drafts are deleted manually after verified processing.
**Discarded:** idempotence machinery — its cost lands in edge cases (skip/force logic vs. notes already edited or linked), and the risk it covers is human error in a supervised manual process.
