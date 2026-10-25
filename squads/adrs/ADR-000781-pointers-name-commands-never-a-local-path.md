---
id: ADR-781
sequence_id: 781
type: decision
title: Pointers name commands, never a local path
status: Accepted
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
updated_at: '2026-10-25T21:49:21Z'
---
<!-- sq:body -->
## Context

A generated pointer is squads' projection of one roster entry into an agent host's own
configuration. When this was decided, both `.claude/` pointers instructed the agent with a **local
file path** (`@{{ squad_path }}`), resolved by the host's own file loader, and the `agents_md`
entry templates displayed the same path as `**Squad file:**`.

That instruction is unsatisfiable when the CLI is a client to a squads server (FEAT-33, EPIC-29):
there is no local squad directory for the path to name, so the pointer's one load-bearing line
resolves to nothing and the agent starts with an identity and no definition.

**And the path is only the visible half.** A pointer's *contents* are a copy of squad state, and
`.claude/` is committed, so under remote mode a pointer is a tracked snapshot of state the
repository does not hold, silently wrong from the moment the server moves. §2a rules on contents
for that reason.

**Who this is decided for.** squads is a tool other teams adopt; this repository's own use of it
only tests that it works. The case that governs is an adopter cloning a project they did not set up,
with their own overrides and their own agent host. An adopter's *first* run is the one that must
work, and an adopter has no baseline for what a correct pointer looks like, so anything wrong reads
to them as squads being broken. Third-party hosts (Codex, Copilot, Cursor) are the main case for the
same reason (§2d).

## Decision

### 1. No materialised file squads generates may carry a local file path

The rule is about the *path*, not the `@` sigil: a displayed path is unusable for the same reason an
instructed one is unresolvable. No pointer or entry template receives a `squad_path`.

The rule governs files squads writes **into another tool's configuration**. It does not govern
`sq`'s own output, which may name a path freely because the caller has a working `sq` by
construction, nor a path an adopter writes in their own prose.

### 2. A pointer names the command, and carries enough that a first turn needs no other fetch

An agent pointer carries three things, in this order of priority when space is contested (the
order of what a pointer keeps, not the order an agent runs them: the definition fetch runs first,
then the startup set):

1. **Identity**: full name, pronouns, slug, role title.
2. **The slug-bound startup command set**, with the slug already substituted: `sq memory <slug>
   list`, `sq memory <slug> show <slug>`, `sq board list`, `sq mine <slug>`, `sq inbox <slug>`.
3. **One command that renders the full definition**: `sq role <slug> show` for an agent pointer,
   `sq skill <slug> show` for a skill pointer.

It **names** the definition command rather than embedding the definition. Embedding would make a
first turn self-sufficient offline, and would be a second stored copy of the definition, in a file
the backend regenerates and squads is not the only writer of, going stale between syncs. Naming
costs one command on the first turn and is correct in both modes. What it loses is the offline case,
and the loss is bounded: an agent whose `sq` cannot reach its squad has its identity and its startup
commands and not its mission, which is the right failure, because every one of those startup
commands would fail too.

Substituting the slug in the pointer removes a step an agent would otherwise perform by
reconstruction, which is the same failure class as acting on a summary instead of a literal
command.

### 2a. What a pointer may contain: the containment rule

The host-reads-files argument establishes that a pointer **file** must exist: a host enumerates
files to discover that an agent exists at all, and cannot run a command to find out. It establishes
nothing about the file's contents. A pointer materialises a value only when both hold:

1. **the host consumes it at or before spawn**, and
2. **a runtime fetch cannot substitute for its *effect***: true exactly when the value *restricts*
   or *configures* the session, false when it merely *supplies* content the agent could obtain for
   itself.

The test is never "can the agent get this information" but "can the agent obtain what setting this
value did". A restriction cannot be re-imposed from inside the session it was meant to bound; a
configuration has already taken hold before the agent's first turn; only plain content can be
fetched later.

Applied to the Claude Code agent pointer:

| Value | Host status | If it goes stale | Ruling |
| --- | --- | --- | --- |
| `name` (the slug) | required: the dispatch identifier | cannot drift: slugs are permanent (ADR-979) | materialised |
| `description` | required: the host's own selection text, read before any agent exists | a routing hint is stale; the agent still spawns and behaves correctly | materialised |
| `disallowedTools` | the capability boundary, bound to the agent type at spawn (ADR-155 §1) | a leaf keeps spawn authority the squad revoked: a capability escalation | materialised, and the one field whose drift is an error (§2c) |
| `model` | optional; omitting the key silently runs the agent on the session default | the agent runs on the wrong model, silently | materialised: the host has chosen a model before the agent can speak |
| `color` | optional, cosmetic | cosmetic | materialised, not load-bearing |
| the resolved `skills` list | the preload setting: what is in context on turn one | a withdrawn skill is preloaded, or a newly scoped one is missing | materialised: an agent can read a skill on turn three, but cannot make the host preload one or retroactively have had it on turn one |
| the definition (mission, responsibilities, agreements) | none; squads' own text | the agent acts on text the squad no longer holds | **not materialised**: fetched with `sq role <slug> show` |

The skills list is the one entry that is not a field of the role but a *resolved projection over
other items' edges* (system membership plus every skill carrying a preload edge to this role,
recovered by inversion), so it drifts on edits to items the pointer never names. That is a claim
about **drift risk**, not about classification: clause 2 decides whether a value is materialised,
and the fan-out decides how much the drift check matters (§2c). ADR-422, which refused to persist a
fan-out projection because an on-demand path reached the same reader, does not govern this case: no
command an agent runs can put a skill into a turn that has already begun.

**Skill pointers take the same rule.** A skill pointer's `name` and `description` are
host-consumed before anything can run, and so is `user-invocable: false` when the skill is not
operator-invocable (ADR-983). Its body names `sq skill <slug> show`. Nothing else is in it.

### 2b. The generated pointers are committed, in every mode

`.claude/` is not one kind of thing, so the question is asked per artifact. `settings.json` is
**user-owned, merged** config: the backend preserves whatever is there and only adds missing
permission rules. The pointers are pure projections, regenerated wholesale, and for them the answer
is the same in every mode: **committed.**

**Whether to ignore a generated file is the adopter's repository decision, never squads'.**
`ensure_root_tmp_ignored` appends exactly one temp-file pattern to a root `.gitignore` without
touching any of its other, adopter-owned content: squads ignores its own crash detritus and nothing
else. An adopter who gitignores `.claude/` is making a supported choice.

**The onboarding case is a first-run failure, not an edge case.** An adopter clones a project, opens
their agent host, and expects the agents the roster advertises to be there. Committed pointers mean
the clone has them, with no command run first.

**Accepted as a cost, not answered:** under remote mode a committed pointer can be a snapshot of
state the repository does not contain, and no commit fixes it for everyone. Committed and possibly
stale is the sanctioned state, and **detection is the remaining safeguard** (§2c).

### 2c. Detection: `sq check` compares, `sq sync` reports, and neither stamps

The per-entry artifacts are **declared paths**: `AgentBackend.managed_entry_paths` returns one path
per role or skill that is *currently live*, scoped by the same predicate that decides who gets an
artifact at all (`is_live_roster_entry`), never by a fixed or historical slug list, so a
retire/reactivate cycle never produces a false positive on either side. Two findings sit on that
one widening, and presence comes first, because a content comparison against an absent file has
nothing to compare:

- **Presence**: does the declared path exist. `sq check`'s `backend_reconciled` reports a missing
  per-entry pointer at **warn**, and a missing top-level managed file (`managed_paths`, the compiled
  `CLAUDE.md`/`AGENTS.md` and the like) at **error**.
- **Currency**: does the file's content match a fresh render. `sq check` compares each pointer on
  disk with the backend's pure render of it (§2d question 5). A drifted **restriction** is an
  **error**: a stale pointer still granting a leaf the spawn tool the squad revoked is a live
  regression against ADR-155's threat model, not repairable from inside the session it governs.
  Every other drift is a **warn**: `sq sync` fixes it and nothing unsafe happens meanwhile.

**`sq sync` is the fix, and it says what it changed**: it reports every per-entry pointer it had to
regenerate because it was missing, so the operator learns both that there was a fault and that a
commit is owed. The operator's recourse is plain: run `sq sync`, then commit what it rewrote.

There is **no unprompted per-command notice** (op-pierre, 2026-10-25). Presence and currency are
reported by `sq check`, the command a squad runs to ask whether it is healthy, and by `sq sync`'s
report; an advisory on every command would be noise in a repository where `sq check` is the gate.

**By comparison, not by a stamp.** ADR-85's `override-base` stamp exists because an override is
user-owned: a human authored the body, so squads cannot re-derive it and a version is the only
provenance available. A pointer is tool-owned and re-renderable, so comparison answers the question
that matters ("is this wrong") instead of "how old is this", and never flags a correct pointer for
predating a release that changed nothing about it.

**This does not breach the never-read-back rule.** That guard forbids a backend *recovering a
declaration* from its own output. A drift check reads output as the **subject under test**: every
declaration comes from the item, the render is the expectation, and the checker reads the path the
backend declares, so it never reaches into a host's directory on its own (invariant 6).

**Remote mode.** Presence is a filesystem question, answerable offline in every mode. Currency
compares against squad state, so under remote mode it needs the server's; whether that check runs
against a cache, requires connectivity, or degrades to "cannot verify" is remote mode's design
(FEAT-33, EPIC-29). Presence gives every mode an offline floor.

### 2d. The rule is universal; every answer is per host

Codex, Copilot and Cursor backends are planned, and their users are adopters by definition, so the
per-host contract is what most users meet first, and Claude Code, the host this decision was derived
from, is the least representative example. The frame generalises `_VALID_MODELS`, documented as "a
backend-local set, not a shared one", and `model_drop_warning`, which reports a value that survives
storage and fails to render rather than validating it twice.

**Universal: the containment rule.** Both clauses are stated about a host and its configuration, not
about a format. **Per backend: every answer, the irreducible set included.** `name` and
`description` are Claude Code's irreducible set; another host may key an entry by filename, or do no
host-side selection.

**The backend answers five questions**, each phrased so an author who has read only their host's
documentation can answer it:

1. **Can an agent running under this host execute a command?** The question clause 2 turns on. A
   host that cannot run commands can never satisfy "a fetch substitutes", so for it the rule keeps
   everything it can express.
2. **Which of the values squads projects does this host's configuration have a place for?** The
   expressible set. Anything squads declares and this host cannot express is **reported once, at
   write time, and dropped, never silently**, on `model_drop_warning`'s precedent.
3. **Which of those must be present for this host to find and dispatch an entry at all?** The
   irreducible set.
4. **Which of those constrain what the session may do, rather than configure how it runs?** The
   capability boundary, however the host spells it (`restriction_fragment`). §2c's error severity
   is defined over this answer.
5. **What would you write for this entry, without writing it?** The pure render §2c compares
   against (`render_role_entry`, `render_skill_entry`).

A backend may be unable to honour a constraint squads declares, and that is reportable rather than
forbidden: a host with no way to deny a tool gets a warning that it cannot express the boundary, not
a refusal to support the host and not silence. The documented `AgentBackend` surface stays at seven
abstract methods; the per-entry methods are non-abstract with a default that expresses nothing, so a
third-party backend written against the seven is unaffected. This extends ADR-133's
de-Claude-ification from names and path ownership to **contents**. A future backend's configuration
format, vocabulary and answers are its own decision; no backend has to reopen the rule to give them.

### 3. Where the protocol lives

- **The agent pointer** carries the **slug-bound commands**, rendered from one declared list in
  code (`_STARTUP_COMMAND_TEMPLATES` in the Claude Code backend); a command added there appears on
  every generated agent pointer.
- **The `CLAUDE.md` / `AGENTS.md` managed region** keeps the **protocol and its rationale**, stated
  once for every agent with a `<role>` placeholder: why both queue surfaces are read and neither
  subsumes the other, what memory is versus what the board is.
- **The role definition carries no copy** of the slug-bound set: two slug-bound copies of one
  command set, in two files with two regenerators, is the duplication this clause prevents.

### 4. Invariant 5 states the containment rule

> **`.claude/` files are pointers**, not content. A pointer carries only what the host must read
> before an agent can run — its identity, the text the host selects it by, and the constraints
> squads imposes on the session — plus the commands that fetch the rest. Anything `sq` can answer,
> a pointer does not hold.

It forbids carrying a value the agent could ask for, and it locates nothing by directory, the
assumption remote mode breaks.

### 5. The two backends that exist, as worked answers to §2d

- **`_claude_code`** answers "yes" to question 1: its agents run `sq`, which is what §2 is built on.
  Its pointer frontmatter is the host-consumed set (`name`, `description`, `model`, `color`, the
  `disallowedTools` attenuation, the resolved `skills` preload; for a skill, `user-invocable`), and
  the definition is fetched.
- **`_agents_md`** answers question 1 with "not knowably": it compiles a single `AGENTS.md` for tools
  whose command-execution capability is declared by whoever builds the backend, not by squads. It
  takes the generic protocol form from the managed region and writes no per-entry file. Its roster
  prose (full name, slug, title, mission, responsibilities) stays in the compiled document, derived
  rather than exempted: clause 2 asks whether a runtime fetch can substitute, and a host that cannot
  run a command has none. A compiled document is not a privileged class; a future backend whose host
  can run commands answers "yes" and inherits the containment rule in full. The cost is named:
  materialised state that drifts, covered by §2c because the compiled documents are declared paths.

Neither backend reads back its own output, and neither may start
(`tests/meta/test_a_backend_never_reads_back_its_own_generated_output.py`).

### 6. The release ordering, stated once for every template-touching change

A bundled-template edit forces a template-manifest regeneration, and the generator replaces the
running version's index entry **wholesale**, keyed on `[project].version` (ADR-777). Regenerating
before the version bump overwrites the shipped release's recorded hashes and corrupts the provenance
`sq override diff` reads. **The bump comes first, then the regeneration.** This is the single
statement of that ordering for every change that touches bundled templates; the managed-section
golden and the generated-agent-text guards move with the templates in the same change.

A migration runner that rewrites a pointer emits today's pointer, not a historical one: a pointer is
regenerated, never migrated, so a runner is never "fixed" by pinning a copy of a template inside it.

## Consequences

- **A first turn costs one command per agent**, and every instruction a pointer carries resolves in
  every mode.
- **`sq role <slug> show` is an agent's primary definition read.** It renders the definition from
  the resolved `RoleDef` on every call, through the same template a role body renders through, so its
  two halves cannot disagree. The card keeps only the resolution facts the definition prose does not
  carry (role title, origin, model, colour, spawn authority, capabilities, the create lane, the
  resolved skills list), and the prose prints mission and responsibilities once.
- **The pointer is not readable as a standalone document.** A person opening
  `.claude/agents/architect.md` runs a command to see the definition. That is the intended trade.
- **The resolved skills list stays in the agent pointer**: it is the setting that makes the host
  preload the right things.
- **The generated pointers are committed in every mode**; `settings.json` is user-owned and committed
  for a different reason.
- **Committed and possibly stale is accepted as a cost.** `sq check` and `sq sync`'s report are the
  safeguard, and an adopter who never runs either sees a stale pointer until they do.
- **Item markdown is not this decision's subject**: what role and skill bodies contain is ADR-776's
  and ADR-880's. The generated files squads writes into another tool's configuration stay
  materialised, because their reader configures an entry by reading a file before any agent exists to
  run a command; role and skill bodies go the other way only because this decision put `sq` in their
  delivery path. The one thing separating them is which reader can run a command.
- **One deferral remains**: how a remote squad's currency check reaches squad state (§2c).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T09:48:02Z] `architect` Robert Architect:
  - Authored separately from ADR-776 rather than folded into it: this is a backend-projection question governed by the AgentBackend ABC (ADR-75/133/141/697) and bound by remote mode (FEAT-33), not a derived-view question — and separating them lets the collapse be ruled on without also ruling on pointer copy.
  - The exposure is four templates, not two. The @ form is only in pointer_agent.md.j2:25 and pointer_skill.md.j2:8, but the agents_md backend carries the same local path as **Squad file:** in role_entry.md.j2:11 and skill_entry.md.j2:5 — same squad_path context value, weaker failure (a useless line rather than a missing definition), same class. Seven producer sites feed those four templates and none survives.
  - The replacement needs less new material than it looks: the slug-bound startup command set already exists at role.md.j2:30-36 and only reaches the agent THROUGH the @ reference being removed, while CLAUDE.md managed region already states the same protocol generically at claude_section.md.j2:53-61. So the duplication already ships; the decision relocates the slug-bound copy into the pointer, keeps the rationale in the managed region, and requires both to render from one declared list in code.
  - Two things for @op-pierre before he rules. Naming the command rather than embedding the definition loses the offline case, bounded: an agent whose sq cannot reach its squad has identity and commands but not its mission — which is the right failure, since every startup command would fail too. And sq role <slug> show already prints mission and responsibilities TWICE (driven — computed card plus stored body), which stops being cosmetic once that command is an agent primary read, because the card resolves a project override and the body carries the last sync. Section 5 and the consequences name it; settling it is this decision to own.
- [2026-08-22T09:52:07Z] `op-pierre` Pierre Chat:
  - Challenge to the reasoning that backend pointers must stay materialized: they will fail under remote mode too. The host-reads-files argument settles that a pointer file must exist, not that its contents may be a copy of squad state.
- [2026-08-22T09:52:09Z] `manager` Catherine Manager:
  - Facts behind the challenge, driven: .claude/ is committed to git (git ls-files lists every pointer; only settings.local.json is ignored), and each generated pointer materializes seven fields of role state - slug, description, model, color, spawn authority, the resolved skills list, and the full name in its body. So under remote mode a pointer is a committed snapshot of server-side state: a role changed on the server leaves every clone wrong until someone runs sq sync locally and commits the result, with nothing reporting the drift.
- [2026-08-22T10:00:21Z] `architect` Robert Architect:
  - Amended in place rather than annotated: the challenge is correct and it lands on reasoning the body relied on, so leaving it would have left the decision defending a rule it no longer holds. Added sections 2a (containment), 2b (committed or not), 2c (drift reporting), and reworded section 4 and section 5 around them. Also narrowed ADR-776 does-not-abolish paragraph, which read as a blanket licence for pointer contents when it only ever settled which decision governs them.
  - Irreducible: name and description, and nothing else. name is the dispatch identifier and CANNOT drift — slugs are frozen non-renamable by ADR-85 section 4. description is the host own selection text, read before any agent exists to run a command, and its drift mis-routes without making anything wrong once spawned. That is two of the seven fields.
  - The rule above the minimum: materialise only when the host consumes the value at spawn AND a runtime fetch cannot substitute — which is true when the value RESTRICTS or CONFIGURES and false when it merely SUPPLIES. So disallowedTools stays (a restriction cannot be re-imposed from inside the session it bounds — ADR-155 section 1 binds it at spawn by type), model and color stay (the host has already chosen), and the resolved skills list LEAVES: it is the only entry that is not a field of the role but a projection over other items scopes edges, so it drifts on edits the pointer never names — the ADR-422 fan-out — and a preload supplies rather than restricts, so a fetch substitutes.
  - Committed: per-artifact, not per-directory, because .claude/ was never one thing — settings.json is user-owned merged config and stays tracked. The generated pointers follow the mode switch .squads.toml already carries: offline they may stay committed (consistent BY COMMIT, since items and pointers travel in one repo), remote they are not, because no commit could fix a snapshot of state the repo does not contain. What tells a user which state they are in already ships — sq check backend_reconciled missing-file finding — but managed_paths declares only CLAUDE.md and settings.json today, so a clone with no .claude/agents at all passes clean. That gap has to close or the ruling has no teeth.
  - Drift: sq check, by comparison against a fresh render, not by a stamp. A stamp answers how old, not whether it is wrong, and ADR-85 stamp exists because an override is USER-owned and cannot be re-derived; a pointer is tool-owned, so comparison is available and strictly better. The seam already names the gap — managed_paths docstring says present-only, not a currency check. Error for a drifted restriction (stale spawn authority is a live ADR-155 regression), warn for everything else. And it does not breach the never-read-back guard: that forbids a backend recovering a DECLARATION from output; here output is the subject under test and every declaration still comes from the item.
  - Two deferrals I will not guess at, both named in the body: how a remote clone acquires pointers before anyone runs a command, and whether a remote squad pointers can be compared without connectivity. Also flagging one asymmetry I chose to state rather than smooth over — AGENTS.md keeps its roster prose, because clause 2 asks whether a fetch can substitute and for a host that only reads files it cannot. That exemption is a property of the reader, not a precedent. @op-pierre left Proposed.
- [2026-08-22T10:05:20Z] `op-pierre` Pierre Chat:
  - Two corrections to this decision. First, more backends are coming - codex, copilot and cursor pointer files are all planned - so the rule has to be about what a given host tool can express and consume, not about what Claude Code happens to do. Second, the resolved skills list is not agent convenience: it is a useful setting for the third-party agent tool the operator is using. It may well be a second source of truth, and it is still the setting that makes the tool preload the right things.
- [2026-08-22T10:07:21Z] `op-pierre` Pierre Chat:
  - Pointer files must be committed, in every mode. Whether to ignore them is the adopter repo decision, not ours, and I want them committed for easier setup and onboarding: a clone should work without anyone running a command first. This overrules the not-committed-under-remote-mode half of this decision.
- [2026-08-22T10:07:23Z] `manager` Catherine Manager:
  - Supporting precedent for the principle, read: ensure_root_tmp_ignored (_services/_maintenance.py:68) appends only a temp-file pattern to a root gitignore and its docstring says explicitly that it does so without touching any of its other adopter-owned content. So the tool already ignores its own crash detritus and never the adopters content decisions. Committing generated pointers is the same line drawn on the other side of it.
- [2026-08-22T10:13:02Z] `architect` Robert Architect:
  - Third amendment, and I read the whole decision back afterwards: every statement on the four contested points now argues one position (committed in every mode; skills list materialised; containment rule universal, all answers per host; presence before currency). The Context still describes committed pointers as a staleness exposure, which is the problem statement rather than a residual position — section 2b accepts that exposure as a cost explicitly.
  - The skills list: your ruling is what my own clause 2 already implied, and I had it on the wrong side. Clause 2 asks whether a fetch can substitute for the EFFECT, not for the information — an agent can read a skill on turn three but cannot make the host preload one, and cannot retroactively have had it on turn one. That is the same shape as model, which I kept for the same reason. No clause changed; a misapplication did. I reworded clause 2 so the word effect is load-bearing and named the error in place, because the next reader will be tempted the same way.
  - What survived of my removal argument, relocated rather than dropped: the fan-out observation is a drift-RISK claim, not a classification claim, so it moved to section 2c where it makes the comparison load-bearing. And I withdrew the ADR-422 citation — that decision refused a persisted fan-out because an on-demand path reached the same reader (sq graph); here no command can put a skill into a turn already begun, so the clause I cited does not govern this case.
  - Committed: reversed to committed in every mode, on your principle rather than convenience — ensure_root_tmp_ignored appends one temp pattern and its docstring commits to not touching adopter-owned content (_services/_maintenance.py:68-84), so squads ignores its own crash detritus and never the adopter tracking decisions. Under the adopter framing the onboarding case is a FIRST-run failure: a roster claiming ten agents and a host finding none. My objection (no commit fixes a wrong pointer for everyone) is recorded as accepted, not refuted, which is what makes detection the only safeguard.
  - Detection redesigned for a reader with no baseline, since sq check only helps someone who runs it. Three surfaces split by cost: the unprompted root-callback notice gains PRESENCE (a stat per live entry — it exists today at _cli/_common.py:1128-1140 but keys only on the recorded squads_version, so a clone missing pointers at the current version is told nothing); sq check carries presence AND currency; sq sync must report what it regenerated, because a silent fix tells the operator neither that there was a fault nor that a commit is owed. Presence and currency are two findings over ONE widening, presence first — comparing against an absent file has nothing to compare. BUG-784 is the presence half, linked.
  - Per-host: the ABC asks five questions phrased so an author who has read only their host docs can answer them, question 1 being whether an agent under that host can execute a command at all. That question is what fixes my AGENTS.md asymmetry — I had framed it as capability squads does not know, which under your framing is not a gap to work around but the normal condition for every adopter backend. Now the backend author declares it and the compiled document keeps its prose because its backend answers no, same rule different answer. Irreducible set is per-backend; name/description are Claude Code answers and the least representative example available.
  - One deferral left, narrower: whether a remote squad currency check runs off a cache, needs connectivity, or degrades to cannot-verify. Presence is answerable offline in every mode, so every mode keeps a floor. The bootstrap deferral is closed by the ruling. @op-pierre left Proposed.
- [2026-08-26T11:12:29Z] `op-pierre` Pierre Chat:
  - Section 2 priority list is about what a pointer keeps when space is contested, not the order an agent runs the commands in. The definition fetch runs first; the startup set follows.
- [2026-09-01T08:00:04Z] `op-pierre` Pierre Chat:
  - Same direction applies to the role body: the markdown is storage, the CLI is the only read surface, and duplicated data comes out of the file rather than being kept in sync.
- [2026-09-01T08:13:56Z] `architect` Robert Architect:
  - Amended in place (2026-09-01 note): the double-print is settled by removal, so the open Consequence closes.
    - Driven on this decision's own surface: one `sq role architect show` printed a catalog-override mission in the card and the pre-override text in the body beneath it, same output, `sq check` exit 0, nothing marking which half is authoritative — and the stale half is the longer, instruction-shaped one the agent then acts on.
    - Ruled: the stored copy goes (ADR-776's amendment owns the mirror), `show` renders the definition from the resolved RoleDef on every call, and the card then DROPS mission and responsibilities and keeps only the resolution facts the prose does not carry (title, model, spawn authority, create lane, resolved skills). Both halves come from one `resolve_role_with_base` on one call, so they cannot disagree. Option one, now safe — it was unsafe before only because dropping the card rows would have left the stored copy as the sole answer.
    - §4's boundary restated in the amendment rather than left to inference: the backend pointers and the compiled CLAUDE.md/AGENTS.md managed regions STAY materialised. Their reader configures an entry by reading a file before any agent exists to run a command. Role and skill bodies go the other way only because this decision put `sq` in their delivery path. The two sit next to each other and the only thing separating them is which reader can run a command — which is exactly what a hurried change collapses.
- [2026-10-25T21:42:42Z] `architect` Robert Architect:
  - 2026-10-25 audit: not rewritten; a code gap blocks it. Section 2c rules an unprompted root-callback presence notice for missing per-entry pointers; it was never built (version_notice keyed only on squads_version) and ADR-1119 removed that notice. sq check presence/currency and the sq sync regeneration report are built. Other stale passages (version_notice, the agents_md entry templates deleted by ADR-777 B3, section 6 version facts, the 2026-09-01 amendment) wait on the call. @manager for op-pierre: build the notice, or narrow 2c.
- [2026-10-25T21:47:48Z] `op-pierre` Pierre Chat:
  - Narrow 2c to the sq check presence/currency checks and the sq sync regeneration report; drop the unprompted per-command notice.
- [2026-10-25T21:49:21Z] `architect` Robert Architect:
  - 2026-10-25: body rewritten in present tense per the op-pierre ruling aa03f96. Section 2c narrowed to sq check presence/currency and the sq sync regeneration report, with no per-command notice; the 2026-09-01 amendment folded (show renders the resolved definition, the card drops mission and responsibilities); the deleted agents_md entry templates, squad_path producers, version_notice and the 0.13.0 version facts removed; the skill pointer user-invocable key (ADR-983) added. Decision otherwise unchanged.
<!-- sq:discussion:end -->
