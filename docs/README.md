# squads documentation

`squads` (`sq`) is the **coordination layer** for a team of AI agents working on one codebase. It
gives the team a shared structure to work in: a stable JIRA-like ID for every piece of work,
defined roles and skills, a status lifecycle, and a handoff protocol (comments, `@mentions`, an
inbox) — one source of truth every agent reads and writes through `sq`. Claude Code is the first
backend.

## Where to go

**Using squads**

| Doc | Read it for |
|-----|-------------|
| **[tutorial.md](tutorial.md)** | A 15-minute, end-to-end first squad. |
| **[workflow.md](workflow.md)** | The team workflow (who creates & links what) and the per-type status lifecycles. |
| **[agents.md](agents.md)** | Operating *as* an agent inside a squad — the create→write→hand-off loop. |
| **[roles.md](roles.md)** | The bundled roster, bundles, and stack developers. |
| **[recipes.md](recipes.md)** | Copy-paste sequences for common moves. |
| **[faq.md](faq.md)** | Common errors and how to fix them. |
| **[adoption.md](adoption.md)** | Migrating an existing project: `sq adopt` + history-preserving `--at` timestamps. |
| **[overrides.md](overrides.md)** | Customizing templates, roles, and agent names: `.overrides/` layout, the `sq override` workflow, and handling drift across upgrades. |
| **[migration.md](migration.md)** | Upgrading a squad to a new squads version: `sq sync`/`repair`, frontmatter & marker transformers, and LLM runbooks for non-deterministic changes. |

**Under the hood / contributing**

| Doc | Read it for |
|-----|-------------|
| **[stability.md](stability.md)** | The 1.0 contract: which surfaces are stable after 1.0, what each promises, and the post-1.0 versioning scheme. Five tiers from durable `.md` format down to tool-owned files. |
| **[internals.md](internals.md)** | How squads works — the index & counter, frontmatter-as-truth, markers, refs, the backend & pointers, the playbook, a worked lifecycle. |
| **[backends.md](backends.md)** | Writing a new agent backend (the `AgentBackend` ABC). |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Dev setup, the gate, conventions, how to add things. |
| [`../README.md`](../README.md) · [`../CLAUDE.md`](../CLAUDE.md) · [`../CHANGELOG.md`](../CHANGELOG.md) | Intro/install · contributor quick-ref · release history. |

## The shape of it

```
                  ┌───────────────────────────────────────────────┐
   you / agent ─▶ │  sq   —  CLI command interface                 │
                  └───────────────────────┬───────────────────────┘
                                          │  calls
                  ┌───────────────────────▼───────────────────────┐
                  │  Service orchestration layer                   │
                  └────────┬──────────────┬───────────────┬───────┘
                           │              │               │
              ┌────────────▼───┐  ┌───────▼──────┐  ┌─────▼──────────┐
              │ Index          │  │ Backend      │  │ Rendering      │
              │ Store          │  │              │  │ (Jinja2)       │
              │ .squads.json   │  │ → .claude/   │  │                │
              └────────┬───────┘  └───────┬──────┘  └────────────────┘
                       │                  │
              ┌────────▼──────────────────▼────────────────────────┐
              │  squad folder:  *.md   (frontmatter = source of     │
              │                         truth; index is rebuildable)│
              └─────────────────────────────────────────────────────┘
```

## What lives where

```
project/
├─ .squads.toml ───────────────┐  config → which squad folder is active
├─ CLAUDE.md                   │  (managed section: roster, impersonation, workflow)
├─ .claude/                    │  tool-owned pointers + config
│  ├─ settings.json            │  merged, never clobbered
│  ├─ agents/architect.md ─────┼──@──▶ squads/agents/roles/ROLE-000002-architect.md   (real def)
│  └─ skills/sq-task/SKILL.md ─┼──@──▶ squads/agents/skills/sq-task.md                 (real body)
└─ squads/                  ◀──┘  self-contained, relocatable (override with --dir)
   ├─ .squads.json               the index: counter + items + refs  (rebuildable)
   ├─ epics/  features/  tasks/  bugs/  adrs/  reviews/  guides/
   │     └─ TASK-<n>-fix-login.md          ← frontmatter is the truth
   └─ agents/{roles,skills}/
```
