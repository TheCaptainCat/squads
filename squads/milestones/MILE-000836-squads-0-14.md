---
id: MILE-836
sequence_id: 836
type: milestone
title: squads 0.14
status: InProgress
author: manager
created_at: '2026-08-26T16:00:04Z'
updated_at: '2026-09-03T07:38:33Z'
extra:
  target_date: '2026-09-15'
---
<!-- sq:body -->
The spec-driven customization release: ref kinds and views as declared workflow vocabulary, one override contract across every bundled spec document, pointers that name commands instead of local paths, and two new item types.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-03T07:38:33Z] Theo Writer:
  - - Rewrote PR #19's title and body to release house style (matched against PRs 12/13/14): narrative opener, bold schema/migration status + VS Code lockstep, then Added/Changed/Fixed/Migration with bold-lead bullets. No Claude Code footer — none of the last three carries one. Sourced from the CHANGELOG `## [0.14.0]` section, not from task handoffs.
    - One figure corrected against measurement. The corpus-sweep count circulating as **654** is the pre-fix number: it was measured on a scratchpad copy while the sweep still emptied skill bodies. The shipped sweep is **642** — driven, not inferred, by running `sq repair` from the installed 0.14.0 against an isolated copy of the pre-sweep corpus (tree at `2d5725eb`), which printed `stripped retired regions from 642 item files`. Cross-checks: 632 item files carry a retired region, plus the 10 role files. The PR body says 642. @op-pierre @manager
    - Unrelated to the PR, but noticed while verifying: this repo's own 12 skill items were emptied by the sweep commit `1d20d2e9`, when the sweep still had its skill half, and were never restored. The shipped code is correct — `_sweep_empties_body` returns false for skills — so this is corpus residue in our own squad, not a defect in what ships. Flagging it as a call for someone, not fixing it here.
<!-- sq:discussion:end -->
