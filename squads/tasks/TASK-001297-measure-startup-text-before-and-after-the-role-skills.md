---
id: TASK-1297
sequence_id: 1297
type: task
title: Measure startup text before and after the role skills
status: InProgress
parent: FEAT-1290
author: tech-lead
assignee: qa
refs:
- ADR-1294:implements
description: ADR-1294 section 8 table on this repository, before and after
subentities:
- local_id: ST1
  title: 'Before: startup figures at the base commit'
  status: Done
  assignee: qa
  maps_to: US9
- local_id: ST2
  title: 'After: startup figures once this squad is migrated'
  status: Todo
  assignee: qa
  maps_to: US9
created_at: '2026-11-04T21:46:38Z'
updated_at: '2026-11-04T21:56:15Z'
---
<!-- sq:body -->
## Goal

Measure what each agent and the main session receive at startup on this repository's squad, before and after FEAT-1290, as ADR-1294 §8 defines it, and record the figures on FEAT-1290 as one comment (US9). This is a measurement on this repository, not product code.

## Base and after commits

- **Before**: the commit just before the first code change of FEAT-1290. The manager records its SHA on this task when round 1 of the Python task is dispatched (today's head is that commit if nothing else lands first). Measure it from a git worktree checked out at that SHA, with that commit's own `sq` build on `PATH` (`uv run` in the worktree, or a wheel built from it), so the pointers and the command outputs are that commit's.
- **After**: the commit after the main loop has migrated this repository's squad with the finished build (`sq migrate up`, then `.claude/` committed). Same method.

## Method (ADR-1294 §8)

- For each of the ten roles and for the main session, spawn the agent (or open the session) in a non-interactive `claude -p` run on the worktree, with a short neutral prompt, and read the first messages from the host transcript (the subagent's or session's JSONL under the host's project directory), never from the model's report.
- Columns: the agent pointer body in characters (the system prompt squads contributes); each preloaded or invoked skill as delivered (before: the pointer text; after: the rendered text, the role skill's three lines summed, echo lines included where a command failed); the total delivered at startup; the effective total, adding the output of every command the agent pointer or the `sq-greeting` body names (the `show`, `mine`, `inbox`, `board` and `memory` commands, run as that role).
- The main session row: before, the managed `CLAUDE.md` section plus what the `greeting` skill pointer delivers and what its commands print; after, the section plus the rendered `sq-greeting` and the output of its steps 3 to 7 for the default role.
- Never pass a permission-bypass flag (`--dangerously-skip-permissions`, `--permission-mode bypassPermissions`) to the nested `claude`; use the project's allow rules. A spawn that aborts on a render is a finding: record it, and open a bug.
- Write the scripts and raw transcripts under `/home/pchat/.cache/sq-adr1290/measure/`, not `/tmp`.

## Output

One comment on FEAT-1290: the table (rows per role and main session, before and after side by side), the two SHAs, the Claude Code version, and one line per figure that could not be read. No size budget applies; no recommendation is asked for.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1297 add-subtask "<title>"`; track with `sq task 1297 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Before: startup figures at the base commit

<!-- sq:subtask:ST1:body -->
Story US9. ADR-1294 §8.

From a worktree at the base SHA the manager records on this task, with that commit's `sq` on `PATH`: read every column for the ten roles and the main session from the host transcripts. This subtask can run as soon as the SHA is recorded, in parallel with the Python rounds, since it never touches the main working tree. Keep the raw numbers and the transcript paths under `/home/pchat/.cache/sq-adr1290/measure/before/`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — After: startup figures once this squad is migrated

<!-- sq:subtask:ST2:body -->
Story US9. ADR-1294 §8.

After the main loop has migrated this repository's squad with the finished build and committed `.claude/`: the same columns, same method, from a worktree at that commit. Check in the transcripts that every role's spawn went ahead with its three role skill lines rendered (no echo fallback), which also verifies the three-entry `allowed-tools` grant on the host. Then post the one FEAT-1290 comment with the before and after table.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-04T21:48:09Z] `manager` Catherine Manager:
  - Base commit for the before measurement: 973058e5 (code identical to 311b3a21; only board files changed).
- [2026-11-04T21:56:14Z] `qa` Mara Tester:
  - ST1 before figures (base 973058e5, Claude Code 2.1.318). Characters, read from host transcripts unless marked. Raw: /home/pchat/.cache/sq-measure/ (raw/ transcripts, cmds/ command outputs, before_figures.json, measure_before*.py).
    
    Per role. Body = agent pointer system prompt (api-request-shape, system block 2). Skills = sum of the preloaded skill pointers as delivered (each ~563-599 chars: command marker block + pointer text; count in brackets). Delivered = body + skills. Cmds = role show + memory list + board list + mine + inbox, run as that role. Effective = delivered + cmds.
    
    | role | body | skills (n) | delivered | cmds | effective |
    |---|---|---|---|---|---|
    | manager | 1889 | 2911 (5) | 4800 | 22674 | 27474 |
    | architect | 1901 | 4013 (7) | 5914 | 23572 | 29486 |
    | tech-lead | 1891 | 6309 (11) | 8200 | 20356 | 28556 |
    | reviewer | 1893 | 3414 (6) | 5307 | 21222 | 26529 |
    | qa | 1851 | 4017 (7) | 5868 | 20463 | 26331 |
    | devops | 1873 | 2312 (4) | 4185 | 19074 | 23259 |
    | product-owner | 1921 | 4025 (7) | 5946 | 22023 | 27969 |
    | tech-writer | 1910 | 2883 (5) | 4793 | 20625 | 25418 |
    | python-dev | 1906 | 3997 (7) | 5903 | 22661 | 28564 |
    | typescript-dev | 1938 | 4596 (8) | 6534 | 19615 | 26149 |
    
    Not in effective, per role (memory show <slug> for every indexed entry; sq skill <name> show for every preloaded skill pointer): manager 8392 / 50562; architect 17018 / 43939; tech-lead 1600 / 58639; reviewer 17561 / 44699; qa 3214 / 50164; devops 2061 / 45554; product-owner 2409 / 45830; tech-writer 6567 / 47995; python-dev 4747 / 48000; typescript-dev 794 / 53008. Board list is 15255 in every row.
    
    Main session (default role manager):
    - Managed CLAUDE.md section as delivered: 9234. greeting skill pointer via the Skill tool: 456 (plus the 27-char tool result). Delivered at startup: 9690.
    - Commands the greeting body names (sq skill greeting show 3751, sq list -t operator --all 130, sq operator op-pierre show 614, sq tree --json 102703, sq mine manager 28, sq blocked 476): 107702. Effective: 117392. With sq list in place of sq tree --json, the tree term is not measured.
    - Start-of-run commands the section names as manager (role show 3811, memory list 1474, board list 15255, inbox 2106): 22646. Effective with those: 140038.
    
    Method: each role spawned with claude -p --allowedTools=Agent from the worktree, prompt "say hello and stop"; main session with --allowedTools=Skill and a prompt to invoke the greeting skill. No permission-bypass flag. Command outputs run as stdout+stderr, NO_COLOR, FORCE_COLOR unset, 80 columns, sq -C on the worktree.
    
    Limits:
    - The base commit's own sq (0.20.0) refuses this squad (schema v0.19, migration pending), so command outputs come from the released sq 0.19.0 on the unmigrated squad. Cross-check on a migrated throwaway copy with the base build: eight commands (role qa show, memory qa list, board list, mine qa, inbox qa, skill greeting show, tree --json, blocked) gave identical sizes. Other roles' commands were not cross-checked. The squad in the main repo was not migrated.
    - Command outputs are the squad at 973058e5 (board, queues, tree), not today's. Operator op-pierre assumed for the main session; the greeting's git config user.name step not counted.
    - The main-session figure excludes the user-level CLAUDE.md, MEMORY.md and environment text; only the squads-contributed section is counted. The section was cut from the transcript's CLAUDE.md block (the marker lines are not in it); the file's marker region is 9310.
    - Only a hello was prompted, so no skill was followed and no command run by the models; the effective columns are my runs of the named commands. No spawn aborted.
<!-- sq:discussion:end -->
