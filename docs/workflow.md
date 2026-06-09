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
  (`sq feature <n> add-story`); defines acceptance criteria.
- The **tech lead** authors **tasks** (`sq create task`) and breaks them down:
  - a task's **parent is the feature** it implements (`--parent FEAT-…`);
  - each **subtask maps to one user story** of that feature (`sq task <n> add-subtask … --story USn`);
  - a task that fixes a bug or follows up a review links it as a **ref**
    (`sq task <n> ref add <id> --kind fixes|addresses`);
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
sq feature 2 add-story "As a user, I want to log in"

# tech lead
sq create task "Validate token" --parent FEAT-000002
sq task 3 add-subtask "Check expiry" --story US1
sq task 3 ref add BUG-000009 --kind fixes        # or REV-… --kind addresses

# everyone
sq task 3 status InProgress
sq task 3 comment --as reviewer -m "@qa please verify the redirect"
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

The sub-entities (subtasks/stories/findings) are tracked by `sq` too — each has its own status, and
the parent shows an **sq-managed summary table** that rolls them up (regenerated on every change).
Their state (status/assignee/severity/story) lives in the parent item's **frontmatter** (so the index
sees them); the block in the body holds only the prose and a derived badge header. The block's **body
is sq-managed too** — set it with `sq <type> <n> <kind> <k> body -m
"…"` (or `--file body.md` / `--file -`) and read the whole block with `sq <type> <n> <kind> <k> show`;
no manual markdown editing.

| Sub-entity | Lives on | Add / transition | Lifecycle |
|------------|----------|------------------|-----------|
| **subtask** | task | `sq task <n> add-subtask "…" [--story US1]` · `sq task <n> subtask <k> update --status <S>` | `Todo → InProgress → Done` (+ Blocked, Cancelled) |
| **user story** | feature | `sq feature <n> add-story "…"` · `sq feature <n> story <k> update --status <S>` | `Todo → InProgress → Done` (+ Blocked, Cancelled) |
| **finding** | review | `sq review <n> add-finding "…" --severity high` · `sq review <n> finding <k> update --status <S>` | `Open → Fixed → Verified` (+ WontFix) |

`sq <type> <n> <kind> <k> update` is the one metadata entry point for a sub-entity — `--title`,
`--status` (+`--force`), `--assignee`/`--clear-assignee`, plus a subtask's `--story`/`--no-story` and
a finding's `--severity`. Findings carry a **severity** (🔴 critical · 🟠 high · 🟡 medium · 🟢 low ·
🔵 info), set at `add` time and changeable with `update --severity`. Transitions are validated by the
sub-entity machines (`squads._workflow.SUBENTITY_WORKFLOWS`); `--force` overrides.
