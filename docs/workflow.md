# squads workflow

Two layers: **who creates and links what** (the team workflow) and **how each item moves through
its states** (the status lifecycle). `sq workflow` prints a short version of the first; this is the
full reference. The rules are enforced — at `create`/`link`/`status` time and by `sq check`.

---

## Team workflow

```
        product owner                         tech lead
            │                                    │
            ▼                                    ▼
   ┌──────────────────┐  parent   ┌───────────────────────────┐
   │ FEATURE          │◀──────────│ TASK                       │
   │  + user stories  │           │  parent = the feature      │
   │    US1, US2, …   │◀╌╌╌╌╌╌╌╌╌╌│  subtask ST1 (→ US1) …     │
   └──────────────────┘  maps to  └───────────┬───────────────┘
            ▲ parent                          │ refs
   ┌────────┴────────┐              ┌─────────┴───────────┐
   │ EPIC            │              │ BUG  (--kind fixes) │
   │ (groups feats)  │              │ REVIEW (--kind addresses)
   └─────────────────┘              └─────────────────────┘
```

- The **product owner** authors **features** (`sq create feature`) and their **user stories**
  (`sq story add`); defines acceptance criteria.
- The **tech lead** authors **tasks** (`sq create task`) and breaks them down:
  - a task's **parent is the feature** it implements (`--parent FEAT-…`);
  - each **subtask maps to one user story** of that feature (`sq subtask add … --story USn`);
  - a task that fixes a bug or follows up a review links it as a **ref**
    (`sq ref add <task> <id> --kind fixes|addresses`);
  - a purely-technical task has no feature parent and no such ref.
- The hierarchy spine is **epic → feature → task**, with **subtasks → user stories**.
- Other roles read these to do their work: **QA** derives tests from user stories; the **reviewer**
  drives review items; the **architect** records **ADRs** and authors **guides**.

### Enforced rules

- `task.parent` must be a **feature**; `feature.parent` must be an **epic** (`ALLOWED_PARENTS`).
  Bugs/reviews attach as refs, **not** as a task's parent.
- A subtask's `(→ USn)` must exist in the task's parent feature.
- `sq check` flags violations (bad parent type, dangling subtask→US, dangling refs).

### Commands at a glance

```bash
# product owner
sq create feature "User authentication" --parent EPIC-000001
sq story add FEAT-000002 "As a user, I want to log in"

# tech lead
sq create task "Validate token" --parent FEAT-000002
sq subtask add TASK-000003 "Check expiry" --story US1
sq ref add TASK-000003 BUG-000009 --kind fixes        # or REV-… --kind addresses

# everyone
sq status TASK-000003 InProgress
sq comment TASK-000003 --as reviewer -m "@qa please verify the redirect"
sq inbox qa
```

---

## Status lifecycles

Every item type has its own state machine. `sq status <ID> <Status>` only allows a transition the
machine permits; `--force` overrides. New items start at the machine's initial state.

```
work items (epic · feature · task · bug)
    Draft ──▶ Ready ──▶ InProgress ──▶ InReview ──▶ Done ┄┄▶ (reopen) InProgress
                          ▲                └──────────┘ rework
    Blocked  ⇄  Ready / InProgress / InReview          Cancelled ◀── any non-terminal

ADR (decision)   Proposed ──▶ Accepted ──▶ Superseded     (Proposed ─▶ Rejected ; Accepted ─▶ Deprecated)
review           Requested ─▶ InReview ─▶ Approved        (InReview ⇄ ChangesRequested ; any ─▶ Rejected)
guide            Draft ──▶ Published ──▶ Deprecated        (⇄ both directions)
role · skill     Draft ──▶ Active ⇄ Archived

  ─▶ allowed transition   ⇄ both ways   ┄▶ escape hatch   terminal states have no outgoing edge
```

| Type | Initial | Transitions |
|------|---------|-------------|
| epic / feature / task / bug | `Draft` | Draft→{Ready, InProgress, Cancelled}; Ready→{InProgress, Blocked, Cancelled}; InProgress→{InReview, Blocked, Done, Cancelled}; InReview→{InProgress, Done, Blocked, Cancelled}; Blocked→{Ready, InProgress, Cancelled}; Done→{InProgress}; Cancelled→{Draft} |
| decision (ADR) | `Proposed` | Proposed→{Accepted, Rejected}; Accepted→{Superseded, Deprecated}; Rejected→{Proposed} |
| review | `Requested` | Requested→{InReview, Rejected}; InReview→{ChangesRequested, Approved, Rejected}; ChangesRequested→{InReview, Rejected} |
| guide | `Draft` | Draft→{Published}; Published→{Deprecated, Draft}; Deprecated→{Published} |
| role / skill | `Draft` | Draft→{Active}; Active→{Archived}; Archived→{Active} |

**Terminal states** (no outgoing transitions) are `Done`, `Cancelled`, `Rejected`, `Superseded`,
`Deprecated`, `Archived`, `Approved`, `Verified`, `WontFix`. `sq inbox` only surfaces **open**
(non-terminal) items.

> Status is stored in the `.md` frontmatter *and* mirrored in the index. The dated discussion
> entries (`sq comment`) are what record the *history* of a transition — see
> [adoption.md](adoption.md) for replaying that history with `--at`.

The machines themselves live in `squads._workflow` (`WORKFLOWS`, `can_transition`, `TERMINAL`,
`ALLOWED_PARENTS`); see [internals.md](internals.md) for how they're wired in.

## Sub-entities: subtasks, user stories, findings

The body-local sub-entities (`sq subtask`/`story`/`finding`) are tracked by `sq` too — each has its
own status, and the parent shows an **sq-managed summary table** that rolls them up (regenerated on
every change). Their state lives in an sq-owned `:meta` marker region inside each block, never in the
heading prose; the block's body stays free-form for the agent.

| Sub-entity | Lives on | Add / transition | Lifecycle |
|------------|----------|------------------|-----------|
| **subtask** | task | `sq subtask add TASK "…" [--story US1]` · `sq subtask status TASK ST1 <S>` | `Todo → InProgress → Done` (+ Blocked, Cancelled) |
| **user story** | feature | `sq story add FEAT "…"` · `sq story status FEAT US1 <S>` | `Todo → InProgress → Done` (+ Blocked, Cancelled) |
| **finding** | review | `sq finding add REV "…" --severity high` · `sq finding status REV F1 <S>` | `Open → Fixed → Verified` (+ WontFix) |

Findings also carry a **severity** set at `add` time: 🔴 critical · 🟠 high · 🟡 medium · 🟢 low ·
🔵 info. `sq subtask done` remains a shortcut (Done / `--undo` → Todo). Transitions are validated by
the sub-entity machines (`squads._workflow.SUBENTITY_WORKFLOWS`); `--force` overrides.
