---
id: BUG-704
sequence_id: 704
type: bug
title: A missing index tracebacks instead of pointing at sq repair
status: Verified
author: manager
priority: high
description: load() handles a corrupt index cleanly but lets FileNotFoundError escape
created_at: '2026-07-30T10:43:42Z'
updated_at: '2026-07-30T12:36:52Z'
---
<!-- sq:body -->
`IndexStore.load` catches ValidationError and UndecodableFileError and raises a clean SquadsError naming `sq repair` as the remedy. A *missing* .squads.json is not caught, so `read_text` raises FileNotFoundError and the CLI prints a raw traceback. Every read path is affected — reproduced on `sq list`, `sq role list` and `sq check` — while the remedy itself works: `sq repair` rebuilds the index from the markdown files (verified, 18 items).

The two cases have the same cause (an unusable index), the same remedy, and the frontmatter-is-the-source-of-truth invariant is what makes recovery possible in both. Only the message is missing.

It matters most to adopters: the index is rebuildable by design, so a project that gitignores it — a reasonable reading of 'never store what can be reconstructed' — gets a traceback on the first command after every fresh clone, with nothing naming the one-word fix.

Repro: sq init; rm squads/.squads.json; sq list. Expected: the corrupt-index wording, adapted — an unreadable index, run sq repair to rebuild it from the markdown files.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-30T12:26:10Z] Pierre Chat:
  - 0.13, and take it now — ahead of the remaining roster tasks.
- [2026-07-30T12:29:28Z] Operator:
  - Fixed: IndexStore.load now catches FileNotFoundError and raises a clean SquadsError naming sq repair, mirroring the corrupt-index wording ("missing index X.json; run sq repair..." vs "corrupt index X.json (...); run sq repair...").
  - Write path: transaction() calls load() internally, so it inherits the same clean error for free — no separate fix needed there.
  - repair() already guards with store.exists() before its own load() call, so it was unaffected; verified explicitly with a new CLI test that repair rebuilds from zero .squads.json.
  - Tests: service-level (tests/unit/test_index_allocation.py) + CLI smoke + repair-still-works (tests/cli/test_undecodable_squad_files_fail_cleanly.py). Falsified: reverting the fix reproduces the raw FileNotFoundError traceback in both new tests.
- [2026-07-30T12:29:50Z] Elias Python:
  - Correction: the previous comment (mis-attributed to Operator by a missed --as flag) is mine — Elias Python, python-dev.
- [2026-07-30T12:36:51Z] Catherine Manager:
  - Verified on the committed build (17d5dfe) by running the repro directly, not off the dev's report: sq list, sq check and a create mutation all give the clean 'missing index ...; run sq repair' message with a bare exit code of 1; sq repair rebuilds (18 items) and sq list is normal afterwards. The write path is confirmed in practice, which the report had only reasoned about.
  - Verified by the manager rather than QA — a one-line error-path fix with a reproducible check, so I did not spawn a QA pass for it.
<!-- sq:discussion:end -->
