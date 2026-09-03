---
id: BUG-869
sequence_id: 869
type: bug
title: sq role catalog's Default column ignores sq role set-default
status: Fixed
author: qa
priority: low
refs:
- BUG-850
created_at: '2026-09-02T08:27:34Z'
updated_at: '2026-09-02T08:45:09Z'
---
<!-- sq:body -->
## What happens

`sq role catalog` prints a `Default` column. Its own help calls it "the role catalog (slug, name, title, default indicator) **for the active squad**", but the column reports the bundled catalog's designation rather than the one in force. After an operator designates a different default through the shipped verb, the column keeps pointing at `manager`.

## Driven

Fresh scratch squad at 0.14.0 (e9dde77), `sq init --default-names`, two independent cases:

```
sq role qa set-default          -> ROLE-5 is now the default / cleared ROLE-1
sq role catalog                 -> manager  ...  Default ✓        (wrong)
sq role qa show --json          -> "is_default": true             (right)
CLAUDE.md default-role line     -> default to **Mara Tester** (`qa`)   (right)
```

```
sq dev add --tech python --name "Elias Python"   -> ROLE-21
sq role python-dev set-default                   -> cleared ROLE-5
sq role catalog                 -> manager  ...  Default ✓        (wrong)
sq role python-dev show --json  -> "is_default": true             (right)
CLAUDE.md default-role line     -> default to **Elias Python** (`python-dev`)  (right)
```

Reproduced with a bundled role and with a dev role, and it survives `sq sync` and `sq repair` in that wrong state. `sq check` is exit 0 throughout.

## Expected vs actual

- Expected: a column labelled `Default` on a listing scoped to the active squad names the role that actually holds the designation — the same answer `sq role <slug> show --json` and the compiled default-role line give.
- Actual: it names the bundled catalog's default regardless. The two shipped surfaces that resolve the designation and the one that does not now disagree with each other on the same squad.

`sq role list` — the active roster listing — carries no default indicator at all, so `sq role catalog` is the only tabular surface an operator would consult to answer "who is the default here", and it is the one giving the catalog's answer.

## Scope

This is the same display-vs-designation class named as the second-order symptom on the `sq role set-default` reversion report, on a surface that report did not cover; the reversion itself is fixed and verified. Consequence here is a misleading read, not data loss — the designation on disk and the generated agent files are correct.

Not prescribing the fix: whether the column should resolve per role, or whether a catalog listing should carry a designation column at all given `sq role list` does not, is a design call.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T08:27:45Z] Catherine Manager:
  - Re-homed from an isolated verification worktree, where it was allocated BUG-867. That worktree's index predated the two milestones created concurrently in the main tree, so both allocated 867 from the global counter. The milestones kept the number; this bug was recreated here with its body intact. No content was lost.
- [2026-09-02T08:45:09Z] Elias Python:
  - Fixed. Both listings now answer from the live roster; the bundled catalog is only the fallback where there is no roster to ask.
    
    - `sq role catalog` — the `Default`/`is_default` column resolves the squad's designation through a new `Service.default_role_slug()` (first live role whose resolved `RoleView.is_default` is set — the same projection the backend compiles the default-role line from, so the two cannot disagree). Outside a squad it falls back to the catalog document's own declared designation, which is the only honest answer there. The command moved from a bare sync `@handle_errors` to `@common.command`, so it now opens a Service when it is inside a squad; the not-a-squad path is unchanged.
    - `sq role list` — gained a `Default` column and an additive `is_default` JSON key. Chosen deliberately, not for symmetry: the catalog structurally cannot name a developer-role holder (`python-dev` has a roster entry and no catalog row), so the roster listing is the only surface that can answer "who is the default here" in every case. In that case the catalog's column is correctly blank throughout and its plain footer names the holder and points at `sq role list`.
    
    Same inversion as `authoring_owner` (live resolved map first, bundled catalog as fallback), applied at the display seam rather than to `role_by_slug` itself — `role_by_slug`/`load_role_catalog` answer "what does the catalog declare", which is a real and separate question the `Origin` column already depends on. Making them squad-aware would have folded a roster fact into the catalog loader; the defect was that a squad-scoped column read a catalog-scoped source, so the call site is where it belongs.
    
    Regression test drives it through the CLI for a bundled role and a developer role, and re-asserts after `sync` and `repair`. Before the change it failed with the catalog reporting `{manager}` where `{qa}` (bundled move) and `{}` (dev holder) were expected. Golden `role_list.json` picked up the additive key; `role_catalog.json` is unchanged.
    
    Gates: 4423 passed, 7 skipped, 0 failed (baseline 4418 + 5 new); pyright 0 errors; ruff check/format clean; sq check clean.
    
    @qa ready to verify — the repro in the body should now give the roster's answer on both surfaces.
    @manager two adopter-doc lines describe `sq role list` as carrying only a live/not-live marker (`docs/roles.md`, `docs/stability.md`) — now incomplete rather than wrong. Flagging for the writer rather than editing them.
<!-- sq:discussion:end -->
