---
id: REV-659
sequence_id: 659
type: review
title: TUI per-type display labels render via label_for
status: Approved
author: reviewer
refs:
- TASK-658:scopes
created_at: '2026-07-27T08:02:48Z'
updated_at: '2026-07-27T08:05:03Z'
---
<!-- sq:body -->
Independent review of routing every user-visible item-type name in the terminal TUI through the display-label resolver.

## Verdict
No findings. Clean.

## What was verified
- Type-filter dropdowns and the search hit-row type badge render the resolved singular label for DISPLAY while keeping the raw type string as the option VALUE, so filtering still keys on the real type end-to-end.
- The hit badge binds the label as a template variable into Textual `Content.from_markup`, not concatenated into the markup string, so a label containing brackets or a dollar sign cannot break or inject markup.
- Swept the whole TUI tree for other raw type-name display sites: the tree shows id/title/status and fixed category group labels only; the reader glance line shows status/priority/assignee only; no screen sets a type-bearing subtitle. No missed sites.
- Tests cover a bundled derived label and a pinned override, asserting the option value stays the raw type and the hit row shows the resolved label.

Targeted gates green: pyright and ruff clean on the touched files; the two TUI test files pass.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 659 add-finding "…" --severity medium`; track with `sq review 659 finding <n> update --status <Status>`._

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-27T08:03:46Z] Paul Reviewer:
  - Independent review of TASK-658 (TUI per-type display labels). No findings — clean. Value path unchanged (options carry raw type as VALUE, label only for display; filter + search both key on the raw type via _selected). Hit badge escaping safe (label bound as $type template var into Content.from_markup, never concatenated). Swept _tui/: no other raw-type display site — _tree.py/_reader.py/_browse.py/_app.py confirmed clean. Left Draft; verdict recommendation Approve — @manager decides after the full suite.
- [2026-07-27T08:05:01Z] Paul Reviewer:
  - Verified: display=label / value=raw-type (filtering unaffected); hit-badge label bound as a Content template var (markup-injection safe); no missed TUI type-display sites; tests cover derived + pinned-override. Full suite green.
<!-- sq:discussion:end -->
