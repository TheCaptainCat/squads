# Working as an agent in a squad

How an AI agent (or a human role-playing one) operates inside a squads-managed project — squads is
the coordination layer that gives the team its shared structure; this is how you work within it. If
you're an agent reading this in a session: this is your operating manual. See
[workflow.md](workflow.md) for who-does-what and the status rules.

## You have a name

Every agent in a squad is one of its roles, and starts each run with that role's guidance already
in hand. How it gets there depends on whether a person opened the conversation or another agent
spawned it.

### The main session: `sq-greeting`

After `sq init`/`sq adopt`, the project's `CLAUDE.md` carries a managed section with one mandatory
instruction: before its first reply to a human, the main session invokes the `sq-greeting` skill
and completes every step it gives. A spawned subagent never does. The skill lists the steps as
commands the session runs itself, in this order:

1. **Identify the operator**: the logged-in user, otherwise `git config user.name`, checked against
   `sq list -t operator --all`. A registered operator's profile is read with
   `sq operator <slug> show --raw --no-header`; an unregistered one is asked first and registered
   only on a yes; when it is unclear who is there, the session asks rather than guesses.
2. **Adopt the role**: the agent the operator greets by name or by function ("Hi Robert", "talk to
   the architect"), matched to a live role. A greeting that matches no live role means asking which
   one. When the operator greets no agent, the session adopts the squad's default role, which the
   skill names (Catherine Manager, `manager`, in a bundled squad; she triages the request and routes
   it to the right specialist).
3. **Read the role**: `sq role <slug> show --raw --no-header`.
4. **Read the queue**: `sq mine <slug>`.
5. **Read the mentions**: `sq inbox <slug>`.
6. **Read the board**: `sq board list --raw`.
7. **Read the memory**: `sq memory <slug> list --raw`, then `sq memory <slug> show <entry>` for each
   entry the request touches.
8. **Greet**, matching the operator's tone ("Hello Robert" → "Good morning, Alice"; "Hi Mara!" →
   "Hey Alice!"), saying who you are and how you help, and giving one short read of the project.

The skill states the steps; it runs none of them, so each one shows in the session's transcript as
the command it is. A person introducing themselves ("it's Alice") is the operator, not a role to
adopt: you stay the agent.

**Changing the default role.** `sq role <slug> set-default` moves the designation to another live
role and clears the previous holder. `sq-greeting` names the default when it renders, so the next
session adopts the new one. A squad with no default role (its holder was retired, say) gets one line
naming `sq role <slug> set-default` in its place, and the session asks the operator which role to
adopt.

On a host that reads `AGENTS.md` instead, the managed section's "Start of a run" part states the
same steps, with the same commands.

### A spawned agent: its role skill

Each role's Claude Code agent file, `.claude/agents/<slug>.md`, preloads three skills:
`sq-role-<slug>`, `sq-how-to` and `sq-memory`. The host renders a preloaded skill into the agent's
first message, so the agent starts with:

- **its role** (`sq role <slug> show --raw --no-header`): the role's definition (mission,
  responsibilities, working agreements), then its part of the playbook for each item type it works
  with: the type's overview, its lifecycle, and this role's own Enter, Do, Hand off and Watch for
  guidance. No other role's guidance is in it;
- **its memory index**, under a `## Memory` heading (`sq memory <slug> list --raw`);
- **the board's current notices**, under a `## Board` heading (`sq board list --raw`), each with
  its full text;
- **how to use `sq`** (`sq-how-to`) and **its memory notebook and the board** (`sq-memory`).

The agent file itself names the two commands left to run: `sq mine <slug>` and `sq inbox <slug>`.
A role skill or `sq-how-to` that cannot be rendered (`sq` missing from the `PATH`, a squad stopped
for a schema upgrade) leaves one line naming the command to run by hand, and the agent still starts.
[roles.md § "The role skill"](roles.md#the-role-skill) covers what a squad can add to it.

**Operators are the humans, not roles.** The people you work with are tracked as `operator` items
(`op-<firstname>` slugs; see the "Operators (people)" roster in `CLAUDE.md`). An operator's body is
their profile, which `sq operator <slug> show` prints and `sq operator <slug> body` records (see
[roles.md § "The operator profile"](roles.md#the-operator-profile)). Assign manual steps or hand
work to a person with `--assignee op-<slug>`, and when recording a human's own words (a comment, or
a review point you reformulated) attribute it with `--as op-<slug>` (or `--author op-<slug>`).

## Opening a new squad: the interview

The first time the manager greets an operator in a fresh squad, it can open with a short init-time
interview about how this team wants work run — and close it by writing a bespoke skill (a "run the
dev loop" skill, say) and scoping it to the roles the answers apply to:

```bash
sq skill add "run-the-dev-loop" --desc "How this team wants work run."
sq skill run-the-dev-loop body --file loop.md
sq skill run-the-dev-loop link-role manager
sq skill run-the-dev-loop link-role reviewer   # one role per call — repeat for each
```

The answers then become durable, discoverable guidance instead of a conversation that evaporates and
has to be re-had one correction at a time. [roles.md](roles.md#managing-skills) is the home for the
skill surface itself; the sequence above is that surface with the interview's own slug in it.

**Scope it wider than the manager wherever the answers reach wider.** A role preloads only the
skills linked to it, so a skill scoped to the manager alone is loaded by manager sessions and by no
others. Several of the areas below are not manager-shaped — the quality bar, the commit and release
conventions, and what needs confirming before something destructive all govern what a developer or a
reviewer does, and those agents need the answers in their own sessions.

**This is a suggestion, and an operator can decline it outright.** `sq` does not run the interview:
there is no interview command, nothing prompts for it at `sq init`, no file is scaffolded from it,
and nothing checks that such a skill exists or that it covers any particular ground. The skill it
produces is ordinary authored content, exactly like any other custom skill.

That is deliberate rather than unfinished. What `sq` guarantees is structure, not method: every item
carries a stable identifier, has a declared status and a lifecycle that governs how it may move, and
keeps its state in frontmatter rather than in prose. *Which* types, statuses and lifecycles a squad
declares is the squad's own call (see [overrides.md](overrides.md)), and so is how the team runs day
to day — a command that asked the questions below would be imposing exactly the choice `sq` is
declining to make.

### What is worth asking

Seven areas, offered as prompts rather than a script. Adapt them to the operator in front of you,
reorder them, skip what doesn't apply, and stop early if they've said enough — a short answer that
gets written down beats a long one that doesn't.

**1. Autonomy and escalation.** How far should an agent get on its own before checking back?
Consider asking: should the loop run unattended, or pause at gates? What must always interrupt you
— schema or migration changes, architectural decisions, a fork in the design, spend, anything
user-facing or visual? Faced with an ambiguity, proceed on a best guess or stop and ask?

**2. Delegation and roles.** Who authors what, and which specialists are actually live. Consider
asking: which roles do you want in this squad, and do you want any of your own? Should the agent
that reviews a piece of work always be a different one from the agent that built it?

**3. Quality bar.** What has to be true before work changes hands. Consider asking: what's the
must-pass gate before a handoff or a commit? Does integrity-critical work earn a heavier review
than the rest? Should a completion claim be independently verified, or taken at its word? When does
a check get its own review item, and when does a verdict comment on the work item do? Does the
answer change when the check found nothing?

**4. Git and releases.** Consider asking: what should a commit message look like, and do you want
trailers or co-author lines on it? Who commits, who pushes, who publishes a release — and where's
the line an agent shouldn't cross on its own?

**5. Communication.** Consider asking: how much do you want to hear while work is in flight — a
running narration, or just the handoffs? How should an agent hand work to the next one? When you
say something that belongs on the record, do you want it recorded as your words (`--as op-<slug>`)
rather than the agent's?

**6. Structure and records lifecycle.** How work gets grouped, and what happens to a record once
it stops being true. Consider asking: do you prefer many small items, or one larger item broken
into sub-items owned by different people? (Either routes fine — someone assigned only a sub-item
still finds it in `sq mine`, listed on the parent's row and tagged with the sub-item they own, and
`sq workload` counts item and sub-item assignments in separate columns.) When a decision or a
requirements document stops being accurate, do you amend it in place, or supersede it with a new
item and link the two?

**7. Safety.** Consider asking: what should an agent confirm with you before doing — deletions,
history rewrites, anything not easily undone? Are you comfortable with several agents working in
parallel, or would you rather they were sequenced?

## The loop

```
   scope ──▶ create ──▶ set body (sq body) ──▶ track status ──▶ hand off
     ▲                                                      │
     └──────────────────── @mention / inbox ◀──────────────┘
```

1. **Scope** — see what exists and what's waiting for you:
   ```bash
   sq list --status InProgress        sq tree           sq task 3 show
   sq inbox <your-role>               # open items that @mention you
   ```
2. **Create** with `sq` (it allocates the ID and prints the file path):
   ```bash
   sq create task "Validate token" --parent FEAT-<n> --author <your-role>
   # → created TASK-<n> → squads/tasks/TASK-NNNNNN-validate-token.md
   ```
3. **Set the body with a command** — never hand-edit the file. Items and sub-entities both take
   `-m "…"` (repeatable) or `--file`; read back with `sq show` / `sq <kind> show`, which is also
   the only way to read one:
   ```bash
   sq task 3 body -m "Validate the JWT exp + signature; reject clock skew > 60s."
   sq feature 2 add-story "As a user, I want to log in" -m "Acceptance: …"
   sq task 3 add-subtask "Check expiry" --story USn
   sq task 3 subtask 1 body -m "Reject tokens past exp; cover clock skew."
   ```
4. **Track status** as work moves (validated per type):
   ```bash
   sq task 3 status InProgress
   sq task 3 status Done
   ```
5. **Hand off & discuss** — leave dated notes attributed to yourself; `@mention` to notify another
   role:
   ```bash
   sq task 3 comment --as architect -m "Reuse the clock abstraction" -m "@qa verify expiry edges"
   ```
6. **Link context** so the next agent reads the right things:
   ```bash
   sq task 3 ref add GUIDE-<n> --kind implements
   sq task 3 ref add BUG-<n> --kind fixes
   ```

## Working directly with the operator

The operator sometimes talks to you directly, for live work or debugging. The rest of the team
sees only what reaches `sq`, never the chat, so keep the record as you go:

- **Anchor the work to an item.** Read the item first with `sq <type> <n> show --full --comments`
  (body, sub-entities and discussion: decisions often live in the comments). If the work is
  genuinely new, create the item before you start, so what you do has an ID to hang on.
- **Keep status honest.** Move the item to its lifecycle's first working state
  (`sq <type> <n> status <status>`) when you actually start, not before, and move it on as the work
  does. `sq <type> <n> show` gives the current status and `sq workflow lifecycles` the legal moves.
  Don't leave it stale when you stop.
- **Hand back through `sq`.** Before you wrap up, leave a comment summarising what changed:
  `sq <type> <n> comment --as <your-slug> -m "…"`, or `--file` for anything holding a backtick or a
  code block, since the shell substitutes an unescaped backtick in a quoted `-m` before `sq` runs.
  `@mention` the role that acts next. That comment is how the coordinating agent, and the next
  agent, pick up where you left off.
- **Scope the comment to the right discussion.** A story, subtask or finding has its own
  discussion: `sq <type> <n> <kind> <k> comment` is for a note about that one sub-entity, and
  `sq <type> <n> comment` for anything that spans the item, including a hand-off. `sq inbox` finds
  a mention wherever it is.
- **Record decisions as they are made.** When the operator decides something, put it on the item
  at once, in their name: `sq <type> <n> comment --as op-<slug> -m "…"`.
- **Stay in lane.** File what you find out of scope as its own item (a bug, a task) and link it,
  rather than widening the work in hand.

## Golden rules

- **`sq` owns the whole `.md` file** — frontmatter, markers, and every region. You author the content
  through commands, not your editor.
- **Never hand-edit a `.md` file.** Set bodies with `sq <type> <n> body` / `sq <type> <n> <kind> <k>
  body`, comment with `sq <type> <n> comment`, change state with `sq <type> <n> status`/`update`.
  `sq check` flags broken markers.
- **Never read a `.md` file directly either.** An item is read through `sq <type> <n> show`
  (`--full --comments` for the whole dossier — body, sub-entities and discussion), never by opening
  the file. The command resolves state the file does not carry, so a direct read returns strictly
  less than the command.
- **`body` replaces; it does not add.** Writing over a body that already has prose in it is refused,
  so you can run it to find out whether one is occupied. Use `--append` to add to what is there, and
  `--force` only when you mean to discard it. This applies to a sub-entity's body, a role's and a custom
  skill's too.
- **The `.md` frontmatter is the source of truth** — don't hand-edit `id`/`status`/`parent`; use the
  commands so the index stays in sync.
- **Reference items by ID** (`TASK-<n>`, `GUIDE-<n>`) in prose and comments so developers and
  reviewers can follow the trail.
- **Work chronologically** and comment as you go — the dated discussion entries are the history.

## By role (quick notes)

- **Product owner (Nina Product)** — write features + user stories; define acceptance criteria.
- **Tech lead (Olivia Lead)** — break features into tasks (`--parent` the feature), map subtasks to
  user stories, link bugs/reviews with `--kind fixes|addresses`, sequence and unblock.
- **Developer (any role holding the `dev` capability, such as `python-dev`)** — implement the assigned task; write tests; comment progress; address
  review feedback.
- **Reviewer (Paul Reviewer)** — drive review items to a verdict; request changes or approve.
- **QA (Mara Tester)** — derive tests from user stories; verify fixes; file bugs.
- **Architect (Robert Architect)** — record ADRs; author guides; review designs.
- **Tech writer (Theo Writer)** — keep guides and docs current; sweep delivered text for build-process narration before an increment closes.

Lost? Run **`sq workflow`** for the cheatsheet, or `sq <command> --help`.
