---
id: BUG-985
sequence_id: 985
type: bug
title: A [dev] catalog override is reverted for existing devs by sq sync
status: Open
author: qa
priority: medium
refs:
- ADR-984
- MILE-934:targets
created_at: '2026-10-09T18:42:59Z'
updated_at: '2026-10-09T18:43:13Z'
---
<!-- sq:body -->
A project override of the `[dev]` table in the role catalog (`.overrides/roles.toml`) is applied to a developer when it is added, then silently reverted for that same developer by the next `sq sync`. An existing developer's template is not read from the catalog the squad resolves.

## Reproduction

Dev build `.venv/bin/sq` (release/0.16, f0c6295b), scratch squad outside the repo.

```
git init -q . && sq init                      # exit 0
sq override scaffold roles                    # exit 0
printf '\n[dev]\nmodel = "haiku"\ncolor = "pink"\n' >> squads/.overrides/roles.toml
sq override list                              # roles / current, exit 0
sq dev add --tech rust                        # exit 0
grep -E '^(model|color):' .claude/agents/rust-dev.md
    model: haiku
    color: pink          <- override applied
sq sync                                       # exit 0
grep -E '^(model|color):' .claude/agents/rust-dev.md
    model: haiku
    color: green         <- bundled value, override lost
sq sync                                       # second sync, same result
sq check                                      # exit 0, no warning about the revert
```

Bundled `[dev]` is model sonnet, color green.

## Expected versus actual

Expected: the pointer for every developer keeps reflecting the resolved catalog (`color: pink`) across syncs, as it did when the developer was added.
Actual: the first `sq sync` rewrites `color` to the bundled value for the developer that was just added with the override. Nothing reports it.

## Bounds (each row driven)

| Shape | Result |
|---|---|
| Override color+model, `dev add`, then `sync` | add: haiku/pink. After sync: haiku/green. Color reverted. Model kept (the model survives, the color does not). |
| Same squad, override model changed haiku to opus, `sync` | existing rust-dev and go-dev stay haiku/green: the model change does not reach existing developers. A developer added afterwards gets opus/pink. |
| Developer added BEFORE the override existed, then override added, `sync` | existing developer stays sonnet/green: the override never reaches it. A developer added afterwards gets haiku/pink. |
| Second `sync` | no further change (stable after the first). |
| `sq role rust-dev show` | prints `model` only, no color, so it cannot expose the color revert. After sync it agreed with the pointer on model (haiku) in the first shape; in the third it printed sonnet, as the pointer did. |

So a squad's `[dev]` override applies only at `dev add` time. For existing developers a color override never applies after sync, and a model override applies only if it was present before the developer was added (the model is carried from creation, not re-read).

## Not covered

`name_pool`, the per-slug `.overrides/roles/<slug>.toml` file, and the AGENTS.md backend were not driven. Model carry-over was inferred from behaviour, not from reading the code.

ADR-984 decision 2 (the template is read from the catalog the squad resolves) is expected to remove the cause.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
