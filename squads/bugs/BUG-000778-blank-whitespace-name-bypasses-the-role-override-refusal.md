---
id: BUG-778
sequence_id: 778
type: bug
title: Blank/whitespace --name bypasses the role-override refusal
status: Verified
author: qa
severity: medium
refs:
- REV-770
created_at: '2026-08-22T09:33:45Z'
updated_at: '2026-08-22T10:33:00Z'
---
<!-- sq:body -->
Re-driven, symptom for symptom, in a fresh throwaway squad.

BUG-760's blank/whitespace-string refusal lives entirely in `_apply_override` — the merge point
for a `.overrides/roles/<slug>.toml` file. The two CLI entry points that also let an operator
set a role's name directly never reach it: `dev_role`/its `dc_replace`-based override build a
`RoleDef` straight from the CLI argument, with no pass through `_refuse_blank_strings`.
`Item.title` itself only enforces `min_length=1`, which a whitespace-only string satisfies.

Driven, fresh squad:

    sq dev add --tech go --name "   "
      added     (`go-dev`) ROLE-12                                       exit 0
      frontmatter                title: '   ', extra.full_name: '   '
      CLAUDE.md                  - **   ** — Go developer (`go-dev`)
      .claude/agents/go-dev.md   "You are **   **, the Go developer on this project."
      sq check                                                           exit 0

    sq role activate architect --name "   "
      activated     (ROLE-13)                                            exit 0
      frontmatter                title: '   ', extra.full_name: '   '
      CLAUDE.md                  - **   ** — architect (`architect`)
      sq check                                                           exit 0

For contrast, the identical value through the already-fixed override path on the same squad:

    .overrides/roles/architect.toml:  full_name = "   "
    sq sync
      error: invalid role override …/architect.toml: field(s) blank or whitespace-only
      (omit the key instead to inherit): full_name                       exit 1

Same symptom BUG-760 fixed — including the `.claude/` pointer's identity sentence, the surface
that bug called the worst instance because it is prose an agent reads as its own identity — now
reachable through two documented flags instead of an override file, with `sq check` silent on
both.

Also re-driven: `--name ""` (empty, not whitespace) is harmless only by accident. It is falsy in
both `dev_role`/`add_dev` and `activate_role`, so it falls through to the pool/bundled name
rather than being stored — confirmed `sq dev add --tech rust --name ""` produces a normal pool
name ("Ada Rust" in the run driven here), not a blank one. Only the whitespace form actually
lands as a stored value. That inconsistency (one falsy-looking input is silently ignored, the
other is silently accepted) is worth closing in the same pass as the two flags: `""` should
refuse for the same reason the override path refuses it, not be quietly treated as "no name
given."

Direction of fix, not prescriptive: validate the operator-supplied name at the two roster entry
points (`activate_role`, `add_dev`) with the same message `_refuse_blank_strings` produces, or
route the name through a seam both paths and the override path share.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T10:25:49Z] Mara Tester:
  - Verified on c6a03b2 against the bug's own repro, all four cases driven separately in a throwaway squad: sq dev add --tech go --name "", sq dev add --tech go --name "   ", sq role activate architect --name "", sq role activate architect --name "   " -- all four refuse with 'role full_name is blank or whitespace-only — every role needs a real name', exit 1, and confirmed no item/file is created for any of them (roster/agents-dir/sq check all unchanged).
  - Override path message confirmed byte-identical across sq sync, sq role <slug> show, and sq check: 'invalid role override <path>: field(s) blank or whitespace-only (omit the key instead to inherit): full_name'.
  - Padding question settled by driving all three construction paths side by side on one squad with the identical padded string: sq dev add --name "  Padded Person  ", sq role activate --name "  Padded Qa  ", and an override full_name = "  Padded Override  " all store the value verbatim, padding intact, in both frontmatter and extra.full_name. No divergence between the override path and the two CLI paths -- all three agree on accept-and-store-verbatim.
  - Omitted --name still auto-picks correctly on both paths: sq dev add --tech rust (no --name) -> pool name (Ada Rust); sq role activate devops (no --name) -> bundled default (Hugo Ops). sq check clean throughout.
  - Holds fully. Status note: this item is InProgress on disk, not Fixed -- sq bug 778 status Verified refuses ('bug cannot move InProgress -> Verified'). Not transitioning; flagging for whoever should move it to Fixed first.
- [2026-08-22T10:32:57Z] Catherine Manager:
  - Fix landed in c6a03b2 on release/0.14 (TASK-782), shipping in 0.13.1. Recording the landing commit and moving this to Fixed - my bookkeeping lagged the work again, which is why QA could not transition it and correctly refused to force the illegal jump.
<!-- sq:discussion:end -->
