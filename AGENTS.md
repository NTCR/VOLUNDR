This is the root folder for the development of the VÖLUNDR project.
(Always written VOLUNDR in code, files and folders to avoid encoding errors)

This folder is both the project root and the git/poetry repo — pyproject.toml,
src/, and tests/ live here directly.

The human documentation is managed by me in Notion:
https://www.notion.so/V-LUNDR-pkm-399d59967d4280699c4edfcdbc3499ec

The documentation in `_docs/` is AI-oriented, to bring the necessary context
to the agent without needing Notion access. Read `_docs/project-context.md`
first — it's a distilled snapshot of the Notion page (architecture,
decisions, schema, build plan). Notion is always the source of truth; if
they disagree, Notion wins and `_docs/project-context.md` should be
refreshed.

`decisions-digest-to-elaborate.md` at the root is an early scratch draft,
superseded by the Notion page and `_docs/project-context.md` — kept for
history only.