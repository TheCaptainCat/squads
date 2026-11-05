---
id: BUG-1305
sequence_id: 1305
type: bug
title: sq-how-to repeats the managed CLAUDE.md section
status: Verified
author: qa
refs:
- FEAT-1290
created_at: '2026-11-05T01:43:47Z'
updated_at: '2026-11-05T02:47:24Z'
priority: low
severity: low
---
<!-- sq:body -->
US3 says `sq-how-to`, `sq-greeting` and `sq-memory` carry no text that the role skill, the managed `CLAUDE.md` section or `sq docs` already gives. `sq-how-to` repeats, almost sentence for sentence, the "Working with squads" and "Team workflow" bullets of the managed `CLAUDE.md` section, which every agent and the main session already receive.

## Steps to Reproduce

On the fresh squad (`/home/pchat/.cache/sq-qa-1290/fresh`) compare `sq skill sq-how-to show --raw --no-header` with the managed section of `CLAUDE.md`:

- CLAUDE.md "Team workflow": "Items are addressed as `sq <type> <number> <verb>` ... Sub-entities nest: `sq <type> <n> <kind> <k> update --status <status>`." and sq-how-to Golden rules, first bullet: the same statement, same example.
- CLAUDE.md "Working with squads": "the `.md` files are sq-managed ... read them through `sq <type> <n> show`, never by opening the file: the command resolves state the file does not carry, so a direct read returns strictly less than the command." The same sentence is in sq-how-to.
- Set bodies through commands (`body -m`, `--file`), read with `show --full --comments`, comment with `--as <slug> -m` and `--file` for backticks, the comment hash `show|edit|remove` rules, link by ID: each appears in both.

An exact-sentence scan finds 2 identical sentences; the rest is paraphrase with the same commands and rules.

## Expected vs Actual

- **Expected:** the duplicated bullets live in one place; sq-how-to keeps only what no other startup text carries.
- **Actual:** about the first half of sq-how-to (Golden rules) restates the managed section.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-05T02:18:42Z] `python-dev` Elias Python:
  - Fixed: sq-how-to drops the golden rules the managed CLAUDE.md section carries and keeps only what it lacks (marker/frontmatter rule, --file -, --desc, sub-entity metadata, comment edit/remove flags). A test fails if a long CLAUDE.md sentence reappears in it. Manifest and content store regenerated. Uncommitted.
- [2026-11-05T02:47:12Z] `reviewer` Paul Reviewer:
  - Verified at 307c1030 by the reviewer. `sq-how-to` opens with "Beyond the managed section" and keeps only the rules the managed CLAUDE.md section lacks. The new test fails if any CLAUDE.md sentence over 60 characters reappears in it. That test passes on the bundled and override squads.
<!-- sq:discussion:end -->
