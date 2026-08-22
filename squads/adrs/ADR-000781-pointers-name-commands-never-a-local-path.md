---
id: ADR-781
sequence_id: 781
type: decision
title: Pointers name commands, never a local path
status: Proposed
author: architect
refs:
- FEAT-693
- ADR-776
- ADR-75
- ADR-133
- ADR-697
- ADR-141
- FEAT-33
- ADR-775
- ADR-777
- ADR-155
- ADR-85
- ADR-422
- BUG-784
created_at: '2026-08-22T09:44:15Z'
updated_at: '2026-08-22T10:13:02Z'
---
<!-- sq:body -->
## Context

A generated pointer is squads' projection of one roster entry into an agent host's own
configuration. Both `.claude/` pointers instruct the agent with a **local file path**:
`@{{ squad_path }}` at `_rendering/templates/claude/pointer_agent.md.j2:25` and
`pointer_skill.md.j2:8` (read), resolved by the host's own file loader before squads is in the
picture at all.

That instruction is unsatisfiable when the CLI is a client to a squads server (FEAT-33, EPIC-29):
there is no local squad directory for the path to name, so the pointer's one load-bearing line
resolves to nothing and the agent starts with an identity and no definition.

**And the path is only the visible half.** A pointer's *contents* are a copy of squad state, and
`.claude/` is committed — so under remote mode a pointer is a tracked snapshot of state the
repository does not hold, silently wrong from the moment the server moves. That is the same failure
one layer up, and §1 alone does not reach it; §2a rules on contents for that reason.

**The exposure is wider than the two `@` templates.** A grep for the `@` form finds exactly those
two, but the `agents_md` backend carries the same local path in a different spelling:
`**Squad file:** \`{{ squad_path }}\`` at `_rendering/templates/agents_md/role_entry.md.j2:11` and
`agents_md/skill_entry.md.j2:5` (read). Four templates, two backends. The `agents_md` pair is
weaker — it *displays* a path rather than instructing a load, so an unreachable path degrades to a
useless line rather than to a missing definition — but it is the same class and it is the same
`squad_path` context value, so it moves with them or the rule is only half true.

**Who this is decided for.** squads is a tool other teams adopt; this repository's own use of it
only tests that it works. So the case that governs is an adopter cloning a project they did not set
up, with their own overrides and their own agent host — not what is already convenient here. Two
consequences run through everything below: an adopter's *first* run is the one that must work, and an
adopter has no baseline for what a correct pointer looks like, so anything wrong reads to them as
squads being broken rather than as a command they never ran. The third-party hosts are the main case
for the same reason (§2d): Codex, Copilot and Cursor users are adopters by definition, and nobody
dogfooding this repository uses them.

**Two facts change what the replacement has to carry.** Both are read, and both mean less new
material than the problem suggests.

- **The slug-bound startup command set already exists**, one hop too far away. The role *body*
  template renders it with the slug substituted — `sq memory <slug> list`, `sq memory <slug> show
  <slug>`, `sq board list`, `sq mine <slug>`, `sq inbox <slug>` (read: `agents/role.md.j2:30-36`) —
  and the agent reaches it only *through* the `@` reference that is being removed.
- **`CLAUDE.md`'s managed region already states the same protocol generically**, with a `<role>`
  placeholder the agent must substitute for itself (read: `claude/claude_section.md.j2:53-61`). So
  two renderings of one protocol already ship; the direction relocates one of them rather than
  creating a duplicate.

## Decision

### 1. No materialised file squads generates may carry a local file path

The rule is about the *path*, not the `@` sigil: a displayed path is unusable for the same reason an
instructed one is unresolvable. All four templates lose `squad_path`, and the `squad_path` context
value stops being computed for them.

The rule's boundary: this governs files squads writes **into another tool's configuration**. It does
not govern `sq`'s own output, which may name a path freely because the caller has a working `sq` by
construction — and it does not govern a path an adopter writes in their own prose.

### 2. A pointer names the command, and carries enough that a first turn needs no fetch

The pointer carries three things, in this order of priority when space is contested:

1. **Identity** — full name, slug, role title. Already present and unchanged.
2. **The slug-bound startup command set**, moved from the role body: the memory, board, `mine` and
   `inbox` commands with the slug already substituted.
3. **One command that renders the full definition** — `sq role <slug> show` for an agent pointer,
   `sq skill <slug> show` for a skill pointer. Both exist and both render the definition today
   (driven: `sq role architect show` prints a computed card plus the stored body).

It **names** the definition command rather than embedding the definition. The trade, stated rather
than implied:

- **Embedding** would make a first turn self-sufficient offline, and would reintroduce the defect the
  cache in the derived-views decision exists to remove: a second stored copy of the definition, in a
  file the backend regenerates, going stale against the role item between syncs — and, unlike the
  role body, stale in a file squads is not the only writer of.
- **Naming** costs one command on the first turn and is correct in both modes. What it loses is the
  offline case, and the loss is bounded precisely: an agent whose `sq` cannot reach its squad has its
  identity and its startup commands and not its mission — which is the right failure, because every
  one of those startup commands would fail too. An agent that cannot read its queue cannot work; the
  pointer should not pretend otherwise by carrying a mission it can act on with no board.

Priority 2 is what makes this a real improvement rather than a lateral move. Substituting the slug
in the pointer removes a step an agent otherwise performs by reconstruction, which is the same
failure class as acting on a summary instead of a literal command.

### 2a. What a pointer may contain: the irreducible set, and the rule above it

A path that does not resolve is only the visible half of the problem. `.claude/` is **committed**
(driven: `git ls-files .claude/` lists 22 files; only `settings.local.json` is ignored), and each
agent pointer materialises seven values of role state — slug, description, model, colour, spawn
authority, the resolved skills list, and the full name in its body. Under remote mode that makes a
pointer a committed snapshot of state the repository does not contain: the server moves and every
clone is wrong until a person syncs and commits, with nothing reporting it. Removing the `@`
reference does not touch that, so §1 is necessary and not sufficient.

The host-reads-files argument establishes that a pointer **file** must exist — a host enumerates
files to discover that an agent exists at all, and cannot run a command to find out. It establishes
nothing about the file's contents. So the contents need their own rule.

**The containment rule.** A pointer materialises a value only when both hold:

1. **the host consumes it at or before spawn**, and
2. **a runtime fetch cannot substitute for its *effect*** — which is true exactly when the value
   *restricts* or *configures* the session, and false when it merely *supplies* content the agent
   could obtain for itself.

The second clause is what does the work, and the word *effect* is load-bearing rather than decorative:
the test is never "can the agent get this information" but "can the agent obtain what setting this
value did". A restriction cannot be re-imposed from inside the session it was meant to bound; a
configuration has already taken hold before the agent's first turn; only plain content can be
fetched later. Reading the clause as being about information is the misapplication it is worded
against — see the skills list below, where this decision made exactly that error.

**Applied field by field.** The "cannot drift" and drift-consequence columns are why each ruling
differs; they are not decoration.

| Value | Host status | If it goes stale | Ruling |
| --- | --- | --- | --- |
| `name` (the slug) | **required** — the dispatch identifier; without it there is no agent to spawn | **cannot drift.** Slugs are canonical and not renamable, frozen by ADR-85 §4 — a team renames who the architect is called, never the slot | materialised |
| `description` | **required** — the host's own selection text, read to decide whether to route here, before any agent exists to run anything | a routing hint is stale; the agent still spawns and still behaves correctly, because its definition is fetched | materialised |
| `disallowedTools` | the capability boundary, expressed in the definition the harness loads and bound to the agent **type** at spawn (ADR-155 §1) | **a leaf keeps spawn authority the squad revoked** — a capability escalation against that decision's own threat model | materialised, and the one field whose drift is an error (§2c) |
| `model` | optional; omitting the key silently runs the agent on the session default (read: `_backends/_claude_code/_frontmatter.py:14-22`) | the agent runs on the wrong model, silently — the same failure `model_drop_warning` already reports at write time | materialised: the host has chosen a model before the agent can speak |
| `color` | optional, cosmetic | cosmetic | materialised, and explicitly not load-bearing |
| the resolved `skills` list | the **preload** setting: it decides what is in context on turn one | a withdrawn skill is preloaded, or a newly scoped one is missing — and this is the most drift-prone value of the seven | materialised, and the reason §2c's comparison is load-bearing rather than optional |
| `full_name` (body prose) | none; squads' own text | the agent calls itself by a name the squad no longer uses | **not materialised** — arrives with the definition (§2) |

**The skills list stays, and clause 2 is what says so — I had it on the wrong side.** This is the
case the rule has to earn, so the correction is recorded rather than quietly applied.

My argument for removing it was that a preload *supplies* rather than *restricts*: the agent can
read a skill later, so a fetch substitutes. That tested the wrong thing. Clause 2 does not ask
whether the agent can obtain the **information**; it asks whether a runtime fetch can substitute for
the **configuration effect** — which is why the clause reads "restricts *or configures*". A preload
list configures the session before the agent exists. The agent can read a skill on turn three; it
cannot make the host preload one, and it cannot retroactively have had that context on turn one. The
effect is unobtainable from inside the session, exactly as `model`'s is.

So the parallel with `model` is exact, and it is the one I should have noticed: I kept `model` on the
reasoning that "the host has chosen a model before the agent can speak," and the host has chosen the
preload set at precisely the same moment. Nothing about clause 2 needs to change; a misapplication of
it does.

**What survives of the fan-out argument, and where it belongs.** The observation itself holds and is
worth keeping: the skills list is the only entry that is not a field of the role but a *resolved
projection over other items' edges* — system membership plus every skill carrying a `scopes` edge to
this role, recovered by inversion (read: `_services/_base.py:1156-1181`) — so it drifts on edits to
items the pointer never names. That is a claim about **drift risk**, not about classification.
Clause 2 decides whether a value is materialised; the fan-out decides how much the drift check
matters. It therefore transfers to §2c, where it makes the comparison load-bearing.

**And ADR-422 does not support the conclusion I cited it for.** That decision refused to persist a
fan-out projection *because a computed alternative reached the same reader* — its option D, "serve
the same need on demand" via `sq graph`. Here there is no such alternative: no command an agent runs
can put a skill into the context of a turn that has already begun. ADR-422's reasoning turns on the
availability of the on-demand path, and the availability is what differs. Citing it for removal was
measuring against a clause that does not govern this case.

**Skill pointers take the same rule with the same result.** A skill pointer's `name` and
`description` are host-consumed before anything can run, so they stay; its body already becomes a
fetch command under §2. Nothing else is in it.

### 2b. The generated pointers are committed, in every mode

`.claude/` was never one kind of thing, and per-directory is the wrong granularity. `settings.json`
is **user-owned, merged** config — the backend preserves whatever is already there and only adds
missing permission rules (read: `_backends/_claude_code/_backend.py:47-62`). The pointers are the
opposite: pure projections, regenerated wholesale. So the question is asked per artifact, and for the
projections the answer is the same in every mode: **committed.**

**The principle, not a preference: whether to ignore a generated file is the adopter's repository
decision, never squads'.** The tool already draws that line and draws it narrowly.
`ensure_root_tmp_ignored` appends exactly one temp-file pattern to a root `.gitignore` and its own
docstring commits to doing so "without touching any of its other (adopter-owned) content" (read:
`_services/_maintenance.py:68-84`). squads ignores its own crash detritus and nothing else.
Committing generated pointers is that same line drawn on the other side of itself: we produce the
artifact, we do not decide whether their repository tracks it. An adopter who gitignores `.claude/`
is making a supported choice, and this decision does not make it for them.

**And the onboarding case is a first-run failure, not an edge case.** squads is a tool other teams
adopt; this repository's own use of it only tests that it works. An adopter clones a project, opens
their agent host, and expects the ten agents the roster advertises to be there. If the pointers do
not exist until somebody runs a command, the first thing they meet is a roster claiming ten agents
and a host finding none — with nothing connecting the two facts. That is the failure the ruling
exists to prevent, and it happens on run one, to a reader with no baseline for what correct looks
like.

**What this accepts rather than answers.** The objection against committing under remote mode was
that a pointer would be a snapshot of state the repository does not contain, and *no commit could fix
it for everyone*. That objection is not refuted by the ruling; it is **accepted as a cost**. So
committed-and-possibly-stale is the sanctioned state, and **detection is the only remaining
safeguard** — which is why §2c is load-bearing twice over: once because the most drift-prone value of
the seven stays materialised (§2a), and again because a committed pointer under remote mode can be
wrong for every clone at once. A decision that accepts a staleness cost owes a detection design, and
that is the next section rather than an afterthought.

**One deferral this ruling closes.** The bootstrap question — what produces a clone's pointers before
anyone thinks to run a command — is answered: the clone has them, because they are committed. What
remains deferred is narrower and sits in §2c.

### 2c. Detection reaches the operator unprompted; `sq check` compares, and never stamps

Nothing reports any of this today, in any mode, and the gap is wider than drift: `sq check` does not
notice a **missing** per-entry pointer at all. BUG-784 drove it — deleting one pointer, one skill
directory, one backend's whole set, or both backends' sets together leaves `sq check` at exit 0 with
no mention, every time, while deleting `CLAUDE.md` is caught at exit 3. `_backend_reconciled` reports
on exactly the paths a backend declares (read: `_services/_validators.py:509-525`), and both bundled
backends declare only their compiled top-level document (read:
`_backends/_claude_code/_backend.py:416-422`). No per-entry path is declared, so none is ever looked
for.

**Presence and currency are two findings over one widening, and presence comes first.** They are not
alternatives and not one piece of work:

- **Presence** — does the declared path exist. A `stat` per live entry. It is the strictly weaker
  question and the prerequisite: a content comparison against an absent file is a category error,
  with nothing to compare and no useful message. This is BUG-784's fix.
- **Currency** — does the file's content match a fresh render. A render per live entry.

Both need the same thing: the per-entry artifacts must become **declared paths**, which is the single
widening both findings sit on. Sequencing presence first is not politeness about a filed bug; it is
that currency has no meaning until presence holds.

**The hard constraint on that widening, which must not be discovered later.** Retirement
*deliberately* removes a pointer, and today that behaves correctly and `sq check` stays clean on both
sides of it (driven, BUG-784: retiring `qa` removes both backends' entries via `remove_artifacts` and
check stays at exit 0; reactivating regenerates them and it stays clean). So the declared set must be
scoped to the roster's **currently live** entries — the same predicate `_project_roster_item` already
uses to decide who gets an artifact at all (read: `_services/_base.py:1387-1391`) — and never to a
fixed or historical slug list. Anything else turns every retire/reactivate cycle into a false
positive on the retired side.

**Detection must be unprompted, because the reader has never seen a correct pointer.** Our own team
notices drift by living in this corpus; an adopter has no baseline, so a wrong pointer is simply how
their tool behaves, and they attribute it to squads being broken rather than to a sync they never ran.
"The recourse is `sq sync`" is only an answer if something tells them so without being asked. Three
surfaces, split by cost:

1. **The root-callback notice — unprompted, every invocation, presence only.** `version_notice`
   already prints exactly this shape of advisory to stderr, non-fatal, on any `sq` command (read:
   `_cli/_common.py:1128-1140`). Today it keys solely on `.squads.toml`'s recorded `squads_version`,
   so a clone whose pointers are missing *at the current version* is told nothing — precisely the
   adopter's first run. Presence joins that notice because it is a `stat` per live entry and can
   afford to run on every invocation. Currency does not: a render per entry on every command is not
   a cost an advisory may impose.
2. **`sq check` — asked, presence and currency both**, with the detail and the exit code a CI gate
   needs.
3. **`sq sync` — the fix, and it must say what it changed.** Today it regenerates a missing file with
   no message that anything had been missing (driven, BUG-784), which under committed artifacts is
   the wrong silence twice: the operator learns neither that there was a fault nor that a commit is
   now owed. `sync` already returns notices to its caller, so this is a report, not a mechanism.

**The operator's recourse, stated plainly.** Run `sq sync`, then commit what it rewrote. Nothing
beyond `sq check` plus `sq sync` is needed *as machinery* — the missing pieces are all reporting: the
unprompted notice must see the filesystem, and `sync` must say what it fixed.

**By comparison, not by a stamp**, and the reason is ownership rather than convenience. ADR-85's
`override-base` stamp exists because an override is **user-owned**: a human authored the body, so
squads cannot re-derive it and a version is the only provenance available. A pointer is **tool-owned**
and re-renderable, so comparison is available — and it answers the question that matters ("is this
wrong") instead of the one a stamp answers ("how old is this"). Reaching for the stamp here would
import a mechanism built for the opposite ownership, and would flag a correct pointer for predating a
release that changed nothing about it.

**The seam already names this gap.** `AgentBackend.managed_paths`'s own docstring calls itself a
"present-only check — not a currency/drift check" (read: `_backends/_base.py:192-202`). Currency is
the verb that docstring says it is not, and it arrives as §2d's pure-render question, compared against
the path the backend itself declares — so the checker never reaches into a host's directory on its
own (invariant 6).

**This does not breach the never-read-back rule, and the difference has to be stated because it will
be raised.** That guard forbids a backend *recovering a declaration* from its own output — the failure
it was written for is `write_managed` recovering a mission by matching the `**Mission:**` prefix of a
line it had just rendered, so relabelling a template emptied every mission with `sq check` clean
(read: `tests/meta/test_a_backend_never_reads_back_its_own_generated_output.py`, and
`_backends/_agents_md/_backend.py:66-79`). A drift check reads output as the **subject under test**;
every declaration still comes from the item, and the render is the expectation, not the source. The
direction of authority is the thing the guard protects, and it is preserved.

**Two severities, keyed on §2a's own distinction** rather than a new judgement: a drifted or missing
**restriction** is an **error** — a stale pointer granting a leaf the spawn tool the squad revoked is
a live regression against ADR-155's threat model, and is not repairable from inside the session it
governs. Everything else is a **warn**: `sq sync` fixes it and nothing unsafe happens meanwhile.

**The deferral, named and now narrower.** Presence is answerable offline in every mode — it is a
filesystem question. Currency compares against squad state, so under remote mode it needs the
server's, and whether that check runs against a cache, requires connectivity, or degrades to "cannot
verify" is remote mode's design (FEAT-33 / EPIC-29 are Draft). The offline half is fully decidable
today and is what this clause commits to; the remote half inherits the mechanism and owes a
reachability answer. Presence gives every mode an offline floor regardless.

### 2d. The rule is universal; every answer is per host, and the ABC asks in the host's own terms

Codex, Copilot and Cursor backends are planned, and their users are **adopters by definition** —
nobody dogfooding this repository uses them. So the per-host contract is what most users meet first,
and Claude Code, the one host whose contract this decision was derived from, is the least
representative example available. A rule reasoned from what it happens to emit would be relitigated
by every backend after it.

The codebase already models the right frame and this section generalises it rather than inventing
one: `_VALID_MODELS` is documented as "a backend-local set, not a shared one: it describes what *this
host tool* can express, so a second backend is free to know a different vocabulary", and
`model_drop_warning` exists because a value can survive storage and then silently fail to render —
**reported rather than validated twice** (read: `_backends/_claude_code/_frontmatter.py:1-10`,
`:24-48`). That is one field's worth of the shape a whole entry needs.

**What is universal: the containment rule.** Both clauses are stated about a host and its
configuration, not about any format — "the host consumes it at or before spawn" and "a runtime fetch
cannot substitute for the effect". Any host can be asked both.

**What is per-backend: every answer, the irreducible set included.** `name` and `description` are
Claude Code's irreducible set, derived from *its* discovery contract. Asserting them universally would
be the same overreach as a shared model vocabulary: another host may key an entry by filename and need
no `name`, may do no host-side selection and need no `description`, or may require a field Claude Code
has no concept of. The *notion* of an irreducible set is universal; its membership is local.

**So the ABC asks five questions, each phrased so an author who has read only their host's
documentation can answer it — and none of which requires reading squads' internals.** Each traces to a
ruling above that cannot be evaluated without it.

1. **Can an agent running under this host execute a command?** Whether the host gives an agent any
   way to invoke `sq`. This is the question clause 2 turns on, and it is the one this decision most
   needs asked rather than assumed: a host that cannot run commands can never satisfy "a fetch
   substitutes", so for it the rule keeps everything it can express. A host that can — Claude Code
   demonstrably does, which is §2's whole premise — fetches whatever only *supplies*.
2. **Which of the values squads projects does this host's configuration have a place for?** The
   expressible set, generalising `_VALID_MODELS` from one field to all of them. Anything squads
   declares and this host cannot express is **reported once, at write time, and dropped — never
   silently**, on `model_drop_warning`'s precedent: report what this backend just failed to render,
   refuse nothing, and do not validate a second time against a host-local vocabulary at storage time.
   A host with no notion of preloading answers "no" here for the skills list and says so once.
3. **Which of those must be present for this host to find and dispatch an entry at all?** The
   irreducible set, from the host's own discovery contract.
4. **Which of those constrain what the session may do, rather than configure how it runs?** The
   capability boundary, however the host spells it. `disallowedTools` is Claude Code's spelling of
   ADR-155's attenuation; another host will spell it differently, express it partially, or lack it.
   §2c's error severity is defined over this answer.
5. **What would you write for this entry, without writing it?** The pure render §2c compares against.

Questions 1, 2 and 4 together give a property worth naming: **a backend may be unable to honour a
constraint squads declares, and that is reportable rather than forbidden.** A host with no way to deny
a tool cannot enforce ADR-155's attenuation. The honest response is a warning that this host cannot
express the boundary — not a refusal to support the host, and not silence.

This extends ADR-133's de-Claude-ification from names and path ownership to **contents**: that
decision established that a Claude backend returns a pointer-file artifact while an `AGENTS.md`
backend returns a section-update artifact, both through one neutral entry method. These five questions
are the same move applied to what those artifacts may carry.

**What each future backend's own decision keeps.** Deliberately not settled here, because it is not
knowable without that host's documentation: its configuration format and field names, its model and
capability vocabulary, whether it supports preloading, whether its agents can run commands — and
therefore its irreducible set and its answers to all five. This decision fixes the questions and the
rule that consumes the answers; a backend answers them when it is built, and no backend has to reopen
the rule to do so.

### 3. Where the protocol lives: one declaration, two renderings

The split, so the two surfaces cannot drift:

- **The pointer** carries the **slug-bound commands** — the concrete form, for the agent whose slug
  it is.
- **`CLAUDE.md` / `AGENTS.md`'s managed region** keeps the **protocol and its rationale** — why both
  queue surfaces are read and neither subsumes the other, what memory is versus what the board is.
  That reasoning is shared by every agent and belongs stated once, not repeated per pointer.
- **Both render from one declared list in code**, never from two hand-maintained texts. This is the
  same rule the derived-views decision states for a projection: one derivation, many renderings. A
  command added to the startup set appears in both surfaces or in neither.

The role body's copy (`agents/role.md.j2:30-36`) is **removed**, not left beside the pointer's. Two
slug-bound copies of one command set, in two files with two regenerators, is the duplication this
clause exists to prevent.

### 4. Invariant 5 is reworded to state the containment rule

`CLAUDE.md:107` reads: "**`.claude/` files are pointers**, not content. Real definitions live under
`squads/`." Both clauses are true and both mislead, in different ways. "Real definitions live under
`squads/`" locates the definition by **directory**, which is the assumption remote mode breaks. And
"pointers, not content" reads as satisfied by any file that is merely *short* — which is how seven
fields of role state came to sit in one without anybody judging that a violation.

The rewording keeps the invariant's force, drops the locality, and states the containment rule so the
next field has a test to fail:

> **`.claude/` files are pointers**, not content. A pointer carries only what the host must read
> before an agent can run — its identity, the text the host selects it by, and the constraints
> squads imposes on the session — plus the commands that fetch the rest. Anything `sq` can answer,
> a pointer does not hold.

That is a stronger statement of the same rule: it forbids carrying a value the agent could ask for,
which the old wording permitted by only saying where the definition lived.

### 5. The two backends that exist, as worked answers to §2d

- **`_claude_code`** answers "yes" to question 1 — its agents run `sq`, which is what §2 is built on.
  So both pointer templates lose `@{{ squad_path }}` and gain the command set, and what remains in
  frontmatter is the host-consumed set: `name`, `description`, `model`, `color`, the `disallowedTools`
  attenuation, and the resolved `skills` preload (§2a). `full_name` and the definition are fetched.
- **`_agents_md`** answers question 1 with **"not knowably"**, and that is the answer, not a gap. It
  compiles a single `AGENTS.md` for tools whose command-execution capability is declared by whoever
  builds the backend, not by us — so it takes the generic protocol form from the managed region rather
  than a slug-bound set per entry, and both entry templates lose their `**Squad file:**` line.

**Why the roster prose stays in the compiled documents, derived rather than exempted.** `AGENTS.md`
keeps full name, slug, title, mission and responsibilities, and `CLAUDE.md`'s managed region keeps its
three-field roster line (read: `agents_md/role_entry.md.j2`, `claude/claude_section.md.j2:8-12`). Those
values drift exactly as a pointer's would, so §2a's challenge lands here too, and the outcome differs
for one declared reason: **clause 2 asks whether a runtime fetch can substitute, and a host that
cannot run a command has no fetch available.** That is question 1's answer doing the work.

The earlier framing of this — "tools whose command-execution capability squads does not know" — was
wrong, and worth correcting rather than rephrasing. Not knowing a host's capabilities is not a gap in
our knowledge to be worked around; it is the **normal condition for every backend an adopter brings**,
and a rule that only produces a defensible answer for the two hosts we happen to have built is not a
rule. The fix is that the question is *declared* by the backend author, who has the host's
documentation, instead of assumed by us, who never will. The compiled document keeps its prose because
its backend answers question 1 in the negative — the same rule, a different answer.

So a compiled document is not a privileged class. If a future backend targets a host that *can* run
commands, it answers "yes" and inherits the containment rule in full; it does not inherit
`AGENTS.md`'s outcome. The cost of the negative answer is named: it is materialised state, it drifts,
and §2c's presence and currency checks cover it because both documents are declared paths already.

Neither backend reads back its own output, and neither may start
(`tests/meta/test_a_backend_never_reads_back_its_own_generated_output.py`; read:
`_backends/_agents_md/_backend.py:66-79` for the recorded failure when that rule was broken). §2c's
comparison is a checker reading a backend's output through question 5, never a backend reading its own.

### 6. The release ordering, stated once for every template-touching change

A bundled-template edit forces a template-manifest regeneration, and the generator replaces one
version's entry **wholesale**, keyed on `[project].version` (read:
`scripts/gen_template_manifest.py:45-50`, `:121`). That version is still `0.13.0` (read:
`pyproject.toml:3`), which is a shipped release. Regenerating before the version bump overwrites the
shipped release's recorded hashes and corrupts the provenance `sq override diff` reads. **The bump
comes first, then the regeneration** — the ordering TASK-768 already carries.

This section is the single statement of that ordering for the whole set of changes now touching
bundled templates, so it is not repeated in three decisions and cannot drift between them: the four
pointer/entry templates here; the retirement of the closed-vocabulary text from
`workflow_static.md.j2`; and the removal of `role.md.j2`'s skills block and the item templates'
summary regions. All of them regenerate the same manifest, so all of them queue behind the same bump.

The managed-section golden and the generated-agent-text guards move with the templates in the same
change.

**Two frozen migration runners render these same pointer templates** — `_migrations/_v0_4_to_v0_5.py:118-128`
and `_v0_8_to_v0_10.py:113` (read), each passing `squad_path` into `claude/pointer_skill.md.j2`. That
is not a break to fix and must not be "fixed" by pinning a copy of the template inside the runner. A
migration is frozen against the *corpus vocabulary* of the schema version it transforms, never against
regenerable artifacts: a pointer is regenerated, never migrated, so a runner that rewrites one should
emit today's pointer, not a historical one. What the change does owe is dropping the now-unused
`squad_path` argument at both sites, since a template that no longer declares the variable makes the
kwarg dead rather than wrong.

## Consequences

- **A first turn costs one command per agent**, and gains an instruction that resolves in every mode.
- **`sq role <slug> show` becomes an agent's primary definition read**, which promotes a
  pre-existing duplication into the agent's context: it prints mission and responsibilities twice,
  once from the computed card and once from the stored body beneath it (driven). The two can
  disagree, because the card resolves a project override while the body carries whatever the last
  `sq sync` wrote. Settling that is this decision's to own, and the honest options are to drop the
  overlapping card rows or to render the body from the resolved definition on every show.
- **The pointer stops being readable as a standalone document.** Today a person opening
  `.claude/agents/architect.md` can follow the path by hand; afterwards they run a command. That is
  the intended trade and the reason invariant 5's second sentence is reworded rather than deleted.
- **`squad_path` has exactly seven producers and no surviving consumer.** Five backend render sites
  (read: `_backends/_claude_code/_backend.py:223`, `:355`, `:377`;
  `_backends/_agents_md/_backend.py:142`, `:160`) and two migration runners pass it into the four
  templates that are dropping it, so it becomes a dead context value at every site rather than a
  narrowed one. `ctx.root_relative` / `ctx.rel` may lose their last caller on this path too, which is
  where the dead-code scan earns its keep rather than a guess here.
- **The resolved skills list stays in the agent pointer**, so `ctx.resolved_skills_for` keeps its
  call site (read: `_backends/_claude_code/_backend.py:356`). It is the setting that makes the host
  preload the right things, and no command an agent runs can put a skill into a turn that has already
  begun.
- **Three surfaces gain work, and it is reporting rather than machinery** (§2c): the per-entry
  artifacts become declared paths scoped to the live roster predicate; the unprompted root-callback
  notice starts seeing the filesystem instead of only `.squads.toml`'s recorded version (read:
  `_cli/_common.py:1128-1140`); and `sq sync` reports what it regenerated, so an operator learns both
  that there was a fault and that a commit is owed.
- **Presence ships before currency**, over one widening — a comparison against an absent file has
  nothing to compare. BUG-784 is the presence half.
- **Tracking is per-artifact, and the generated pointers are committed in every mode** (§2b).
  `settings.json` is user-owned and stays committed for a different reason. An adopter who gitignores
  `.claude/` themselves is making a supported choice this decision does not override — and hits the
  same first-run gap presence detection now closes.
- **Committed-and-possibly-stale is accepted as a cost, not argued away.** Under remote mode a
  committed pointer can be wrong for every clone at once, and no commit fixes it for everyone. That
  is what makes §2c a safeguard rather than a convenience.
- **Nothing about item markdown changes here.** This decision removes a *reader* of role and skill
  bodies; what those bodies contain is the derived-views decision's subject.
- **One deferral remains, narrower than before** (§2c): whether a *remote* squad's currency check runs
  against a cache, requires connectivity, or degrades to "cannot verify". Presence is answerable
  offline in every mode, so every mode keeps a floor. The bootstrap deferral is closed by §2b — a
  clone has its pointers because they are committed.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T09:48:02Z] Robert Architect:
  - Authored separately from ADR-776 rather than folded into it: this is a backend-projection question governed by the AgentBackend ABC (ADR-75/133/141/697) and bound by remote mode (FEAT-33), not a derived-view question — and separating them lets the collapse be ruled on without also ruling on pointer copy.
  - The exposure is four templates, not two. The @ form is only in pointer_agent.md.j2:25 and pointer_skill.md.j2:8, but the agents_md backend carries the same local path as **Squad file:** in role_entry.md.j2:11 and skill_entry.md.j2:5 — same squad_path context value, weaker failure (a useless line rather than a missing definition), same class. Seven producer sites feed those four templates and none survives.
  - The replacement needs less new material than it looks: the slug-bound startup command set already exists at role.md.j2:30-36 and only reaches the agent THROUGH the @ reference being removed, while CLAUDE.md managed region already states the same protocol generically at claude_section.md.j2:53-61. So the duplication already ships; the decision relocates the slug-bound copy into the pointer, keeps the rationale in the managed region, and requires both to render from one declared list in code.
  - Two things for @op-pierre before he rules. Naming the command rather than embedding the definition loses the offline case, bounded: an agent whose sq cannot reach its squad has identity and commands but not its mission — which is the right failure, since every startup command would fail too. And sq role <slug> show already prints mission and responsibilities TWICE (driven — computed card plus stored body), which stops being cosmetic once that command is an agent primary read, because the card resolves a project override and the body carries the last sync. Section 5 and the consequences name it; settling it is this decision to own.
- [2026-08-22T09:52:07Z] Pierre Chat:
  - Challenge to the reasoning that backend pointers must stay materialized: they will fail under remote mode too. The host-reads-files argument settles that a pointer file must exist, not that its contents may be a copy of squad state.
- [2026-08-22T09:52:09Z] Catherine Manager:
  - Facts behind the challenge, driven: .claude/ is committed to git (git ls-files lists every pointer; only settings.local.json is ignored), and each generated pointer materializes seven fields of role state - slug, description, model, color, spawn authority, the resolved skills list, and the full name in its body. So under remote mode a pointer is a committed snapshot of server-side state: a role changed on the server leaves every clone wrong until someone runs sq sync locally and commits the result, with nothing reporting the drift.
- [2026-08-22T10:00:21Z] Robert Architect:
  - Amended in place rather than annotated: the challenge is correct and it lands on reasoning the body relied on, so leaving it would have left the decision defending a rule it no longer holds. Added sections 2a (containment), 2b (committed or not), 2c (drift reporting), and reworded section 4 and section 5 around them. Also narrowed ADR-776 does-not-abolish paragraph, which read as a blanket licence for pointer contents when it only ever settled which decision governs them.
  - Irreducible: name and description, and nothing else. name is the dispatch identifier and CANNOT drift — slugs are frozen non-renamable by ADR-85 section 4. description is the host own selection text, read before any agent exists to run a command, and its drift mis-routes without making anything wrong once spawned. That is two of the seven fields.
  - The rule above the minimum: materialise only when the host consumes the value at spawn AND a runtime fetch cannot substitute — which is true when the value RESTRICTS or CONFIGURES and false when it merely SUPPLIES. So disallowedTools stays (a restriction cannot be re-imposed from inside the session it bounds — ADR-155 section 1 binds it at spawn by type), model and color stay (the host has already chosen), and the resolved skills list LEAVES: it is the only entry that is not a field of the role but a projection over other items scopes edges, so it drifts on edits the pointer never names — the ADR-422 fan-out — and a preload supplies rather than restricts, so a fetch substitutes.
  - Committed: per-artifact, not per-directory, because .claude/ was never one thing — settings.json is user-owned merged config and stays tracked. The generated pointers follow the mode switch .squads.toml already carries: offline they may stay committed (consistent BY COMMIT, since items and pointers travel in one repo), remote they are not, because no commit could fix a snapshot of state the repo does not contain. What tells a user which state they are in already ships — sq check backend_reconciled missing-file finding — but managed_paths declares only CLAUDE.md and settings.json today, so a clone with no .claude/agents at all passes clean. That gap has to close or the ruling has no teeth.
  - Drift: sq check, by comparison against a fresh render, not by a stamp. A stamp answers how old, not whether it is wrong, and ADR-85 stamp exists because an override is USER-owned and cannot be re-derived; a pointer is tool-owned, so comparison is available and strictly better. The seam already names the gap — managed_paths docstring says present-only, not a currency check. Error for a drifted restriction (stale spawn authority is a live ADR-155 regression), warn for everything else. And it does not breach the never-read-back guard: that forbids a backend recovering a DECLARATION from output; here output is the subject under test and every declaration still comes from the item.
  - Two deferrals I will not guess at, both named in the body: how a remote clone acquires pointers before anyone runs a command, and whether a remote squad pointers can be compared without connectivity. Also flagging one asymmetry I chose to state rather than smooth over — AGENTS.md keeps its roster prose, because clause 2 asks whether a fetch can substitute and for a host that only reads files it cannot. That exemption is a property of the reader, not a precedent. @op-pierre left Proposed.
- [2026-08-22T10:05:20Z] Pierre Chat:
  - Two corrections to this decision. First, more backends are coming - codex, copilot and cursor pointer files are all planned - so the rule has to be about what a given host tool can express and consume, not about what Claude Code happens to do. Second, the resolved skills list is not agent convenience: it is a useful setting for the third-party agent tool the operator is using. It may well be a second source of truth, and it is still the setting that makes the tool preload the right things.
- [2026-08-22T10:07:21Z] Pierre Chat:
  - Pointer files must be committed, in every mode. Whether to ignore them is the adopter repo decision, not ours, and I want them committed for easier setup and onboarding: a clone should work without anyone running a command first. This overrules the not-committed-under-remote-mode half of this decision.
- [2026-08-22T10:07:23Z] Catherine Manager:
  - Supporting precedent for the principle, read: ensure_root_tmp_ignored (_services/_maintenance.py:68) appends only a temp-file pattern to a root gitignore and its docstring says explicitly that it does so without touching any of its other adopter-owned content. So the tool already ignores its own crash detritus and never the adopters content decisions. Committing generated pointers is the same line drawn on the other side of it.
- [2026-08-22T10:13:02Z] Robert Architect:
  - Third amendment, and I read the whole decision back afterwards: every statement on the four contested points now argues one position (committed in every mode; skills list materialised; containment rule universal, all answers per host; presence before currency). The Context still describes committed pointers as a staleness exposure, which is the problem statement rather than a residual position — section 2b accepts that exposure as a cost explicitly.
  - The skills list: your ruling is what my own clause 2 already implied, and I had it on the wrong side. Clause 2 asks whether a fetch can substitute for the EFFECT, not for the information — an agent can read a skill on turn three but cannot make the host preload one, and cannot retroactively have had it on turn one. That is the same shape as model, which I kept for the same reason. No clause changed; a misapplication did. I reworded clause 2 so the word effect is load-bearing and named the error in place, because the next reader will be tempted the same way.
  - What survived of my removal argument, relocated rather than dropped: the fan-out observation is a drift-RISK claim, not a classification claim, so it moved to section 2c where it makes the comparison load-bearing. And I withdrew the ADR-422 citation — that decision refused a persisted fan-out because an on-demand path reached the same reader (sq graph); here no command can put a skill into a turn already begun, so the clause I cited does not govern this case.
  - Committed: reversed to committed in every mode, on your principle rather than convenience — ensure_root_tmp_ignored appends one temp pattern and its docstring commits to not touching adopter-owned content (_services/_maintenance.py:68-84), so squads ignores its own crash detritus and never the adopter tracking decisions. Under the adopter framing the onboarding case is a FIRST-run failure: a roster claiming ten agents and a host finding none. My objection (no commit fixes a wrong pointer for everyone) is recorded as accepted, not refuted, which is what makes detection the only safeguard.
  - Detection redesigned for a reader with no baseline, since sq check only helps someone who runs it. Three surfaces split by cost: the unprompted root-callback notice gains PRESENCE (a stat per live entry — it exists today at _cli/_common.py:1128-1140 but keys only on the recorded squads_version, so a clone missing pointers at the current version is told nothing); sq check carries presence AND currency; sq sync must report what it regenerated, because a silent fix tells the operator neither that there was a fault nor that a commit is owed. Presence and currency are two findings over ONE widening, presence first — comparing against an absent file has nothing to compare. BUG-784 is the presence half, linked.
  - Per-host: the ABC asks five questions phrased so an author who has read only their host docs can answer them, question 1 being whether an agent under that host can execute a command at all. That question is what fixes my AGENTS.md asymmetry — I had framed it as capability squads does not know, which under your framing is not a gap to work around but the normal condition for every adopter backend. Now the backend author declares it and the compiled document keeps its prose because its backend answers no, same rule different answer. Irreducible set is per-backend; name/description are Claude Code answers and the least representative example available.
  - One deferral left, narrower: whether a remote squad currency check runs off a cache, needs connectivity, or degrades to cannot-verify. Presence is answerable offline in every mode, so every mode keeps a floor. The bootstrap deferral is closed by the ruling. @op-pierre left Proposed.
<!-- sq:discussion:end -->
