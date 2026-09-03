---
summary: Schema mid-bump gates sq — run it from an exported HEAD
created_at: '2026-08-26T16:28:00Z'
---
When another agent is mid-way through a schema bump in the same tree, `SCHEMA_VERSION` in the
source and the squad's own `.squads.toml` stamp disagree, and every `sq` command hard-stops on
the gate — including the read-only ones a writer needs (`sq <type> <n> show`, `sq check`).

Do not fix it by running `sq migrate up` (that rewrites the squad, and it is the other agent's
work), and do not edit `_models/_schema.py`.

Run `sq` from an exported copy of HEAD instead, whose schema constant still matches the
on-disk squad:

    git archive HEAD src | tar -x -C /tmp/head-src
    PYTHONPATH=/tmp/head-src/src .venv/bin/python -c "from squads._cli import app; app()" <args>

PYTHONPATH wins over the editable install, so this reads and writes the squad with exactly the
code that wrote it. Re-check the stamp between commands — the other agent may land the
migration mid-session, at which point the plain `uv run sq` starts working again and the
exported copy starts failing with the mirror-image "squad is newer than the package" error.

Doc-suite failures during such a window are usually the gate, not your edits: `sq docs` walks
up to the repo's own `.squads.toml`, so `tests/cli/test_docs_cli.py` fails wholesale. Re-run
once the stamps agree before reporting a regression.