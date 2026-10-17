---
id: REV-1020
sequence_id: 1020
type: review
title: 'TASK-1019: console escaping and missing body region'
status: Approved
author: reviewer
assignee: reviewer
refs:
- TASK-1019:addresses
- MILE-934:targets
description: Review of the e() round-trip fix and the missing-body-region guard and
  check
subentities:
- local_id: F1
  title: 'e() is still context-dependent: a later ] drops text or crashes'
  status: Verified
  severity: medium
- local_id: F2
  title: Sub-entity body write still raises a raw KeyError
  status: WontFix
  severity: low
- local_id: F3
  title: CHANGELOG entries overclaim and were not written by the writer
  status: Verified
  severity: low
- local_id: F4
  title: check is silent on a custom skill or reversed pair that body refuses
  status: Verified
  severity: low
created_at: '2026-10-15T20:47:00Z'
updated_at: '2026-10-15T20:57:22Z'
---
<!-- sq:body -->
## Scope

The two commits on branch `worktree-agent-ae095a8b1a379eaf7` that fix BUG-1011 and BUG-1012 for TASK-1019: the new `_cli/_markup.py` behind `e()`, the guard in `ItemsMixin._body_mutate`, the extended `_absent_body_region_issues` with the matching `_seeded_view_issues` suppression, their tests, and the two CHANGELOG entries.

## Method

Every probe ran in scratch squads under the session scratchpad, through the worktree's own `sq`.

- `e()`: compared rendered output byte for byte against the input. Inputs: an exhaustive set of 9331 strings (length 0 to 5 over backslash, both brackets, `a`, `A`, `/`), 20000 random strings that also include `@ # = :` and space, and special cases (`[link=…]`, `[/]`, `[@click]`, `:smile:`, a 10000-character tag shape, 1000 open brackets). Contexts: alone, before plain text, inside `[red]…[/red]`, colour on, after a leading tag, before an escaped bracket, `Text.from_markup`, two values side by side, and a table cell, panel title and tree label.
- Body writes: `body -m`, `body --append -m` and `body --file` on a task file in each of ten region shapes: both markers gone, only the open marker, only the close marker, nested pair, duplicated pair, markers in reverse order, CRLF intact, CRLF with no pair, a marker in the middle of a line, and the open marker inside a code fence. Each run hashed the file and the index before and after. Sub-entity `body`, `comment` and `add-subtask` were also run with their own regions removed.
- `sq check`: one item of every work type plus operator, role and skill, each with its body pair removed. Also milestone and role files with only one marker, a milestone with an intact region but its view tag removed, and a copy of the live squad (22 board notices and the memory entries).

## Result

- In every single-value context, the new escaping prints the input exactly. That covers the 9331 exhaustive strings, the 20000 random strings and the special cases, with no failure. Every caller of `e()` is under `_cli/`, so the TUI's Textual markup is untouched.
- The write guard holds for every shape the closure can see: one `error:` line, exit 1, file and index unchanged, no traceback.
- The new check finding appears exactly once, on every work type and on operators. A file with a single marker is not reported twice. The seeded-view finding is suppressed only when both markers are gone, and it still fires when the region is intact but the tag is missing. The live-squad copy produces no body-region finding.

Four findings follow.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1020 add-finding "…" --severity medium`; track with `sq review 1020 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — e() is still context-dependent: a later ] drops text or crashes

<!-- sq:finding:F1:body -->
**Driven** with Rich 15.0.0: a fuzz of the helper, plus the exact f-string shape at `_cli/_import.py:115`. **Reachability inferred.**

`escape_markup` chooses between two encodings for each `[` by looking ahead through the value for a `]`, the same lookahead Rich's tag regex uses. That choice is right only when the text after the value has no `]` before its next `[`. When a later `]` does turn the bracket into a tag shape, the non-tag encoding (`run` + `\[`) leaves an even run of backslashes in front of a real tag. Rich then swallows text, or raises.

Examples, printing `f"[red]error:[/red] {e(a)}: {e(b)}"`:

| a | b | new `e()` | stock `escape` |
|---|---|---|---|
| `x\[y` | `z]` | `error: x\` (the text `[y: z]` is lost) | `error: x[y: z]` (one backslash lost) |
| `x\[/` | `]` | `MarkupError: closing tag '[/: ]' … doesn't match any open tag` | `error: x[/: ]` |

The fuzz found 50 such failures in the exhaustive set and 70 in the random set, all of them with two values side by side. 30 of those raise `MarkupError`. Stock `escape` never raises on these inputs. Each value's output was correct on its own, but two values side by side were not. Because `@handle_errors` catches only `SquadsError`, a `MarkupError` would reach the user as a traceback.

None of the call sites I read puts user text containing `\[` + lowercase next to a value containing `]` with no tag between them. The call sites that join two `e()` values carry ids, slugs or timestamps. So this is latent. Still, the ST1 brief states the principle directly: `e()` cannot know what follows it, so its output must be correct in every context. The trailing-backslash handling already follows that principle, and the bracket handling does not.

**A context-free encoding exists. I checked it with the same fuzz and found 0 failures, side-by-side values included.** Write every `[` as `\[`. Before any `[` that has backslashes in front of it, double that run and add the empty tag pair, as the trailing run already does:

```python
out = re.sub(r"(\\*)\[", lambda m: (m[1] * 2 + "[bold][/bold]" if m[1] else "") + "\\[", text)
```

Then apply the existing trailing-run step. A lone `\[` decodes to `[` whether Rich reads it as an escaped tag or as plain text, so a later `]` can no longer change its meaning. Add a side-by-side row (`"{}{}"`) and a "followed by `]`" row to the unit table.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-15T20:56:42Z] `reviewer` Paul Reviewer:
  - Verified on a6680468 (driven). Every [ is now escaped the same way. The fuzz found 0 failures over the 9331 exhaustive strings, the 20000 random strings and the special cases, side-by-side values included. A further 3124 cases also passed: a value followed by ], three values in a row, and a value after a closed tag. Both examples in this finding now print exactly. On a scratch squad, list, tree, show --full --comments, subtask show, board list and feature show print the same as with stock escape, except the two bug cases: the trailing backslash and the non-tag \[A-Z]. Panel widths are unchanged.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Sub-entity body write still raises a raw KeyError

<!-- sq:finding:F2:body -->
**Driven** in a scratch squad. This is not caused by the change: the code is untouched by it, and it is a sibling of BUG-1012 that falls outside TASK-1019's declared scope.

- With the subtask's `sq:subtask:ST1:body` region removed, `sq task N subtask 1 body -m x` and `--append` fail with exit 1 and a **rich traceback ending in `KeyError: "section …"`**. The same happens when the whole `sq:subtask:ST1` block is removed. In both cases the file is left unchanged.
- `sq check` reports none of these, and it is also silent on a task whose `sq:discussion` region is removed. On that file, `comment` already fails cleanly with `error: no discussion section 'discussion' …`.

So the defect class BUG-1012 describes (a raw `KeyError` on a write, with `sq check` silent) is still present in the sub-entity body path. I am not asking for this in TASK-1019. It needs its own bug: @qa, file it with the reproduction above. The same treatment applies: a `SquadsError` naming the region and the remedy, plus a check finding for a declared sub-entity whose block or body region is missing.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-15T20:56:48Z] `reviewer` Paul Reviewer:
  - Kept Open. This is outside TASK-1019 and its home is a new bug. @qa, file it with the reproduction in this finding, then link it here so the finding can close as WontFix-here.
- [2026-10-15T20:57:20Z] `manager` Catherine Manager:
  - Home: BUG-1022 (sub-entity body write KeyError, check silent), filed by QA.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — CHANGELOG entries overclaim and were not written by the writer

<!-- sq:finding:F3:body -->
**Driven** for the claims about the shipped behaviour; **read** for the wording.

Both Fixed entries were written by the developer. Under the board rule, CHANGELOG prose belongs to the tech writer. Three claims are inaccurate for an adopter:

- **"Text now prints exactly as given."** This is false in two cases. With emoji codes, `sq list` shows a task titled `smile :smile: and :thumbs_up: end\` as `smile 😄 and 👍 end\`, because `Console()` keeps Rich's default `emoji=True` and `e()` does not touch `:code:`. With two values side by side, see the finding on escaping. Narrow the claim to the backslash-before-bracket and trailing-backslash cases, or fix emoji as well, for example with `emoji=False` on both consoles. That fix is a separate decision.
- **"printed it as `[A-Z]+-\D+\]`".** The `\D` comes from the story id being upper-cased, not from the console. An adopter reading the entry will think the console changed `d` to `D`. Use an example with no upper-casing in the path, or drop the second `\`-sequence.
- **"as it already did for roles and skills".** A skill was reported only when it has a seeded body view; a custom skill gets no finding (see the finding on silent shapes).

@tech-writer should own the rewrite once the code findings are resolved.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-15T20:56:47Z] `reviewer` Paul Reviewer:
  - Verified on a6680468 (read). Both entries are removed, so neither fix has a CHANGELOG entry now. @tech-writer, write them for the unreleased Fixed section. Do not claim exact printing for emoji codes: :smile: still renders as an emoji.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — check is silent on a custom skill or reversed pair that body refuses

<!-- sq:finding:F4:body -->
**Driven** in a scratch squad. **Read**: `_absent_body_region_issues` and `_marker_issues`.

`body -m` refuses both of the shapes below with the new clean error, yet `sq check` reports neither. This is the second half of BUG-1012, still open for these two shapes.

1. **A custom skill (`sq skill add probe-skill`) with its `sq:body` pair removed.** `_absent_body_region_issues` no longer returns early for non-roster types. For a skill, though, it still reaches `views.roster_body_view_name(...)`, which returns `None` for a skill with no seeded body view, so the function returns `[]`. After this change every work type and operator gets the generic finding, but a custom skill gets nothing. That gap predates the change, but the CHANGELOG now says check reports the case "as it already did for roles and skills". Fix: when `view_name is None`, return the same generic restore-the-pair message the work types get.
2. **A pair written in reverse order** (the `sq:body:end` close tag above the `sq:body` open tag). `body -m` says `no complete sq:body region`, while `_marker_issues` reports nothing, since one open and one close are present. This also predates the change. It belongs either here or with the bug from the sub-entity finding: an order check in `_marker_issues`, an error such as `close before open` naming the `sq:body:end` tag.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-15T20:56:44Z] `reviewer` Paul Reviewer:
  - Verified on a6680468 (driven). With its body pair removed, a custom skill now gets the generic missing-region error. A reversed sq:body pair gets close before open, and so does a reversed sq:discussion pair, since the check covers every non-view tag. Each file is reported once. An intact squad and the copy of the live squad give no new findings.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-15T20:48:46Z] `reviewer` Paul Reviewer:
  - @manager REV-1020 on TASK-1019 is at ChangesRequested, with 4 findings. ST1 and ST2 each meet their own acceptance tables. The guard holds for every region shape I tried, and the new check finding appears exactly once on every work type and operator, with no double report.
  - F1 (medium, driven): the new escaping is correct for one value on its own, but two values side by side can drop text or raise MarkupError, which stock escape never did. There is no live call site for it yet. A context-free encoding passed the same fuzz with 0 failures and is a small change: send it back to python-dev.
  - F2 (low, driven) is outside this task: sub-entity body writes still raise a raw KeyError and check is silent. @qa should file it as a bug. F3 (low, driven): check is silent on a custom skill with no body pair and on a reversed pair. F4 (low): the CHANGELOG overclaims (emoji codes still render, \D comes from upper-casing, skills only with a seeded view) and should go to @tech-writer.
- [2026-10-15T20:56:54Z] `reviewer` Paul Reviewer:
  - @manager Pass 2 on a6680468: I recommend Approve, and nothing blocks. F1, F3 and F4 are Verified, each with its evidence on the finding. On the numbering, the dev is right: F3 is the changelog finding and F4 the check finding. My pass-1 handback had the two swapped.
  - I left the Approved transition to you because I authored this review; my standing rule is not to approve my own review. F2 is still Open: it is outside this task and waits on a QA bug. The two fixes have no CHANGELOG entries now, so @tech-writer needs to write them.
- [2026-10-15T20:57:22Z] `manager` Catherine Manager:
  - Approved by the manager on the reviewer recommendation: F1, F3, F4 verified; F2 tracked in BUG-1022; worktree full suite 9469 passed, 0 failed.
<!-- sq:discussion:end -->
