---
id: REV-926
sequence_id: 926
type: review
title: Role, system-skill and per-type-skill text collapsed onto the view tag
status: Approved
author: reviewer
refs:
- FEAT-906:addresses
- ADR-880
subentities:
- local_id: F1
  title: Upgrading to 0.15 empties every role and skill definition, silently
  status: Verified
  severity: high
- local_id: F2
  title: squads and sq-memory skill text now embeds an absolute path
  status: Verified
  severity: high
- local_id: F3
  title: linearize_lifecycle global to filter breaks an adopter template override
  status: Verified
  severity: medium
- local_id: F4
  title: sq repair aborts with a raw AssertionError traceback, not a SquadsError
  status: Verified
  severity: medium
- local_id: F5
  title: The repair classifier seeds role and system-skill tags without checking the
    spec declares them
  status: Verified
  severity: medium
- local_id: F6
  title: A declared type whose skill slug is already authored loses its guidance silently
  status: Verified
  severity: medium
- local_id: F7
  title: The role view name is a bare literal in three writers
  status: Verified
  severity: low
- local_id: F8
  title: Two narration instances survived both sweeps, one of them false
  status: Verified
  severity: low
- local_id: F9
  title: sq role show lost its unresolvable-role advisory
  status: Verified
  severity: low
- local_id: F10
  title: sq repair reorders the index, so the backfill is a 38k-line diff
  status: WontFix
  severity: low
- local_id: F11
  title: squad_dir display derives the folder name, so a nested squad_dir still diverges
  status: Verified
  severity: medium
- local_id: F12
  title: The role creation path still seeds a tag for an undeclared view
  status: Verified
  severity: medium
- local_id: F13
  title: A skipped convergence is never retried and leaves sq check clean
  status: Verified
  severity: low
- local_id: F14
  title: A non-numeric squads_version makes sq sync raise a bare ValueError
  status: Verified
  severity: low
- local_id: F15
  title: sq migrate up does not report the repair skips it collects
  status: Verified
  severity: low
- local_id: F16
  title: The new empty-body hint names sq sync where a dropped view makes it a no-op
  status: Verified
  severity: low
- local_id: F17
  title: Skill creation seeds a placement tag for an undeclared view
  status: Verified
  severity: medium
- local_id: F18
  title: sq sync reports success and exits 0 on a withheld stamp
  status: Verified
  severity: low
- local_id: F19
  title: The declared-view empty hint still names sq sync where only repair helps
  status: Verified
  severity: low
- local_id: F20
  title: sq migrate up exits 1 on an unreadable file without naming it
  status: Verified
  severity: low
- local_id: F21
  title: The drift trigger orders a prerelease above its own release
  status: Verified
  severity: low
- local_id: F22
  title: chlog drops a migration's manual steps on a prerelease bound
  status: WontFix
  severity: medium
- local_id: F23
  title: sq adopt reports neither repair channel and exits 0
  status: Verified
  severity: medium
- local_id: F24
  title: A duplicated version_tuple feeds chlog, not only the notice
  status: WontFix
  severity: low
- local_id: F25
  title: The view-tag enumeration is narrower than its completeness claim
  status: Verified
  severity: low
- local_id: F26
  title: A gated site's behavioural-test citation can resolve while proving nothing
  status: Verified
  severity: low
created_at: '2026-09-04T14:27:05Z'
updated_at: '2026-09-10T09:33:33Z'
---
<!-- sq:body -->
## Scope

One batch review across both of FEAT-906's tasks, read as a single change:
`git diff 5576511e..e40592e3 -- src/ tests/`, with the concurrent validator work
(`1b8a6974`, `110b845d`) excluded as another feature's change. Reviewed against ADR-880's
ruling and its three amendments, and against each task's own acceptance list.

The three claimed collapses are real. A role's body carries `sq:view:role_definition`, the three
system skills carry their own tags, the per-item-type skill resolves through a corrected
`playbook` subject, and `role_definition_text` / `skill_definition_text` /
`_item_skill_definition_text` / `_cli/_skill.py`'s `if system:` branch are all gone. Every read
surface funnels through `ItemsMixin.read_body`; none of the three has a bespoke render path left
behind a tag-shaped facade. Verified independently rather than accepted: two `git worktree`
builds at `5576511e` and `e40592e3`, same roster, same synthetic `incident` type override, gave
byte-identical `.claude/` (`diff -rq` silent), byte-identical `CLAUDE.md`, byte-identical
`AGENTS.md` under the `agents_md` backend, byte-identical `sq role/skill show --json`, and
22 differing item files whose whole diff is the timestamp pair plus one seeded tag line.

What the equivalence proof missed is where the findings are. Two of the 22 rendered definitions
were **not** equivalent (F2), and the population the backfill was designed for is the one
population nothing invokes the backfill for (F1).

## Method

Claims below are labelled **read** (traced in source), **driven** (executed) or **inferred**.
Falsification was run in a third worktree at `e40592e3`, never in the live tree. Every
disproving search was validated against a known positive before being trusted.

## What was checked and found sound

- **The data-loss guard holds.** Reverting `_converge_body_tag`'s `strict_empty` early return
  reddens three tests, including the end-to-end
  `test_declaring_an_item_type_does_not_delete_an_authored_skill_of_that_name` with a real
  destructive diff. Restored, green. **Driven.**
- **The slug-collision gate is load-bearing.** Reverting the `item.type != ROSTER_SKILL` guard
  makes a TASK item slugged `sq-bug` resolve the `bug` lane; the permanent test catches exactly
  that (`assert 'bug' == 'task'`). **Driven.**
- **The custom-type path generalises.** A synthetic `incident` type gets `sq-incident` from the
  same writer, the same tag, the same template, thin because it has no lane — and its rendered
  text is byte-identical to what the deleted bespoke path produced. `sq workflow view item_skill
  SKILL-19 --json` resolves subject `task`. This is the axis the third amendment turns on, and it
  is proven on the adopter side, not only the bundled side. **Driven.**
- **The four filters are pure** functions of the spec/playbook/roster with no query logic in the
  template; `item_skill.md.j2` calls them and derives nothing itself. **Read.**
- **The shipped `v0.14.0` template-manifest entry is intact** against the tag — the release
  gotcha was handled, not tripped. **Driven.**
- **Live corpus backfill: nothing else moved.** The 22 item files are one inserted line each,
  zero deletions. `.squads.json`'s 38k-line churn is semantically only `squads_version`
  0.14.0 -> 0.15.0 plus two tasks' own subtask statuses; item count, ids and every other field
  are identical. **Driven** (parsed both revisions and compared field by field). The churn itself
  is F10.
- **Layering, conventions:** no `_services` -> `_rendering` edge introduced, `_views` ->
  `_interactions` is downward, no bare non-PEP-695 type alias, no ticket ID in any source or test
  filename or docstring of this feature's diff (the three ticket-shaped hits in the tree are
  TASK-924's file). **Read**, greps validated on known positives.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 926 add-finding "…" --severity medium`; track with `sq review 926 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Upgrading to 0.15 empties every role and skill definition, silently

<!-- sq:finding:F1:body -->
**Driven, on a real corpus.** An adopter at squads 0.14.x who installs 0.15.0 loses every role
definition and every skill definition from `sq role/skill show`, and nothing in the product tells
them so or tells them how to get it back.

Reproduction (the exact sequence run, twice, in throwaway squads):

1. Build a squad on `5576511e` (`sq init --roles all`, `sq dev add --tech python`, `sq sync`) —
   the shape any 0.14 adopter has: role and system-skill `sq:body` regions present and empty,
   because that release rendered the definition on read from a hardcoded branch.
2. Point the 0.15.0 build at it. `sq role manager show` prints
   `(empty — set it with `body`)`. `sq skill squads show` and `sq skill sq-task show` print
   `(no definition — the item type this skill described is no longer declared; restore the type,
   or retire this skill)`.
3. `sq check` -> `✓ no issues`.
4. The version-drift notice on every command says `Run `sq sync` to refresh them`.
   `sq sync` -> `synced managed files to this squads version`. `sq role manager show` still empty:
   `_write_managed_skill` leaves an existing `sq:body` region byte-untouched by design, and
   nothing rewrites a role file on sync.
5. `sq migrate up` -> `already at schema v0.14; nothing to migrate`. The schema did not change in
   0.15, so there is no runner to ride.
6. `sq repair` -> `stripped retired regions from 22 item files`. Everything renders again.

`sq repair` is the only recovery, and it is the one command nothing points the user at. The
blast radius is not cosmetic: `.claude/agents/<slug>.md` and `.claude/skills/<slug>/SKILL.md`
are pointers whose entire content is "load your definition with `sq role <slug> show`", so every
agent in an upgraded squad boots with no role and no skill guidance until somebody guesses
`sq repair`. This is the failure class ADR-880 and this feature exist to eliminate, stated in
TASK-923's own scope: *silently stops rendering with `sq check` clean*.

The gap is structural, not an oversight in the sweep. ADR-880's ruling licensed the retroactivity
as *a migration* ("permitted once under a closed condition set ... report the count"), which the
CLI hard-stops on. The implementation put it in `sq repair` instead, and
`tests/integration/test_migration_corpus.py::test_the_bare_verb_strips_a_corpus_already_at_the_current_stamp`
states the consequence in its own docstring — "the case the migration path structurally cannot
reach, and the whole reason the vehicle is `repair` rather than a runner" — and then proves the
fix works *when `repair` is called*. Nothing makes it get called. That is why the suite is green
at 4889: every corpus fixture below `v0_14` reaches the sweep through `migrate up`'s trailing
repair, and the one fixture at the current stamp is only ever exercised by a test that invokes
`svc.repair()` by hand.

Two secondary defects on the same path, both driven:

- The role's empty hint is `(empty — set it with `body`)`. There is no `body` verb in the
  `sq role` addressing group, and `set_body` refuses a role body unconditionally, so the hint
  names an action that cannot be taken.
- The skill's empty hint blames an undeclared item type. For `squads` and `sq-task` on a squad
  where both are perfectly declared, that diagnosis is simply false; `_cli/_skill.py`'s hint
  branches on `system` alone and cannot tell "no tag seeded" from "type dropped".

Any one of: an advisory in `sq check` when a role or permanently-system skill body carries
neither its tag nor content (a corpus-state finding naming `sq repair`, which is what the
existing view-tag file scan already does for a *dangling* tag); or a schema bump with a runner;
or `sq sync` covering the case its own version notice advertises. The CHANGELOG's 0.15.0 section
also carries no entry for this feature and no upgrade step.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-09-08T13:41:35Z] Paul Reviewer:
  - Verified on the driven upgrade path, not on the handback. A real v0.14.0 build created the
    corpus (`sq init --roles all`, `sq dev add --tech python`, `sq sync` — 9 roles, 12 skills, every
    `sq:body` region present and empty); the 0.15.0 build then read it: every definition empty, `sq
    check` clean. One `sq sync`, no `sq repair` anywhere in the sequence, and all 21 definitions
    render. Second sync writes nothing (drift-gated).
    
    Narrow scoping confirmed by diff rather than by reading the call: 22 files differ after the
    sync — 21 item files with exactly one inserted tag line each (zero deletions, no frontmatter
    timestamp churn) plus `.squads.toml`'s version stamp. **`.squads.json` is byte-identical**, so
    F10 does not arrive on sync. The writer is the atomic `_itemfile.write_text`, same as repair's.
    
    Both secondary hints fixed and driven: role and skill now read "(empty — run `sq sync` to
    populate it)" — no `body` verb that does not exist, no false "type no longer declared".
    Falsified myself: disabling the trigger reddens 2 of the 4 tests in the new sync-backfill file.
    
    Residue filed separately: F13 (a skip stamps the version anyway, so nothing retries and `sq
    check` stays clean), F14 (a non-numeric `squads_version` makes this trigger raise a bare
    `ValueError`), F16 (the new hint names `sq sync` where a dropped view makes it a no-op).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — squads and sq-memory skill text now embeds an absolute path

<!-- sq:finding:F2:body -->
**Driven.** Two of the three system skills' rendered text is not byte-equivalent after the
collapse: `squads` and `sq-memory` now embed the squad's **absolute filesystem path** where they
previously embedded the relative folder name. US5's acceptance ("byte-identical, or any diff is
reviewed and confirmed intentional") is unmet, and TASK-922's handoff mis-diagnoses it as
"a fixture artifact, not a real difference" — the two temp roots differing. They are not: the
shape of the value changed.

On this repo, right now:

    $ uv run sq skill squads show --raw | grep 'indexed in'
    `/home/pchat/projects/squads/squads/`, indexed in `/home/pchat/projects/squads/squads/.squads.json`. ...

    $ uv run sq skill sq-memory show --raw | grep "It's yours"
    timing quirks, gotchas, conventions. It's yours (`/home/pchat/projects/squads/squads/agents/memory/<role>/`) and

Before the collapse the same two lines read `` `squads/` `` and
`` `squads/agents/memory/<role>/` ``.

Root cause: two different values share one context-key name. The deleted
`ServiceCore.skill_definition_text` passed `squad_dir=self.paths.config.squad_dir` — the squad
*folder name* from `.squads.toml`. `render_source_view` passes the `squad_dir: Path | None` that
`ItemsMixin.read_body` hands `expand_view_tags`, which is `self.paths.squad_dir`, an absolute
path. `templates/views/squads_skill.md.j2` and `templates/views/memory_skill.md.j2` were moved
across that boundary unchanged, so `{{ squad_dir }}` silently changed meaning. The same variable
name still means the folder name in `claude/claude_section.md.j2` and
`agents_md/agents_section.md.j2`, both rendered from the backend — so one template corpus now has
two incompatible meanings for one key.

Why the suite did not catch it: `tests/goldens/claude_md_section.txt` and
`agents_md_section.txt` pin the relative form for the two *backend* templates, and there is no
golden or assertion anywhere in `tests/` for the skill text's `squad_dir` rendering
(`grep -rn squad_dir tests/integration/test_squads_skill_content_generation.py
tests/integration/test_memory_skill_generation.py` -> no hits; the pattern was validated against
a known positive first). `greeting_skill.md.j2` reads no `squad_dir`, which is why only two of
three moved.

Consequences beyond wrongness: the generated agent guidance is now machine-local, so two
developers on the same repo read different text for the same skill; and it leaks the operator's
home directory into agent-facing prose.

Either pass the folder name under its own key and restore the two templates' output, or rename
the view context key so the collision cannot recur — and pin whichever form is chosen with an
assertion, since nothing currently does.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-09-08T13:41:36Z] Paul Reviewer:
  - Verified by comparing rendered text, the way the regression was found — three ways, each with
    its disproving search validated against a known positive first.
    
    1. **Path-independence.** The same corpus copied to two very different absolute roots, both
    synced by this build: all 21 rendered definitions (`sq skill/role <slug> show --raw`)
    byte-identical across the two roots, and no rendered text contains an absolute path. The
    `grep` that found no leak was validated by running it against the pre-fix build's renders,
    where it correctly hits `sq-memory` and `squads`.
    
    2. **Baseline equality.** All 21 rendered definitions are byte-identical to the v0.14.0 build's
    own output for the same slugs — US5's "byte-identical" acceptance now genuinely holds, which it
    did not when this was filed. The comparison loop was validated on a known positive (the same
    loop against the pre-fix renders reports exactly `skill-sq-memory` and `skill-squads`).
    
    3. **Falsification.** Reverting `render_source_view`'s call to pass the raw `Path` reddens 6
    tests, including both new pinning assertions.
    
    The four pre-existing tests that were changed are corrections, not loosened: each asserted
    `sd == str(squad_dir)` and now asserts the configured folder name, still an exact-value
    assertion that fails if the `Path` returns.
    
    Residual filed as F11: the fix derives the name with `Path.name`, so a nested `squad_dir`
    (`docs/squad`) still renders `squad/` in the skill text against `docs/squad/` in `CLAUDE.md`.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — linearize_lifecycle global to filter breaks an adopter template override

<!-- sq:finding:F3:body -->
**Driven.** Converting `linearize_lifecycle` from `env.globals` to `env.filters` is a breaking
change to a documented adopter extension point, and it fails hard rather than degrading.

Reproduction: build a squad on `5576511e`, `sq override scaffold workflow.md.j2` (the scaffold
copies the bundled template, which called `{{ linearize_lifecycle(...) }}` as a global at two
sites), change nothing, then run the 0.15.0 build against it:

    $ sq workflow
    error: template 'workflow.md.j2' failed to render: 'linearize_lifecycle' is undefined

    $ sq skill squads show
    error: view 'squads_skill' failed to render on SKILL-20: template
    'views/squads_skill.md.j2' failed to render: 'linearize_lifecycle' is undefined

(`squads_skill.md.j2` includes `workflow.md.j2`, so the override poisons the skill too.)
`sq check` reports only `warn ... override may be stale: bundled workflow.md.j2 changed since
v0.14.0`, which is the generic drift advisory every bundled-template change raises and says
nothing about a hard render failure. `sq sync` reports `synced managed files to this squads
version` and exits 0.

The conversion itself is correct — ADR-880's ruling is literal that the sanctioned extension
point is a registered filter, and TASK-923's scope names the conversion. What is missing is the
adopter half: nothing in the CHANGELOG's 0.15.0 section mentions it, `sq migrate chlog` has no
manual step for it, and the failure is a bare template error rather than something that names
the fix.

Cheapest containment is to keep `env.globals["linearize_lifecycle"]` as an alias for one release
alongside the filter, and note the deprecation; failing that, the 0.15.0 CHANGELOG needs an
explicit "if you override `workflow.md.j2`, change `linearize_lifecycle(x)` to `x |
linearize_lifecycle`" line. Registering the same callable twice is not the same defect the ruling
was guarding against — the ruling forbids query logic in templates, not a compatibility alias.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-09-08T13:41:36Z] Paul Reviewer:
  - Verified driven, with the pre-fix build as the known positive on the same corpus. A v0.14.0
    build scaffolded `workflow.md.j2` (whose two call sites use the global form), nothing edited:
    
    - pre-fix build: `sq workflow` → `error: template 'workflow.md.j2' failed to render:
      'linearize_lifecycle' is undefined`, exit 1; `sq skill squads show` → the same failure
      through the `squads_skill` include, exit 1.
    - this build: both render clean, exit 0, with the unmodified 0.14 override in place.
    
    Falsified myself: deleting the `env.globals` line reddens the two global-form tests and leaves
    the bundled-template test green — the asymmetric result that proves the test isolates the alias
    rather than the filter. `sq override diff workflow.md.j2` also resolves against the v0.14.0
    base and shows the call-shape change, so an adopter can see it.
    
    On the changelog question the dev deferred: **yes, it needs an entry**, and the reason is the
    alias's own one-release scope. A deprecation nobody is told about is a delayed break — an
    adopter whose override keeps working through 0.15.x has no signal before the line is dropped.
    The 0.15.0 section currently has two Added entries and no Changed/Deprecated section at all.
    Routing the request rather than writing the prose (`@tech-writer`, on the review's own thread).
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — sq repair aborts with a raw AssertionError traceback, not a SquadsError

<!-- sq:finding:F4:body -->
**Driven.** `_converge_body_tag` (`src/squads/_services/_maintenance.py:313`) raises a bare
`AssertionError` when a role's or permanently-system skill's `sq:body` holds marker-shaped
content. `sq repair` has no handler for it, so the user gets a rich-rendered Python traceback and
the whole sweep aborts — on the one command whose job is to recover a damaged corpus.

Reproduction: in a synced squad, put marker-shaped bytes in a role's body region (a legacy
region, a partial migration, a hand-edit someone is running `sq repair` to undo), then:

    $ sq repair
    ... 20 lines of traceback through _strip_retired_regions / _converge_body_tag ...
    AssertionError: repair backfill: expected an empty, already-tagged, or plain
    legacy-rendered sq:body for 'role_definition', found marker-shaped content
    'legacy rendering with a nested region [a well-formed sq:oldthing tag]' — ...
    exit 1

Two problems, both against project convention:

- **Wrong exception class.** `CLAUDE.md`: "User-facing errors subclass `SquadsError`; the CLI's
  `@handle_errors` turns them into a clean message + exit 1. Raise those, not bare exceptions."
  The message text is good and should survive verbatim inside a `SquadsError`; only the class and
  the traceback are the defect.
- **One bad file blocks every other repair.** The sweep is corpus-wide and the raise is
  mid-transaction, so a single unexplained region stops the other 21 files from being converged.
  A per-file report ("skipped ROLE-000001: ...") would let the rest of the pass complete, which
  matters much more now that F1's recovery path is `sq repair`.

The guard itself is right and load-bearing: refusing to guess at marker-shaped bytes is the
correct call, and `test_marker_shaped_content_is_not_silently_overwritten` catches its removal
(falsified — removing the `find_markers` check makes the same input converge silently).
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-09-08T13:42:02Z] Paul Reviewer:
  - Verified driven, on both callers of the guard.
    
    Through `sq repair`, on a 0.14-shaped corpus with one role's body region holding marker-shaped
    content: the message is a clean `error: skipped ROLE-1: ...` with the guard's original text and
    no traceback, exit 1; the other 20 files converge; the marker-shaped region is byte-untouched.
    Through `sq sync` (the caller F1 added, which is what made this matter): the same file is
    reported as a warning, the other 8 roles converge, the region is untouched, exit 0 per that
    verb's documented posture.
    
    The guard is genuinely unweakened — it still refuses to overwrite what it has no model for, and
    what changed is only what happens after the refusal. `ROLE-1` rather than `ROLE-000001` in the
    message is the project's unpadded display-id convention (`Item.id`), not a defect; checked
    before flagging it.
    
    Residue filed as F15: `sq migrate up` collects the same `skipped` list from its trailing repair
    and prints none of it, so on the migration path the refusal is silent.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — The repair classifier seeds role and system-skill tags without checking the spec declares them

<!-- sq:finding:F5:body -->
**Driven.** `MaintenanceMixin._repair_body_tag` (`_services/_maintenance.py:1854-1866`) is
spec-aware for a per-item-type skill and spec-blind for a role and the three permanently-system
skills. The per-type branch only names a tag when `item_type_for_skill_slug(slug, self.spec)`
resolves, so a dropped type's stale skill is left alone. The role branch returns the bare literal
`"role_definition"` and the system-skill branch reads a fixed dict, neither of which consults
`spec.views` at all — so `sq repair` writes a tag naming a view the active spec does not declare,
and keeps writing it.

Reproduction: in a synced squad, add to `.overrides/workflow.toml` a `[selected]` block whose
`views` list omits `role_definition` (a documented, supported way to drop declared vocabulary):

    $ sq check
    error ROLE-000002-architect.md: no declared view 'role_definition' with a resolvable
      presentation template; see `sq workflow views` for the declared set
    ... one per role, 9 errors ...

Nine error-level findings on nine files the adopter never authored and cannot repair: there is no
`view` verb in the `sq role` addressing group, `set_body` refuses a role body, and running
`sq repair` re-converges the tag back in because the classifier does not know the view is gone.
The reads themselves degrade correctly — `expand_view_tags` leaves an unresolvable tag literal —
so this is a *stuck error state*, not a crash.

This is board notice 6 ("customisation must not be able to break squads") and it is the exact
coupling ADR-880's third amendment §3 refused a per-type view name in order to avoid: "an
adopter's ordinary customisation would produce corpus-wide errors from a declaration they never
wrote." The amendment closed that door for the *type-name-in-view-name* shape and left it open
for the three fixed view names the same commit seeded into every corpus.

Gate the role and system-skill branches on the view being declared in `self.spec.views`, the way
the per-type branch already gates on the type being declared — one condition, and the three
branches then agree about what "live" means.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-09-08T13:42:03Z] Paul Reviewer:
  - Verified as scoped, driven, with the pre-fix build as the known positive. On a 0.14-shaped
    corpus with `role_definition` dropped through `[selected].views`:
    
    - pre-fix build, `sq repair`: seeds 9 dangling tags, `sq check` reports 9 errors.
    - this build, `sq repair`: seeds 0, `sq check` reports 0.
    
    So the classifier gate is correct and load-bearing, exactly as the finding prescribed, and the
    dev's caveat about already-tagged bodies is accurate — an already-tagged file is untouched
    either way.
    
    **On the residual disposition, ruled rather than assumed.** The argument that clearing a
    dangling tag from a role or permanently-system skill body is convergence rather than undoing an
    author is a strong one — `set_body` refuses those bodies unconditionally, so there is no author
    to undo, and it keys on the item's current classification rather than on the tag's provenance,
    which is the thing ADR-880's second amendment §3 actually refused ("nothing records a tag's
    provenance and a rule that varied by arrival path would be unimplementable as well as wrong").
    It is not, however, a reviewer's call: that amendment ruled in general terms that a tag valid
    when placed and no longer valid is "not stripped, not relocated, not silently repaired", and
    carving a per-type exception into it is an amendment, not an implementation detail.
    
    But that question is not what has to be answered first, because the harm is not only
    historical. `_create_core` still seeds the tag with no `spec.views` check, so activating a role
    under a dropped view mints a fresh error every time — driven, filed as F12. Two closures that
    need no doctrine change at all, and together leave nothing for an amendment to fix:
    
    1. Gate `_create_core` (F12) — the same one-line condition, on the writer the fix skipped. Stops
       producing new instances.
    2. Expose `view add`/`view rm` on the `sq role` / `sq skill` addressing groups. The doctrine
       already names `view rm` as the sanctioned recovery — "taking a tag off a document must keep
       working for a view the spec no longer declares, and it is the recovery path for precisely
       this state" — and roster items are simply the one family whose addressing group never exposed
       it (verified: `sq role <slug>` offers show/regen/rm/status/set-default, `sq skill <slug>`
       show/regen/rm/status). That turns "no supported command" into the command the ADR already
       provides, and keeps "visible, never undone" intact, because an operator removes it
       deliberately rather than the tool doing it silently.
    
    Recommendation: F5 stands Verified on its own terms; F12 is the in-scope defect to fix now; the
    `view` verb gap is worth its own item; the "have the sweep clear it automatically" variant is
    the only one that needs the architect, and it stops being necessary once 1 and 2 land.
- [2026-09-08T14:59:39Z] Paul Reviewer:
  - - **The recovery verb delivers F5's residue, confirmed driven, and it delivers it the way the
      doctrine requires.** Three things had to hold and all three do:
      1. It clears the state F5 leaves on an already-tagged corpus. On a squad with
         `role_definition` dropped and nine pre-drop role tags standing:
         `sq role manager view rm role_definition` -> `ROLE-1: view role_definition removed from
         sq:body`, the body region goes empty, and `sq check`'s error count drops 12 -> 11 with
         that file no longer named. Same on the skill group
         (`sq skill squads view rm squads_skill`). Idempotent: a second `rm` says `was not
         present, nothing to do`.
      2. Nothing removes a tag automatically. `remove_view` is only ever reached from a CLI verb —
         `_cli/_items.py::_cmd_view`, and now the two roster groups; no service, sweep, backend or
         migration calls it. `sq repair` on the same corpus re-converges an *empty* body onto its
         tag but never strips a standing one, and `_repair_body_tag`'s gate means it does not
         re-seed under a dropped view either. So "visible, never undone" holds: the operator
         removes, the tool does not.
      3. The insert direction still refuses at the door. `sq role manager view add role_definition`
         under the dropped view: `error: no declared view 'role_definition' with a resolvable
         presentation template`, bare exit **1**. Same on the skill group. Both go through
         `resolve_view_target`, the one predicate the file scan and read-time expansion use, so
         the door and the scan cannot disagree.
    - So **no amendment to ADR-880 is needed**, and my ruling last round stands on evidence rather
      than on the argument: the second amendment's "not stripped, not relocated, not silently
      repaired … visible, never undone" is intact, and `view rm` — which the amendment names by
      name as "the recovery path for precisely this state" — is now reachable for the one item
      family whose addressing group never exposed it. F5 is closed in substance, not just for new
      instances.
    - One observation, deliberately **not** filed as a finding because it is pre-existing and
      identical on the generic group: `sq role <slug> view add greeting_skill` succeeds (exit 0),
      and `sq role <slug> show` then renders the greeting skill's text as that role's definition.
      `_SOURCE_APPLICABILITY` treats a `self` source as applying to any type, so the predicate is
      answering as declared — the new verbs widen *reachability* of that placement to the roster
      groups without changing the rule. Worth knowing if the roster groups are ever documented for
      adopters; not a defect in this change.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — A declared type whose skill slug is already authored loses its guidance silently

<!-- sq:finding:F6:body -->
**Driven, in both trees.** The `strict_empty` fix (correctly) stops `sq repair` overwriting an
authored `sq-<slug>` skill whose type is later declared. The side effect, undeclared and
unreported, is that the declared type's *generated* guidance then has nowhere to live and nothing
says so.

Reproduction, run on `5576511e` and on `e40592e3`:

    sq init --roles minimal
    sq skill add sq-widget --desc "An authored runbook"
    sq skill sq-widget body -m "AUTHORED RUNBOOK — my own words."
    # then declare [items.widget] in .overrides/workflow.toml
    sq skill sq-widget show --raw

- On `5576511e`: renders the generated `widget` skill (lifecycle, commands, the sq-managed
  footer). The authored body is shadowed and unreachable.
- On `e40592e3`: renders `AUTHORED RUNBOOK — my own words.` The generated `widget` guidance is
  unreachable, and no other skill carries it.

After the flip, nothing recovers or reports the collision. `_write_managed_skill` leaves an
existing region byte-untouched; `_repair_body_tag` names `item_skill` but `strict_empty` declines
to converge; `sq check` says `✓ no issues` (verified after a `sq sync`, which clears only the
pointer-drift warning). `.claude/skills/sq-widget/SKILL.md` still tells the agent to
"load and follow its full definition with `sq skill sq-widget show`", which now hands it the
operator's private runbook in place of the type's lifecycle and verbs.

The precedence choice is defensible and probably right — not destroying authored content beats
showing generated text. What is missing is the report. `sq check` should say that `sq-widget`
documents the declared type `widget` but carries authored content, so that type has no reachable
generated guidance, and name the resolution (rename the skill, or drop the type). Right now the
only way to notice is to read the file.

Not covered by the generated-artefact diff either: that compared bundled types plus a synthetic
custom *type*, never a custom *skill slug* that a later declaration turns template-owned — which
is the only path `strict_empty` exists for.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-09-08T13:42:29Z] Paul Reviewer:
  - Verified driven and read. Reproduced the exact collision the finding described — `sq skill add
    sq-widget`, an authored body, then `[items.widget]` declared in `.overrides/workflow.toml` — and
    `sq check` now reports `warn SKILL-22: documents declared type 'widget' but carries authored
    content of its own — 'widget's generated skill guidance has nowhere to render; rename this skill
    or drop the type to resolve`. Both facts and the resolution, at warn, exit 0. Silent before the
    type is declared, and silent on an ordinary synced corpus (no spurious warnings on the 12
    tag-converged bundled skills).
    
    Falsified myself: short-circuiting the validator to `[]` reddens the positive test and leaves
    all four negative-direction tests green — the correct asymmetry for an advisory.
    
    Placement and closure both check out. CATALOG-tier per-item is the right tier: it needs the
    resolved `Item` (to read `extra[slug]`) crossed against the live spec, which the pre-frontmatter
    file scan cannot do, and it applies to exactly one type. Closed through all five surfaces —
    `VALIDATOR_NAMES`, `DEFAULT_VALIDATOR_LEVEL` (warn), `VALIDATOR_CONTEXT` (RAW_TEXT), `CATALOG`,
    `UNGUARDED_VALIDATOR_NAMES` — with the three import-time asserts intact, and declared in
    `[items.skill].validators` in the bundled spec. Correctly absent from
    `VALIDATOR_LEVEL_FLOOR` (a subset by assert, and an advisory wants no floor) and from the
    single/multi selection sets (it takes no param; those are subsets of the parameterized set).
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — The role view name is a bare literal in three writers

<!-- sq:finding:F7:body -->
**Read.** The skill view names are declared once and shared —
`interactions.SYSTEM_SKILL_VIEW_NAMES` and `interactions.ITEM_SKILL_VIEW_NAME`, both explicitly
documented as "the two writers this table is shared between, so the slug->view mapping is
declared in exactly one place". The role's view name is not: `"role_definition"` is a bare
literal in three places that must agree.

- `src/squads/_rendering/templates/agents/role.md.j2:2` — the creation scaffold's seeded tag.
- `src/squads/_services/_base.py:866` — `_create_core`'s belt-and-suspenders reseed.
- `src/squads/_services/_maintenance.py:1857` — `_repair_body_tag`'s classification.

(A fourth, `[views.role_definition]` in `_specs/workflow.toml`, is the declaration all three
must match.)

Failure scenario: renaming the bundled view — or an adopter declaring their own
`role_definition` replacement under a different name — leaves the two Python writers seeding a
dangling tag into every newly-activated role, which is an error-level finding under ADR-880's own
invariant, with nothing in the test suite pinning the three literals to the declaration. This is
exactly the agreement-pinning debt the third amendment held TASK-923 to on the slug inversion
("two implementations of 'which type does this skill document' is exactly the agreement-pinning
debt TASK-918 was held to"), applied inconsistently: one class of name got a constant, the
sibling class did not.

A `ROLE_DEFINITION_VIEW_NAME` beside the two existing constants, with the template reading it or
a test asserting the template's tag equals it, closes it.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-09-08T13:42:30Z] Paul Reviewer:
  - Verified read. `ROLE_DEFINITION_VIEW_NAME` sits beside the other two constants, and a grep for
    the string across `src/` leaves only the constant itself, the `[views.role_definition]`
    declaration, the creation template's static tag, doc prose, and the content store — no bare
    literal in any Python writer. The pinning test covers all four: the spec declaration, the
    template's raw bytes, `_create_core`'s reseed driven through `activate_role`, and
    `_repair_body_tag`'s classification.
    
    One thing worth noting for the record rather than as a defect here: this finding enumerated
    three writers, and F5's gate was applied to only one of them. The constant made all three agree
    about the *name*; nothing made them agree about *whether to write it at all*. That gap is filed
    as F12.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Two narration instances survived both sweeps, one of them false

<!-- sq:finding:F8:body -->
**Read**, after a grep pre-filter validated against a known positive. Both tasks ran the
ast+tokenize scanner and both report a clean sweep; two instances survived it. Reporting once,
with the full list, rather than as separate findings.

1. `src/squads/_interactions/__init__.py:957-958`, `example_assignee_slug`'s docstring:

   > Accepts either shape a caller's roster comes in — a plain `{"slug": ...}` mapping (every
   > caller **before this collapse**) or a real `RoleView` ...

   Two defects in one clause. "This collapse" is a build-process reference: a reader with no diff
   cannot tell what collapsed or when. And the parenthetical is **false in the present** —
   `templates/agents_md/agents_section.md.j2:44` still calls
   `example_assignee_slug(roles)` with the backend's dict-shaped `roles_data`, so the mapping
   shape is a live caller, not a historical one. The durable sentence names the two live callers.

2. `tests/unit/test_repair_body_tag_convergence_pure_function.py:20`, module docstring:

   > See ... for the end-to-end regression this guards: **an earlier version of this backfill**
   > converged unconditionally for every template-owned skill and silently destroyed an author's
   > real runbook the moment its slug's type was declared.

   No release ever shipped that version — it existed for part of one work session. The "before"
   exists nowhere but the diff, which is the stranger test's failure condition. What the reader
   needs is the invariant and why it can be violated ("a `sq-` slug can be authored before its
   type is declared, so converging on non-empty content would destroy real work"), with no
   history.

Two nearby past-tense sentences were checked and **pass** the carve-out, for the record, so they
are not on this list: `_converge_body_tag`'s `"Refused today" is not "refused every past
release"` and `test_migration_corpus.py:299`'s "loses the definition it used to store twice"
both describe a corpus state a reader can still reproduce from the frozen fixtures.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-09-08T13:42:31Z] Paul Reviewer:
  - Verified read, both instances. `example_assignee_slug`'s docstring now names its two live
    callers in the present tense, and both call sites resolve —
    `agents_md/agents_section.md.j2:44` passes the dict-shaped `roles`,
    `views/squads_skill.md.j2:138` passes `source.roster` — so the parenthetical that was false in
    the present is gone rather than reworded. The convergence test's module docstring now states
    the invariant and why it can be violated, with no "an earlier version".
    
    Swept both commits' added lines for the wider phrase family (this collapse/pass/phase/round,
    before this, previously, an earlier version, the reviewer, used to be, plus ticket-ID shapes):
    zero hits. Validated the pattern against the two known positives in the pre-fix tree first —
    it finds both.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — sq role show lost its unresolvable-role advisory

<!-- sq:finding:F9:body -->
**Read.** `_cli/_role.py`'s `show_role` lost its third branch. Before, an activated role whose
catalog resolution raised `RoleNotFoundError` printed
`(the definition for <slug> could not be resolved — run `sq check` to see why)`. Now the same
role renders a definition, because the tag's `role` source goes through
`resolve_role_for_item`, which degrades to `RoleDef.from_extra_or_item` rather than raising.

TASK-922's ST2 comment calls this "a defensible behavior improvement", and it is defensible —
but it is an undeclared CLI behaviour change against US1's own acceptance ("role show output is
unchanged for every existing role"), and what it costs is the only place the CLI pointed a user
at the diagnosis. The panel above still degrades to item fields, so the user now sees a
plausible-looking card and a plausible-looking definition with no signal that a project override
is broken; the comment two blocks up in the same function still asserts the opposite intent —
"an invalid override must be reported, never quietly replaced by the stored item's own copy of
the fields".

Either restore a one-line advisory when `r is None` (the branch that computes it is still there),
or record the change deliberately — it is a small surface, but it is the diagnostic path for a
broken `.overrides/roles.toml`, and it went away as a side effect rather than as a decision.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-09-08T13:42:32Z] Paul Reviewer:
  - Verified driven. Scaffolded and activated a custom role, then deleted its
    `.overrides/roles/<slug>.toml`: `sq role <slug> show` prints `(the definition for <slug> could
    not be resolved — run `sq check` to see why)` alongside — not instead of — the degraded body
    render, and the healthy control prints no advisory. The degrade-rather-than-raise behaviour is
    untouched, as the finding asked.
    
    One observation, checked rather than assumed and **not** a regression: `sq check` reports
    nothing about the missing override in that state, so the advisory's own promise is hollow. I
    drove the same scenario on the v0.14.0 build and its `sq check` was equally silent, so this
    predates the collapse and the restoration is faithful to what existed. Worth its own item some
    day; not this review's.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — sq repair reorders the index, so the backfill is a 38k-line diff

<!-- sq:finding:F10:body -->
**Driven.** The mandatory backfill produced a 37,994-line diff in `squads/.squads.json` for a
semantically identical index. Parsing both revisions of the file and comparing field by field:
889 items before and after, identical key set, and exactly three real changes —
`squads_version` `0.14.0` -> `0.15.0`, plus TASK-923's and TASK-924's own subtask statuses. The
rest of the churn is `items` key **order**: `sq repair` rebuilds by globbing the corpus
(`_rebuild_index_from_disk`), so the rebuilt map is in directory-walk order rather than the
incremental insertion order it replaces. First divergence is at index 15 of 889, and neither
order is sorted.

This is pre-existing behaviour, not something the feature introduced — but this feature is what
makes every adopter run `sq repair` once, so it is the first time it lands as a 38k-line commit
on a file a team shares. The cost is real: a reviewer cannot see from the diff that nothing
moved (I had to parse it to answer the question), and any two people repairing on different
filesystems produce conflicting orders.

Serialising `items` in `sequence_id` order on write would make the index diff-stable for good.
Cheap, and independent of this feature; recording it here because it is where it surfaced.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-09-08T13:42:49Z] Paul Reviewer:
  - WontFix accepted, and the deferral is properly homed: TASK-929 exists, Draft, carrying an
    `addresses` ref back here, so the finding is treated rather than triaged away.
    
    Confirmed by the F1 verification that it does not spread: the version-drift backfill does not
    call `repair()`, and `.squads.json` is byte-identical across a drift sync on a real 22-item
    corpus — so this stays a `sq repair` property and does not become an every-sync event.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — squad_dir display derives the folder name, so a nested squad_dir still diverges

<!-- sq:finding:F11:body -->
**Driven.** F2's leak is fixed for a single-segment `squad_dir`, but the fix recovers the
folder name with `Path.name` (`_views.py::_squad_dir_display`), so it is only equal to the
configured value when that value is one path segment — and nothing enforces that. With a
nested `squad_dir`, the same key still means two different things in one template corpus,
which is the defect F2 asked to make unable to recur.

Reproduction, on a fresh squad:

    $ sq init --squad-dir "docs/squad" --roles minimal
    $ sq skill squads show --raw | grep 'indexed in'
    `squad/`, indexed in `squad/.squads.json`. ...
    $ grep 'indexed in' CLAUDE.md
    ... under `docs/squad/` and indexed in `docs/squad/.squads.json` ...

The backend-rendered managed section says `docs/squad/`; the view-rendered skill text says
`squad/`, which is not a path that resolves from the project root at all. The generated agent
guidance therefore names a directory that does not exist, on the one surface an agent is told
to read first.

The pre-collapse build is correct here — the deleted `skill_definition_text` passed
`self.paths.config.squad_dir` verbatim. Driven on the v0.14.0 build against the same
`--squad-dir docs/squad` shape: both surfaces read `docs/squad/`. So this is the same
regression F2 reported, narrowed rather than closed.

`SquadsConfig.squad_dir` is a bare `NonEmpty` with no single-segment constraint, and
`sq init --squad-dir docs/squad` is accepted and works.

`_squad_dir_display`'s own docstring states the assumption as a property ("`.name` recovers
exactly the configured folder name — the single path segment the field's own docstring
documents") — the field's docstring says "Folder (relative to the project root)", which a
multi-segment value satisfies. A docstring is the wrong place for that invariant either way.

Two closures, either one sufficient: thread the configured string (`config.squad_dir`) into
the view-rendering path beside the resolved `Path`, so no derivation is involved and the two
call sites agree by construction — the first of the two options the finding named; or
constrain `squad_dir` to one segment at the config boundary, so the derivation is sound and
`sq init` refuses the shape rather than producing wrong guidance from it. The new pinning
assertions should then cover a nested value, not only the default.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-09-08T14:58:07Z] Paul Reviewer:
  - - Verified, driven, on a **three**-segment nested value rather than the two-segment repro the
      finding used — `sq init --squad-dir docs/nested/squad`, real CLI in a scratch project:
      `sq skill squads show --raw`, `sq skill sq-memory show --raw` and `CLAUDE.md` all render
      `docs/nested/squad/` and `docs/nested/squad/.squads.json`. No truncation to the last segment
      anywhere.
    - F2's own criterion re-checked on the same squad, with the disproving search validated against
      a known positive first: the absolute project path appears **0** times in each of the `squads`,
      `sq-memory` and `greeting` skill texts, in `sq role manager show`, and in `CLAUDE.md`; the same
      `grep -cF` pattern returns 1 against a synthetic line containing that path.
    - **Class-closed, and by construction rather than by discipline.** The fix did not derive one
      value from the other and it did not add an invariant on the input: `squad_dir: Path | None`
      (disk access, for `_resolve_role_source`) and `squad_dir_display: str | None` (the template's
      `{{ squad_dir }}`) are now two parameters with two *types*, threaded side by side through
      `expand_view_tags` -> `_render_resolved_source_or_raise` -> `render_resolved_source` ->
      `render_source_view`. Collapsing them back is a pyright error under strict mode, not a silent
      behaviour change — which is the property my own note about this class asked for and did not
      get last round. `_squad_dir_display` is gone, so there is no derivation left to be wrong.
    - Both service callers pass the configured string: `_services/_items.py::read_body` and
      `_services/_views.py::render_view`. Both backends already did (`_claude_code/_backend.py:103`,
      `_agents_md/_backend.py:101`).
    - Checked for a sibling rather than only this instance: enumerated every `{{ … }}` expression in
      `templates/views/*.j2`. `squad_dir` is the only path-shaped value any view template reads —
      every other is `item`/`spec`/`source`/a badge field. There is no second derived-path value in
      the view-render path to have missed.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — The role creation path still seeds a tag for an undeclared view

<!-- sq:finding:F12:body -->
**Driven.** F5's gate covers two of the three writers that name a role's placement tag. The
third, `ServiceCore._create_core`, seeds it unconditionally — so the state F5 reported is not
only left standing on an existing corpus, it is freshly produced every time a role is
activated under a dropped view.

The three writers are the ones F7 enumerated by name. The fix used the new shared constant in
`_create_core` (F7) but did not add the one condition there (F5):

    src/squads/_services/_base.py:866   # ROLE_DEFINITION_VIEW_NAME, no spec.views check
    src/squads/_rendering/templates/agents/role.md.j2:2   # static tag, no condition possible

Reproduction, on a synced squad whose `.overrides/workflow.toml` drops `role_definition`
through `[selected].views`:

    $ sq check                       # 9 errors, one per existing role
    $ sq repair; sq check            # still 9 — the gate holds, nothing re-seeded
    $ sq override scaffold --new sec-analyst   # fill in the stub
    $ sq role activate sec-analyst
    $ sq check                       # 10 errors

The new role's body region carries the sq:view:role_definition placement tag (spelled without
its comment wrapper here), naming a view the active spec does not declare.

`sq check` exits 3 on that state (verified bare, not through a pipe), so an adopter who drops
this view is in a permanently failing gate that grows by one error per role they add, on files
they never authored, with no verb that can remove the tag.

This is why the residual question F5 raised cannot be answered by weighing the doctrine alone:
the choice is not only "do we retroactively clear tags we already wrote" but "do we keep
writing them". Gating `_create_core` on the same `spec.views` condition needs no doctrine
change at all — it is the same one-line condition the fix already applied to the sweep, on the
writer the fix skipped. The creation template's static tag lands in a body `_create_core`
replaces on that path anyway, but it should be covered by the same test that pins its name.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-09-08T14:58:27Z] Paul Reviewer:
  - - Verified driven, with a live control in the same squad. On a synced squad whose
      `.overrides/workflow.toml` drops `role_definition` through `[selected].views`: `sq check`
      error count held **flat at 12 across two `sq role activate` calls and one `sq dev add
      --tech python`** (activate architect: 12; activate qa: 12; dev add: 11 after an intervening
      `view rm`, unchanged by the add). The new role files' `sq:body` regions are empty; only the
      role that was tagged *before* the drop still errors. So all three creation entrypoints
      (`sq role activate`, `sq dev add`, and the bulk importer, which shares `_create_core`) are
      covered by the one gate.
    - **The third writer's reasoning holds — checked, not accepted.** The claim is that
      `agents/role.md.j2`'s static tag needs no gate because `_create_core` overwrites the same
      region afterward. Two things had to be true for that to be authoritative, and both are:
      1. The overwrite is unconditional for a role. `_services/_base.py:874` calls
         `sections.replace_section(rendered, markers.BODY, …)` inside `if item_type == ROSTER_ROLE:`
         with **no** enclosing condition — only the *content* is conditional (the tag, or `""`).
         `_sections.replace_section` replaces everything between the marker pair, so `""` wipes the
         template's tag rather than leaving it. The template's output can never survive on this path.
      2. Nothing else renders that template's body region into anything that is trusted.
         `_template_for` has exactly two call sites: `_create_core` (above) and
         `ServiceCore.pristine_body`, which returns the scaffold's `:body` and is reached from a
         single consumer — `ItemsMixin._body_mutate`'s authored-body check — which raises
         `SquadsError` for `ROSTER_ROLE` several lines *before* the `pristine_body` call. So the
         ungated static tag is unreachable as a value, not merely overwritten as a file.
         `regen` regenerates the backend pointer only (`_services/_items.py:489`), never the item
         file. No migration writes a role body region.
    - So the gate on `_create_core` is authoritative for the role. **Instance-closed, not
      class-closed** — the identical writer on the skill side is ungated; filed as F17.
    - Doc nit for whoever touches this next, not a finding of its own:
      `_interactions/__init__.py`'s `ROLE_DEFINITION_VIEW_NAME` docstring still describes
      `_create_core` as *reasserting* the template's static tag "belt-and-suspenders". Under a
      dropped view it *overrides* it with an empty region, which is the whole point of this fix;
      and `_specs/workflow.toml`'s `[views.role_definition]` comment still says the scaffold "seeds
      the tag naming this view into every newly-activated role's `sq:body`", which is now false for
      exactly the configuration this finding is about.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — A skipped convergence is never retried and leaves sq check clean

<!-- sq:finding:F13:body -->
**Driven.** The version-drift trigger is one-shot: `sync()` stamps `squads_version` at the end
of the run whether or not the backfill it just ran actually converged everything. A body the
guard refused is therefore never retried, and the state it leaves behind is F1's own failure
signature — a definition that does not render, with `sq check` clean and `sq sync` reporting
success.

Reproduction, on a real 0.14.0-built corpus (roles/system skills with empty untagged bodies)
with one role's body region holding marker-shaped content the guard has no model for:

    $ sq sync
    warning: skipped ROLE-1: repair backfill: expected an empty, already-tagged, ...
    synced managed files to this squads version        # exit 0
    $ sq check
    ✓ no issues                                        # exit 0
    $ sq role manager show | tail -1
    legacy  x                                          # the stale content, not the definition
    $ sq sync
    synced managed files to this squads version        # no warning, nothing retried
    $ sq check
    ✓ no issues

After the first run the config reads 0.15.0, so the drift comparison is false forever and the
backfill never runs again. The one warning line scrolled past in a run that also said
"synced"; nothing durable records the state. `sq repair` also declines the same body (correctly
— the guard is right), so recovery is a hand edit, and nothing tells the operator that.

Note the asymmetry this creates with `sq repair`, which treats the identical skip as
`error:` and exits 1. Both postures are defensible on their own; together they mean the command
F1 routes every upgrade through is the one that reports the condition most weakly.

F1's own remedy list named the closure: "an advisory in `sq check` when a role or
permanently-system skill body carries neither its tag nor content". Nothing like that exists —
the file-level view scan only reports a tag that is *present* and unresolvable, never a missing
one, so an untagged roster body is invisible to every gate. Either add that advisory, or do not
stamp `squads_version` when the run reported skips, so the next `sync` retries.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-09-08T14:58:56Z] Paul Reviewer:
  - - Verified driven on a 0.14-shaped corpus: one role's `sq:body` holding marker-shaped content
      (an `sq:legacy` open/close marker pair around prose (tags written without their comment wrapper here)), `squads_version = "0.14.0"`.
      - `sq sync` #1: prints the `warning: skipped ROLE-1: repair backfill: … marker-shaped
        content … refuses to overwrite it`, and `.squads.toml` still reads `0.14.0` — the stamp
        was withheld.
      - `sq sync` #2, nothing else changed: the drift trigger is still true, the backfill runs
        again, the same skip is reported again, stamp still withheld. The condition is now
        durable and self-announcing rather than one-shot, which is exactly what the finding asked
        for.
    - Retry mechanism read as well as driven: the stamp guard is `if not backfill_skipped:` and
      `backfill_skipped` is *only* this run's own `_backfill_roster_body_tags` return — not the
      whole `skipped` list — so an unrelated skip (roster skew, an unindexed skill body) does not
      withhold the stamp and turn every sync into a permanent no-drift-forever state. That
      scoping is the part that could easily have been wrong and is right.
    - **Two residuals, both new with this fix, filed as F18** — `sq sync` still prints
      `synced managed files to this squads version` in green and exits 0 on the run that
      deliberately withheld the stamp, so the one line an operator reads asserts the thing the
      service just declined to do.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — A non-numeric squads_version makes sq sync raise a bare ValueError

<!-- sq:finding:F14:body -->
**Driven.** The new trigger compares `squads_version` with `schema_tuple`, which raises
`ValueError` on any segment that is not a plain integer. The CLI's own drift notice compares
the same field with `version_tuple` (`_cli/_common.py`), which strips non-digits and tolerates
it. So the two comparators disagree about the field's domain, and the tolerant one is what
tells the operator to run the command that then crashes.

Reproduction — a 0.14-shaped corpus whose `.squads.toml` reads `squads_version = "0.14.0rc1"`:

    $ sq check
    squads 0.15.0 detected (managed files at 0.14.0rc1). Run `sq sync` to refresh them.
    ✓ no issues                                     # exit 0
    $ sq sync
    ... rich-rendered traceback through _maintenance.sync / _schema.schema_tuple ...
    ValueError: invalid literal for int() with base 10: '0rc1'
    exit 1

The same input on the v0.14.0 build syncs cleanly (driven), so this is a new crash rather than
a pre-existing one — nothing parsed `squads_version` numerically before this trigger.

Reachable without a hand edit: `_stamp_version` writes `__version__` verbatim, so any install
whose package version carries a non-numeric segment (a pre-release, a `.devN` build, a local
version) stamps that string into `.squads.toml`, and every later `sync` from any build then
raises. A merged or hand-edited config does it too.

This is the exact class F4 was raised about — a bare exception and a traceback where the
project's convention is a `SquadsError` with a clean message — reintroduced at the new call
site by the same commit that fixed F4. Two closures: compare with the tolerant
`version_tuple` (moving it down out of `_cli` so `_services` can import it without inverting
the layering), or guard the comparison and treat an unparseable stamp as drift with a named
message.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-09-08T14:58:49Z] Paul Reviewer:
  - - Verified driven: a squad whose `.squads.toml` reads `squads_version = "0.14.0rc1"` —
      `sq check` prints the drift notice and exits 0, `sq sync` completes cleanly (`synced …`,
      bare exit 0, no traceback), and the stamp advances to `0.15.0`. No `ValueError`, and the
      two comparators now agree about the field, which was the acceptance.
    - The dev's same-shape audit checks out, verified independently rather than on the handback:
      the three remaining `schema_tuple` call sites are `_cli/_migrate.py:46` (disk
      `schema_version` vs `SCHEMA_VERSION`), `_services/_maintenance.py:1455` (`m.to_schema` vs
      disk) and `_cli/_common.py:1423` (disk vs `SCHEMA_VERSION`). All three read
      `schema_version`, which is hand-authored dotted-int and never carries a package suffix.
      Nothing else feeds a package version into a strict parser.
    - **One residual the swap inherited, filed as F21**: `version_tuple` strips non-digits *per
      segment and concatenates*, so `version_tuple("0.15.0rc1") == (0, 15, 1)` — a prerelease
      sorts **above** its own final release and equal to the next patch. F1's whole recovery
      depends on this comparison firing. A loud crash was traded for a quiet wrong answer in an
      adjacent shape; the alternative closure this finding named (treat an unparseable stamp as
      drift) would have been right for both.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — sq migrate up does not report the repair skips it collects

<!-- sq:finding:F15:body -->
**Read.** F4's fix threads a new `skipped` channel from `_converge_body_tag` out through
`RepairResult`, and wires it into `sq repair`'s CLI (printed at error level, exit 1). The other
consumer of the same result was not wired: `_cli/_migrate.py`'s `up` reads
`run.repair.strip_notice()` and nothing else, so a refused body-tag convergence during a
migration's trailing repair is printed nowhere and the command exits 0 reporting
"migrated ... index rebuilt".

    src/squads/_cli/_migrate.py:57   notice = run.repair.strip_notice() if run.repair else None

That is the one route a squad behind the current schema takes, and the one place the sweep runs
without the operator having typed `repair` — so it is where an unreported skip is least likely
to be noticed. `unreadable` is unreported there too, which predates this change; the new
channel simply inherited the hole rather than being asked about it.

Closure is one loop over `run.repair.skipped` beside the existing notice, with the same
wording `sq repair` already prints. Whether `sq migrate up` should also exit non-zero on a skip
is a separate call (it would change that verb's exit contract) — reporting it at all is the
part that is clearly missing.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-09-08T14:59:17Z] Paul Reviewer:
  - - Verified driven, bare, never through a pipe. On a squad set back to `schema_version = "0.13"`
      with one file carrying malformed frontmatter:
      - `sq repair` on the same corpus: names the file at error level, bare exit **1**.
      - `sq migrate up`: applies `0.14.0`, prints `migrated to schema v0.14; index rebuilt`, and
        bare exit **1**.
      - `sq migrate up` again (already current): `already at schema v0.14; nothing to migrate`,
        bare exit **0**.
    - **The guard the coordinator asked me to check is right.** `raise typer.Exit(1)` sits after
      the `if not applied: … return` early return, so the nothing-to-migrate case can never reach
      it — driven above, not just read. A migration that applied with a fully clean trailing repair
      falls through both `run.repair.unreadable` and `run.repair.skipped` as empty and exits 0, so
      a clean migration does not start failing. The condition is byte-for-byte the one
      `_cli/_main.py::repair` uses, which is what the two verbs' exit contracts had to share.
    - The `skipped` reporting loop is verbatim `sq repair`'s wording, and it fires on the migrate
      route.
    - **New residual, filed as F20**: the exit condition includes `unreadable`, and this command
      prints nothing about `unreadable`. Driven above — the run that exited 1 printed a *green*
      `migrated` line and never named the file that caused the failure. Before this change the
      same corpus was silent and exited 0; it is now silent and exits 1, which is better for a
      script and worse for a human. `sq repair` already has the loop.
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — The new empty-body hint names sq sync where a dropped view makes it a no-op

<!-- sq:finding:F16:body -->
**Driven.** F1's replacement hint and F5's gate interact: under a dropped view the gate
correctly leaves a roster body empty and untagged, and the new hint then tells the operator to
run the one command that provably cannot populate it.

Reproduction — a 0.14-shaped corpus whose `.overrides/workflow.toml` drops `squads_skill`
through `[selected].views`:

    $ sq sync            # exit 0; the gate leaves the body empty, correctly
    $ sq skill squads show | tail -1
    (empty — run `sq sync` to populate it)
    $ sq check
    ✓ no issues

`sq sync` has already run; running it again changes nothing, because `_repair_body_tag` now
returns `None` for a view the spec does not declare. The same applies to a role under a dropped
`role_definition`.

This is the defect F1 itself reported in the old hints — "the hint names an action that cannot
be taken" — in a new instance created by the two fixes landing together, which is why neither
task's own tests see it. Small surface, and the honest fix is cheap: the hint has the spec in
hand at that point, so it can distinguish "the view this body would render is not declared"
from "the backfill has not run yet" the same way the skill hint already distinguishes a dropped
item type.
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
- [2026-09-08T14:59:19Z] Paul Reviewer:
  - - Verified driven, both states, both groups.
      - Role, `role_definition` dropped through `[selected].views`: `sq role architect show` ends
        with `(empty — the view 'role_definition' is not declared in this project's spec, so
        `sq sync` cannot populate it; declare it in `.overrides/workflow.toml` … — or, if a role's
        body still carries this tag from before it was dropped, clear it with
        `sq role <slug> view rm role_definition`)`. Names the state, names the real remedy, does
        not send the operator at `sq sync`.
      - Role, `role_definition` declared and the body genuinely unpopulated: unchanged
        `(empty — run `sq sync` to populate it)`.
      - Skill: the dropped-*item-type* branch still takes precedence over the dropped-*view*
        branch (`dropped_type is None and …` in the `view_dropped` predicate), so the two
        conditions do not fight when both hold.
      - A per-item-type skill whose tag is already placed under a dropped `item_skill` renders the
        tag literally rather than hitting a hint at all — the accepted degradation, and `sq check`
        reports it with `view rm` as the remedy.
    - Both hints resolve the condition off `svc.spec.views`, the same predicate the classifier
      gates on, so the hint cannot disagree with what a sync will actually populate.
    - **New residual, filed as F19**: the *third* branch — declared view, empty body, "run
      `sq sync`" — is now false in a state this same commit made reachable. Driven.
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->

<!-- sq:finding:F17 -->
### F17 — Skill creation seeds a placement tag for an undeclared view

<!-- sq:finding:F17:body -->
**Driven.** F12's gate covers the *role* creation writer. The *skill* creation writer —
`ClaudeCodeBackend._write_managed_skill` (`_backends/_claude_code/_backend.py:209`) — seeds a
placement tag with no `spec.views` check at all, so under a dropped `item_skill` (or
`squads_skill`/`greeting_skill`/`memory_skill`) view a newly created skill body mints a fresh
dangling tag, and `sq check` grows by one error per skill created. That is F12's defect,
unchanged, on the writer nobody enumerated.

Reproduction, on a squad whose `.overrides/workflow.toml` drops `item_skill` through
`[selected].views`:

    $ sq check | grep -c '^error'          # 10, incl. SKILL-14 sq-widget
    $ cat >> squads/.overrides/workflow.toml   # declare [items.gadget]
    $ sq sync                              # exit 0, "synced managed files …"
    $ sq check | grep -c '^error'          # 11
    error SKILL-000015-sq-gadget.md: no declared view 'item_skill' with a resolvable
      presentation template; see `sq workflow views` for the declared set

The nine pre-existing errors are the F5 already-tagged state — correct, and now clearable with
`view rm`. `sq-widget` and `sq-gadget` are **new** files this build wrote after the view was
dropped. Driven control in the same squad: with `role_definition` also dropped, two
`sq role activate` calls and one `sq dev add` added **zero** errors. Role side flat, skill side
+1 each. Same class, same severity, one writer apart.

**Both call sites already hold the active spec**, so this is the same one-line condition F5 and
F12 applied, not a new mechanism:

    _backend.py:110   spec = ctx.spec if ctx.spec is not None else bundled_spec()
    _backend.py:116   body_tag=view_name,                       # SYSTEM_SKILL_VIEW_NAMES
    _backend.py:274   body_tag=interactions.ITEM_SKILL_VIEW_NAME    # playbook-lane types
    _backend.py:287   body_tag=interactions.ITEM_SKILL_VIEW_NAME    # custom types

The cheapest closure keeps the condition out of the backend: pass `body_tag=None` when the name
is not in `spec.views`. `_write_managed_skill` already has that branch, already documented as
"this method's own contract for a caller that doesn't have one (there is none today)" — it
writes an empty `sq:body` region, which is precisely the accepted quiet state F5's gate and
F12's gate produce. The branch stops being dead and no backend learns a new rule.

**Second route, read/inferred rather than driven**: `_migrations/_v0_11_to_v0_14.py:276` stamps
ids onto the skill body files the backend regeneration above it wrote, so `sq migrate up` on an
older corpus with the view dropped reaches the same ungated writer without an operator ever
typing `sync`.

**Why this one matters beyond its own blast radius.** The declaration site names its own
writers, two lines above the constant, and the sweep still missed it:
`_interactions/__init__.py:172-175` — "seeded … at creation (`_write_managed_skill`) and
backfilled … by `sq repair` (`MaintenanceMixin._repair_body_tag`) — **the two writers this
table is shared between**". F5 gated one of the two. F12 was scoped to the role name only and
nobody re-ran F5's condition against the sibling table. The enumeration existed in the code;
the sweep of it did not happen.

Board notice 6 applies: dropping a view through `[selected].views` is documented, supported
customisation (`docs/overrides.md`, "Dropping a view"), and it must not be able to put a squad
in a permanently failing gate that grows on its own.
<!-- sq:finding:F17:body:end -->

#### Discussion

<!-- sq:finding:F17:discussion -->
- [2026-09-10T08:16:58Z] Paul Reviewer:
  - - Verified driven on the shipped build. Squad with `item_skill`, `squads_skill` and
      `role_definition` all dropped through `[selected].views`:
      - declared a new `[items.widget]` type, `sq sync` -> the new `SKILL-…-sq-widget.md` body
        region is **empty and untagged**, `sq check` error count **11 -> 11**;
      - declared a second `[items.gadget]` type, `sq sync` -> same, still **11**. The growth
        signature I drove last round (+1 per declared type) is gone.
      - system-skill branch driven separately by forcing a *fresh* write: deleted the `squads`
        skill body file and re-synced — `_write_managed_skill` recreated it with an empty,
        untagged region, count still 11.
      - controls: `sq role activate architect` added 0; `sq repair` added 0 (the F5 gate still
        holds and nothing re-seeds).
    - **Falsified in an isolated `git worktree`, never in this tree.** Reverting all three gates
      (`body_tag=view_name`, the `item_skill_body_tag` block, both per-type call sites) reddens
      three of the four rows in
      `tests/service/test_skill_creation_seeds_no_tag_for_an_undeclared_view.py`, including
      `test_repeated_skill_creation_under_a_dropped_view_adds_no_check_findings` with the exact
      growth assertion. So the behavioural test would have caught this instance before the fix.
    - The gate reads the same condition on both call sites, off `ctx.spec` (already resolved at
      each), and passes `None` — which revives `_write_managed_skill`'s own documented `None`
      branch rather than teaching the backend a new rule. That is the shape I recommended and it
      keeps the spec question out of the backend's own body.
<!-- sq:finding:F17:discussion:end -->
<!-- sq:finding:F17:end -->

<!-- sq:finding:F18 -->
### F18 — sq sync reports success and exits 0 on a withheld stamp

<!-- sq:finding:F18:body -->
**Driven.** F13's fix withholds the `squads_version` stamp when the backfill declined a body —
correct, and verified on its own thread. `sq sync`'s own output was not re-derived from that
change: the CLI prints a green success line asserting the stamp, and exits 0, on the run that
deliberately did not stamp.

    $ grep squads_version .squads.toml
    squads_version = "0.14.0"
    $ sq sync
    squads 0.15.0 detected (managed files at 0.14.0). Run `sq sync` to refresh them.
    warning: skipped ROLE-1: repair backfill: expected an empty, already-tagged, …
    synced managed files to this squads version          # green
    $ grep squads_version .squads.toml
    squads_version = "0.14.0"                            # not stamped
    $ sq sync >/dev/null 2>&1; echo $?
    0

`synced managed files to this squads version` is affirmatively false there: the whole point of
the fix is that this run is *not* at this squads version, and the drift notice on the very next
command says so. The information is in hand at the call site —
`_cli/_main.py::sync` already holds `skipped = await svc.sync()` — and
`MaintenanceMixin.sync`'s own docstring documents the withheld stamp, so the CLI is the only
layer that does not know.

Closure for the message is one condition on a list the caller already has: a run that reported
a backfill skip says so instead of claiming the version ("managed files regenerated; the
version stamp was withheld because …" / point at the skip line above it). Note the service
currently returns one flat `skipped` list, so telling a *backfill* skip apart from a roster-skew
or unindexed-body skip needs either a second return channel or a check on the message shape —
worth doing properly rather than string-matching.

**The exit code is a separate call and I am not asserting it here.** `sq repair` exits 1 on this
condition, and `sq migrate up` now does too (F15's follow-up), which leaves `sq sync` — the
command F1 routes every upgrade through — as the one member of the corridor that reports partial
completion at exit 0. That asymmetry is exactly what F13's own text flagged. But `sq sync`
already exits 0 for several other pre-existing skip channels (roster skew, unindexed skill
bodies), so making it exit 1 changes that verb's contract for more than this one condition and
belongs to whoever owns the corridor's exit semantics, not to this finding.
<!-- sq:finding:F18:body:end -->

#### Discussion

<!-- sq:finding:F18:discussion -->
- [2026-09-10T08:16:59Z] Paul Reviewer:
  - - Verified driven. A 0.14-shaped corpus with one role body the guard refuses:
      - `sq sync` prints the `warning: skipped ROLE-1: …` line and then
        `managed files regenerated; the version stamp was withheld — see the skip(s) reported
        above`. The green `synced … to this squads version` line is gone. `.squads.toml` still
        reads `0.14.0`.
      - Second `sync`: the skip **is** re-reported (checked, because the new sentence points "above"
        — a sentence referring to output that had stopped printing would have been a new false
        claim), and the withheld-stamp line repeats.
      - Regression control: an ordinary clean sync still prints the green line (driven, and pinned
        by the fix's own `test_sync_clean_row_still_claims_success`).
    - Exit stays 0, which is exactly what this finding scoped: I wrote that the exit code was a
      separate call because `sq sync` already exits 0 for pre-existing skip channels, and the fix
      left it alone and said so in place. No complaint — the divergence is now stated at the row
      that tests it rather than being silent.
    - The channel is carried structurally rather than string-matched: `sync()` returns
      `SyncSkips(list[str])` with `.backfill_skipped`, and the CLI reads that attribute. Checked
      the zero-breakage claim rather than accepting it — exactly one reader
      (`_cli/_main.py:1219`), reading the return value directly with no slicing, concatenation or
      `list()` round-trip in between, so the subclass-attribute-erasure hazard a `list` subclass
      carries is not live; `assert await svc.sync() == []` in the existing service tests still
      compares as a plain list.
<!-- sq:finding:F18:discussion:end -->
<!-- sq:finding:F18:end -->

<!-- sq:finding:F19 -->
### F19 — The declared-view empty hint still names sq sync where only repair helps

<!-- sq:finding:F19:body -->
**Driven.** F16 gave the empty-body hint a branch for "the view is not declared". The *other*
branch — view declared, body empty, "run `sq sync` to populate it" — is true only while a
`squads_version` drift is still outstanding, because that is the only trigger for
`_backfill_roster_body_tags`. This commit made the false case reachable through the verb it
added in the same change.

Reproduction, on an ordinary synced squad (no override, `squads_skill` declared):

    $ sq skill squads view rm squads_skill
    SKILL-13: view squads_skill removed from sq:body
    $ sq skill squads show | tail -1
    (empty — run `sq sync` to populate it)
    $ sq sync
    synced managed files to this squads version
    $ sq skill squads show | tail -1
    (empty — run `sq sync` to populate it)          # unchanged
    $ sq repair
    rebuilt index: 17 items, counter=17
    stripped retired regions from 1 item file — review the diff
    $ sq skill squads show                          # renders again

`sq sync` cannot help: `sync` only reaches the backfill when
`version_tuple(__version__) > version_tuple(recorded_version)`, and the stamp is already
current; `_write_managed_skill` leaves an existing region byte-untouched by design. The actual
remedies are `sq repair` (driven above) or `sq skill <slug> view add squads_skill`, and the hint
names neither. Same on the role group after `sq role <slug> view rm role_definition`.

This is F1's own complaint — "the hint names an action that cannot be taken" — in its third
instance, and the second one created by a fix for the previous one. Note the code comment
introduced by this commit states the false property in so many words:
`_cli/_skill.py`, "or the type and view are both live but nothing has backfilled the tag onto
this body yet (`sq sync` is the fix, **and only the fix**, for that one case)". It is not the
fix for that case unless a drift is outstanding.

Closure: the hint has three inputs, not two, and the third is already on `svc.paths.config`.
Resolve the whole question in one helper — is the view declared / is the tag present / is a
version drift outstanding — and let all three call sites (`sq role show`, `sq skill show`, and
`sq check`'s own file scan message) read the same answer, the way `resolve_view_target` already
unifies the placement, scan and read-time questions. Three call sites each answering part of it
is why this branch was left behind.
<!-- sq:finding:F19:body:end -->

#### Discussion

<!-- sq:finding:F19:discussion -->
- [2026-09-10T08:17:20Z] Paul Reviewer:
  - - Verified driven, three states x two groups, and — the part that matters — **each state's own
      claim checked for truth**, not just for being a different sentence:
      - **declared + drift outstanding** -> `(empty — run `sq sync` to populate it)`. Verified the
        claim: ran `sq sync`, the body came back as its placement tag and the definition rendered.
        True.
      - **declared + no drift** (body emptied with `view rm`, stamp current) -> `(empty — `sq sync`
        cannot populate it: the version-drift backfill it relies on has nothing outstanding to run.
        Try `sq repair`, which converges an already-tagged or plain-legacy body regardless of
        drift — or, if this body is genuinely untagged, `sq role <slug> view add
        role_definition`)`. Verified: `sq sync` changed nothing, and both named remedies are the two
        I proved were the real ones last round. This is the exact state and the exact false sentence
        this finding was about.
      - **view undeclared** -> names the view and `view rm`, unchanged from F16.
      - Same three on `sq skill`, with the skill's own slug interpolated into the `view add`
        suggestion.
    - One predicate, and it is genuinely one: `squads._views.empty_body_hint_state(name, spec, *,
      drift_outstanding)` is pure, takes `drift_outstanding` from the caller instead of recomputing
      it, and both `show` commands compute that flag with `version_drifted` — the same predicate
      `sync()` gates its backfill on. So the hint and the behaviour cannot disagree *by
      construction*, which is the property I asked for rather than three call sites each answering
      part of the question.
    - The false comment ("`sq sync` is the fix, and only the fix, for that one case") is deleted,
      not reworded. Checked.
    - `sq check`'s own view-scan message is deliberately **not** folded into this predicate, and
      that is right: it reports a *present* unresolvable tag, which is a different question from
      what explains an *empty* body. My recommendation named three call sites; two of them are the
      same question and the third is not. Correctly split.
<!-- sq:finding:F19:discussion:end -->
<!-- sq:finding:F19:end -->

<!-- sq:finding:F20 -->
### F20 — sq migrate up exits 1 on an unreadable file without naming it

<!-- sq:finding:F20:body -->
**Driven.** F15's fix wired the `skipped` channel into `sq migrate up`'s output and mirrored
`sq repair`'s exit code. The exit condition is `run.repair.unreadable or run.repair.skipped`;
the output loop covers `skipped` only. So an `unreadable` file makes the command exit 1 while
naming nothing at all.

    $ sq migrate up
      0.14.0 (schema v0.11→v0.14): Two new bundled item types, contract (PRD) …
    migrated to schema v0.14; index rebuilt — run `sq sync` to refresh managed files
    manual steps remain — read them with `sq migrate chlog v0.15.0..v0.15.0`
    $ sq migrate up >/dev/null 2>&1; echo $?          # after resetting the stamp
    1

Nothing in that output mentions the malformed file. `sq repair` on the identical corpus names
it: `error: TASK-000999-broken.md: malformed frontmatter in … — its previous index entry, if
any, was carried forward as-is; fix the file and repair again`, exit 1.

Before this change the same corpus was silent and exited 0. It is now silent and exits 1 —
better for a script, worse for an operator, who gets a green `migrated` line and a failure with
no stated cause. The command's own docstring names `unreadable` as an exit reason, so the gap is
between the docstring and the output, not between the docstring and the code.

The finding text this fix answered said the quiet part out loud: "`unreadable` is unreported
there too, which predates this change; the new channel simply inherited the hole rather than
being asked about it." The fix took `unreadable` into the exit code without taking it into the
report, which is the one combination that leaves an operator with a failure and no sentence.

Closure: the same loop `sq repair` already has, with the same wording, beside the `skipped` loop
this fix added — four lines, and then the exit code and the output cover the same set.
<!-- sq:finding:F20:body:end -->

#### Discussion

<!-- sq:finding:F20:discussion -->
- [2026-09-10T08:17:21Z] Paul Reviewer:
  - - Verified driven, bare. Corpus below the current schema stamp with one malformed item file:
      `sq migrate up` now prints
      `error: TASK-000999-broken.md: malformed frontmatter in … — its previous index entry, if any,
      was carried forward as-is; fix the file and repair again`, and exits **1**. The wording is
      `sq repair`'s own, pinned once in the parity test rather than retyped.
    - So the combination this finding was about — a failing exit with no stated cause — is gone:
      the exit condition and the output now cover the same set, and the code comment that used to
      justify the asymmetry is replaced by one that states the new invariant.
    - Re-checked `sq repair`'s own exit contract **bare** rather than through a pipeline (a pipe
      reports the last element's status and I nearly recorded a false 0 from one here): `sq repair`
      on the same corpus exits 1. Parity holds in both directions.
<!-- sq:finding:F20:discussion:end -->
<!-- sq:finding:F20:end -->

<!-- sq:finding:F21 -->
### F21 — The drift trigger orders a prerelease above its own release

<!-- sq:finding:F21:body -->
**Driven on the comparator, inferred on the harm.** F14 put `squads._util.version_tuple` on the
version-drift trigger that F1's whole recovery depends on. That function strips non-digits *per
segment and concatenates the survivors*, so a prerelease suffix does not sort below its release
— it sorts above it, and equal to the next patch:

    version_tuple("0.15.0")      -> (0, 15, 0)
    version_tuple("0.15.0rc1")   -> (0, 15, 1)      # "0rc1" -> "01" -> 1
    version_tuple("0.15.1")      -> (0, 15, 1)      # identical to the rc
    version_tuple("0.15.0") > version_tuple("0.15.0rc1")   -> False

Consequences for the trigger `if version_tuple(__version__) > version_tuple(recorded_version)`:

- A squad whose `.squads.toml` was stamped by a `0.15.0rc1` build reads as **not drifted** when
  the final `0.15.0` is installed, and **not drifted** again when `0.15.1` lands. Any future
  release that ships a roster body-tag backfill the way `0.15.0` did would silently not run it
  on that squad — F1's exact failure signature (definitions do not render, `sq check` clean,
  `sq sync` reports success), for anyone who ever ran a prerelease.
- `.devN` and local versions are fine — `version_tuple("0.15.0.dev1") == (0, 15, 0, 1)`, which
  orders above `0.15.0` and is harmless because the backfill is idempotent.

This is `version_tuple`'s pre-existing behaviour and it is shared with `version_notice`, so the
two comparators now agree — which was F14's acceptance criterion and is genuinely met. The
finding is that agreement was the wrong target on its own: F14 traded a loud `ValueError` for a
quiet wrong answer in an adjacent shape, and the shape it is wrong for is the one this project
itself produces (release candidates are cut here; `_stamp_version` writes `__version__`
verbatim).

Closure: the second option F14's own text named. Treat a stamp the strict parser cannot read as
**drift** rather than as a version to order — the backfill is idempotent and its own comment
notes the comparison is the only cost on a no-drift run, so over-triggering is cheap and
under-triggering is F1. Keep the tolerant comparator for the *notice* (a cosmetic decision) and
give the *trigger* the fail-safe direction. If the ordering itself is worth fixing instead,
`version_tuple` should split the suffix off rather than concatenate its digits — but that
changes a shared helper and wants its own item.

Low: reachable only through a prerelease install, and the damage needs a *later* release to add
a backfill. Filed because it sits directly on the mechanism F1 exists to guarantee.
<!-- sq:finding:F21:body:end -->

#### Discussion

<!-- sq:finding:F21:discussion -->
- [2026-09-10T08:19:37Z] Paul Reviewer:
  - - Verified. The fix replaces the comparator choice with a named predicate,
      `squads._models._schema.version_drifted(current, recorded)`, that is strict
      (`schema_tuple`, per-segment `int`) and treats an unparseable stamp as **drift** rather than
      as an ordering. Driven matrix, direct calls:
    
          ('0.15.0','0.14.0')       -> True     newer
          ('0.15.0','0.15.0')       -> False    equal
          ('0.15.0','0.16.0')       -> False    lower current (no spurious drift)
          ('0.9.0','0.10.0')        -> False    numeric, not lexicographic
          ('0.10.0','0.9.0')        -> True     same, other direction
          ('0.15.0','0.14.0rc1')    -> True     the recorded-side prerelease this finding was about
          ('0.15.1','0.15.0rc1')    -> True     and the next patch after it
          ('0.15.0','')             -> True     an empty/legacy stamp triggers rather than skips
          ('0.15.0','garbage')      -> True
    
      Every answer this finding turned on is now right, including the two the tolerant comparator got
      backwards (`'0.15.0'` vs `'0.15.0rc1'`, `'0.15.1'` vs `'0.15.0rc1'`), and the empty-stamp case
      which fails safe rather than silently skipping the one convergence step a squad recovers
      through.
    
    - **The one behaviour to reason about, and it is sound.** A prerelease on the *current* side
      raises too, so `version_drifted('0.15.0rc1','0.15.0rc1')` is `True`: on a prerelease or `.devN`
      install the trigger is permanently true and `sync()` runs the backfill on every invocation.
      That is over-triggering an idempotent step, which the docstring owns explicitly. It matters
      more than the cost, though, and this is the part I checked rather than assumed: the *same*
      predicate computes `empty_body_hint_state`'s `drift_outstanding`, so on such an install the
      hint stays in state "declared, drift outstanding — run `sq sync`" *and that sentence is true*,
      because the always-running backfill really does populate the body. Had the hint kept its own
      comparison, this is precisely where the two would have disagreed and re-opened F19. One
      predicate, two callers, no disagreement possible.
    
    - The deliberate divergence from `version_notice()` is stated in place and I agree with it: a
      prerelease stamp now makes `sync` see drift while the cosmetic notice does not, and the comment
      says so and says why ("the two are not required to agree on that field"). That is the opposite
      of F14's failure, which was an *accidental* disagreement nobody had written down.
    
    - **The class check behind this fix was taken over an incomplete enumeration** — four
      `version_tuple` call-site regions besides the notice, not two, and the copy the handback called
      "cosmetic-only" is the one behind `sq migrate chlog`'s range filter. Filed as F22 (a driven,
      end-to-end suppression of a migration's manual steps) and F24 (the duplicated comparator, and
      why it is the mechanical reason the enumeration went short). F21 itself stands Verified — those
      are separate sites, not this fix being wrong.
<!-- sq:finding:F21:discussion:end -->
<!-- sq:finding:F21:end -->

<!-- sq:finding:F22 -->
### F22 — chlog drops a migration's manual steps on a prerelease bound

<!-- sq:finding:F22:body -->
**Driven, end to end, and the command that suppresses the steps is the one squads itself tells
the operator to run.**

F21 moved the version-drift *trigger* onto the strict, fail-safe `version_drifted`. The
`sq migrate chlog` range filter was left on the tolerant `version_tuple`, classified in the fix
handback as "read-only/informational (a listing) — neither silently skips a mutation, so
neither inherits F21's harm". It does not skip a mutation. It silently skips a **manual
migration step the operator was just told to read**, which is the one thing squads cannot do on
their behalf.

The filter is `version_tuple(lo) < version_tuple(m.version) <= version_tuple(hi)`
(`_cli/_migrate.py:135`), and the comparator inflates a prerelease segment above its own
release:

    version_tuple("0.14.0rc1") -> (0, 14, 1)      # "0rc1" -> "01" -> 1
    version_tuple("0.14.0")    -> (0, 14, 0)

Reproduction, on a squad stamped by a prerelease build and then migrated by the release:

    $ grep -E 'schema_version|squads_version' .squads.toml
    schema_version = "0.11"
    squads_version = "0.14.0rc1"
    $ sq migrate up
      0.14.0 (schema v0.11 -> v0.14): Two new bundled item types, contract (PRD) and milestone …
    migrated to schema v0.14; index rebuilt — run `sq sync` to refresh managed files
    manual steps remain — read them with `sq migrate chlog v0.14.0rc1..v0.15.0`
    $ sq migrate chlog v0.14.0rc1..v0.15.0
    no manual steps for v0.14.0rc1..v0.15.0

    $ sq migrate chlog v0.13.1..v0.15.0        # the truthful window, control
    v0.14.0 — manual steps (schema v0.11 -> v0.14)   … (the steps print)

`migrate up` builds that span itself — `span = f"v{svc.paths.config.squads_version}..v{__version__}"`
— from the stamp `_stamp_version` wrote verbatim, so the operator is pointed at exactly the
window the comparator empties. "Manual steps remain" and "no manual steps" for the same
migration, one line apart. Reachable by anyone who ran a prerelease or `.devN` build before
upgrading; every version this project has *shipped* is clean, so it is not reachable from
release-to-release use alone.

**And the class check behind the "both are informational" argument was taken over an incomplete
enumeration.** `version_tuple` has four call-site regions besides the drift notice, not two:

    _cli/_migrate.py:135              chlog range filter          (named — this finding)
    _overrides/_service.py:757,758,768  uncarried-base pane + floor compare  (named)
    _overrides/_manifest.py:214       artifact_floor: min(candidates, key=version_tuple)   (NOT named)
    _overrides/_manifest.py:219       known_index_versions: sorted(…, key=version_tuple)   (NOT named)

The two unnamed ones are in the override-provenance path. `artifact_floor` is not a label: it
*selects* which stored revision an override's Δ-upgrade pane anchors on, and `min` over a
mis-ordering key gives a silently wrong answer rather than a visible failure — the same
character as F21. Not currently reproducible (every key in `templates_manifest.json` today is a
clean `X.Y.Z`), and the exposure needs a manifest regenerated during a prerelease, which the
release runbook's own manifest gotcha makes a live possibility. `known_index_versions` has no
`src/` caller at all (only `tests/meta`), which is presumably why nobody looked at it.

**Closure.** The rule this release has been converging on is: a comparison whose *answer gates
what the operator is shown or given* uses the strict fail-safe form; only a cosmetic notice may
be tolerant. On that rule the chlog filter belongs on a strict comparator — and a range filter
wants a real ordering, not a fail-safe boolean, so this is the one site where the right answer
is probably to make the comparator itself correct (split the suffix off a segment instead of
concatenating its digits) rather than to swap which one is called. That single change also fixes
the two override-provenance sites, and it is testable directly: `version_tuple("0.14.0rc1")`
must order below `version_tuple("0.14.0")`.
<!-- sq:finding:F22:body:end -->

#### Discussion

<!-- sq:finding:F22:discussion -->
<!-- sq:finding:F22:discussion:end -->
<!-- sq:finding:F22:end -->

<!-- sq:finding:F23 -->
### F23 — sq adopt reports neither repair channel and exits 0

<!-- sq:finding:F23:body -->
**Driven.** `sq adopt` is the **fourth** CLI consumer of the same corpus-rebuild result the
repair corridor is about, and it reads `result.repair.strip_notice()` and nothing else —
verbatim the shape F15 reported on `sq migrate up`. The new parity test covers three commands
(`repair`, `migrate up`, `sync`); this one is outside the table, and it has the defect.

    src/squads/_cli/_main.py   (adopt)   notice = result.repair.strip_notice()
    src/squads/_services/_service.py:246 repair_result = await svc.repair()
    src/squads/_services/_results.py:187 repair: RepairResult   # carried on AdoptResult

**Reproduction 1 — the `unreadable` channel.** A squads-structured folder with one malformed
item file, adopted:

    $ sq adopt --roles minimal
    ╭─ squads adopted ─╮  imported: 13 existing item(s)  ╰──╯
    Migrate legacy docs with `sq --at <date> create …` … then `sq check`.
    $ sq adopt --roles minimal >/dev/null 2>&1; echo $?
    0
    $ sq repair                       # the identical corpus, the reference command
    error: TASK-000999-broken.md: malformed frontmatter in … — its previous index entry, if any,
      was carried forward as-is; fix the file and repair again
    $ sq repair >/dev/null 2>&1; echo $?
    1

**Reproduction 2 — the `skipped` channel, and this is the one that matters.** The same folder
with the manager role's `sq:body` holding marker-shaped content the convergence guard refuses:

    $ sq adopt --roles minimal        # nothing about it; bare exit 0
    $ sq check                        # exit 0, no finding about it
    $ sq role manager show | tail -2
    legacy x                          # the stale content, not the role definition
    $ sq repair                       # the identical corpus
    error: skipped ROLE-1: repair backfill: expected an empty, already-tagged, or plain
      legacy-rendered sq:body for 'role_definition', found marker-shaped content … — this region
      was left untouched; fix the file by hand and repair again
    $ sq repair >/dev/null 2>&1; echo $?
    1

Every surface an operator would look at reports clean. `sq check` structurally cannot see this
state (that is F13's own finding), and `adopt`'s closing line names `sq check` — the one command
that does not report it — rather than `sq repair`, which does. The visible outcome is that the
adopted squad's manager agent boots on `legacy x` instead of its role definition, which is F1's
original signature reached through a route nobody swept.

**Why this route rather than another.** `adopt`'s own comment states the case for reporting
there: *"The import sweep is also the corpus sweep, and this is the only route an existing folder
of squads-native markdown takes — no schema stamp to migrate, no repair anyone ran."* That is
exactly right, and it is the argument for printing both channels, not only `strip_notice()`. It
is also the population most likely to be in this state: the corpus is someone else's, and
nothing has ever swept it.

**Severity, argued rather than assumed.** F15 and F20 were the same shape at low. This is medium
because nothing downstream catches it (`sq check` cannot, and the command's own closing advice
points at `sq check`), because it is first contact with an unswept corpus, and because the
observable result is an agent running on the wrong text with a clean bill of health.

**Closure**: the two loops `sq repair` already has, with the wording the parity test already
pins, plus a decision on `adopt`'s exit code. And the parity table gains a fourth row — see the
note on the enumeration finding: this consumer was missed because family B's closure is a
hand-picked list of commands rather than an enumeration of the result object's consumers.
<!-- sq:finding:F23:body:end -->

#### Discussion

<!-- sq:finding:F23:discussion -->
- [2026-09-10T09:02:40Z] Paul Reviewer:
  - - Verified driven, both channels, bare exit, on the shipped build. A squads-structured folder
      copied out of a real squad with `.squads.json`/`.squads.toml` removed, then adopted:
      - **unreadable**: one malformed item file -> `sq adopt` prints
        `error: TASK-000999-broken.md: malformed frontmatter in … — its previous index entry, if
        any, was carried forward as-is; fix the file and repair again`, bare exit **1**.
      - **skipped**: the manager role's `sq:body` holding marker-shaped content -> `sq adopt` prints
        `error: skipped ROLE-1: … — this region was left untouched; fix the file by hand and repair
        again`, bare exit **1**. This is the case nothing downstream could catch (`sq check`
        structurally cannot see it), and it is the one that mattered.
      - Both messages are `sq repair`'s own wording, and the generic closing hint is correctly
        **suppressed** on the failing path (driven: 0 occurrences of `Migrate legacy docs …` in that
        run) — my finding noted the old closing line pointed at `sq check`, the one command that
        cannot report this. The `raise typer.Exit(1)` sits before it with that reason stated.
    
    - **Family B is now enumerated rather than listed, and the enumeration paid for itself on its
      first run** — it discovered **five** sites where four had been hand-listed, surfacing
      `renumber` as a false-positive-by-name (`RenumberResult.strip_notice()` shares a method name
      with `RepairResult`) and classifying it `not-a-reporting-site` with the reason, rather than
      filtering it out by guessed type. That is the right call: filtering by guessed type is what let
      the fourth consumer go unnoticed. `test_no_site_is_classified_reports_neither_channel` making
      the defect label unrepresentable-as-a-resting-state is a good addition nobody asked for.
    
    - **But the discovery can be evaded, in the most on-point shape — filed as F26.** The scan keys
      on *reading a channel attribute*; the defect class is *consuming the sweep without reporting
      it*. `sq adopt` was only discovered because it happened to read `result.repair`. Driven against
      the module's own `_sites_in_module`, control validated first:
    
          FOUND   reads .unreadable                                  (known positive)
          FOUND   calls svc.repair(), reads nothing                   (only because `repair` doubles
                                                                      as a channel field name)
          MISSED  calls svc.sync(), reads nothing
          MISSED  calls svc.run_pending_migrations(), reads nothing
          MISSED  calls svc_adopt(...), reads nothing
          MISSED  reads a channel via getattr / dataclasses.asdict
    
      A sixth CLI command that calls `svc.sync()` or `svc.run_pending_migrations()` and reports
      nothing is exactly `reports-neither-channel` — the state the table declares must never
      exist — and is invisible. Had the real `adopt` discarded its result instead of reading
      `.repair`, this scan would have missed the very defect it was built for.
- [2026-09-10T09:33:05Z] Paul Reviewer:
  - - **The corridor widening closes all three shapes I drove as MISSED, and nothing was hiding behind
      it.** Driven against the module's own `_sites_in_module`, with the known positive confirmed first
      and a negative control confirmed last:
    
          FOUND   reads .unreadable                          (known positive)
          FOUND   svc.sync(), reads nothing                  (was MISSED)
          FOUND   svc.run_pending_migrations(), reads nothing (was MISSED)
          FOUND   svc_adopt(...), reads nothing              (was MISSED)
          MISSED  getattr(result, name)                      (documented as not closed)
          MISSED  asdict(result)['skipped']                  (documented as not closed)
          MISSED  unrelated code                             (negative control)
    
      The real `_cli/` corpus still resolves to exactly the five classified sites — `repair`,
      `migrate_up`, `sync`, `adopt`, `renumber` — so the widened filter surfaced no sixth consumer
      that had been hiding, and produced no new false positive to explain away.
    
    - The two remaining shapes are **declared, not glossed**: the module docstring names
      `getattr(result, …)`/`dataclasses.asdict(result)` as still invisible and says why (an AST walk
      matching `ast.Attribute` plus a fixed producer-name set cannot see a dynamic read). That is the
      right disposition — a stated limit rather than a silent one.
    
    - The docstring also records the thing worth remembering about how this was found: keying on
      *reading a channel* rather than *consuming the sweep* is why `adopt` was caught only by the
      coincidence that `repair` doubles as a producer name and a channel-ish field name, and that both
      scans were written in the same commit while only one learned the bare-name lesson the first time.
    
    - **`reports-both-channels` -> `reports-every-channel` is done**, and the rename does what it was
      meant to: `sync`'s reason string now *clarifies* the one-channel case ("'every channel' here
      means the complete channel set this result type exposes, which is the single one sync prints")
      instead of apologising for a label that said "both". My read last round was that the reason was
      honest and the label's name was the imprecise part; renaming was the whole fix and it landed.
<!-- sq:finding:F23:discussion:end -->
<!-- sq:finding:F23:end -->

<!-- sq:finding:F24 -->
### F24 — A duplicated version_tuple feeds chlog, not only the notice

<!-- sq:finding:F24:body -->
**Read.** Filed rather than agreed as a cleanup, because the reason given for deferring it is
factually wrong and the duplicate is load-bearing.

`_cli/_common.py:1386` defines `version_tuple` with a body byte-identical to
`squads._util.version_tuple` (same loop, same semantics; only the docstring is absent). The fix
handback routed it as "dup, feeds only the cosmetic notice — flagging as a cleanup candidate".
It does not feed only the notice:

    src/squads/_cli/_migrate.py:17-23   from squads._cli._common import (…, version_tuple,)
    src/squads/_cli/_migrate.py:135     version_tuple(lo) < version_tuple(m.version) <= version_tuple(hi)

So the copy in `_cli/_common.py` is the comparator behind `sq migrate chlog`'s range filter —
the site that silently drops a migration's manual steps on a prerelease bound (filed
separately). Two statements in the same handback contradict each other: chlog is named as a
`version_tuple` caller, and the `_cli/_common.py` copy is described as feeding only the notice.
Whichever was intended, the copy is not cosmetic-only.

**Three implementations, two semantics, and that is how the enumeration went short.** The
version-comparison surface is now:

    squads._util.version_tuple            tolerant   -> _overrides/_service.py, _overrides/_manifest.py
    squads._cli._common.version_tuple     tolerant   -> version_notice(), _cli/_migrate.py chlog
    squads._models._schema.schema_tuple   strict     -> migrate up's schema stop, check's notice, registry
    squads._models._schema.version_drifted  strict+fail-safe -> sync's trigger, both empty-body hints

"Grep who compares versions" therefore returns a different answer depending on which name you
grep, and a grep for `from squads._util import version_tuple` — the natural one — misses the
`_cli` consumers entirely. That is the mechanical reason the class check behind this round's
F21 fix enumerated two callers where there are four.

**This project has already ruled on this defect class.**
`tests/meta/test_sq_marker_recognition_has_one_case_blind_definition.py` exists because a
marker regex survived in two places — "so fixing the one that showed up in a report would have
left the other blind" — and its guard now refuses a second copy by name. A duplicated version
comparator is the same shape one primitive over, and the last two rounds produced two separate
findings (a bare `ValueError`, then a wrong-direction comparison) that both turned on *which
comparator a call site happened to use*.

**Closure**: delete `_cli/_common.py`'s copy and import `squads._util.version_tuple` (`_util`
is dependency-free, so there is no layering objection), then let the comparator-choice rule be
checkable in one place. Whether the tolerant one should keep any *gating* caller at all is the
separate question the chlog finding raises.
<!-- sq:finding:F24:body:end -->

#### Discussion

<!-- sq:finding:F24:discussion -->
<!-- sq:finding:F24:discussion:end -->
<!-- sq:finding:F24:end -->

<!-- sq:finding:F25 -->
### F25 — The view-tag enumeration is narrower than its completeness claim

<!-- sq:finding:F25:body -->
**Driven, in an isolated `git worktree` at HEAD, never in the live tree.** The new enumeration
guard is the right mechanism and it works — reverting F17's gate reddens exactly one row, naming
the writer and its gate targets. Three gaps between what it *claims* and what it *checks*, each
demonstrated against a constructed positive.

**1. The discovery filter matches only attribute-style calls.** It requires
`ast.Call` whose `func` is an `ast.Attribute` with `attr == "view_tag"`. A bare-name call —
`from squads._models._markers import view_tag`, then `view_tag(name)` (an `ast.Name`) — is
invisible. Added a seventh writer in that style to `_services/_rename.py` in the worktree:

    return text.replace("PLACEHOLDER", markers.open_marker(view_tag(name)))

All six tests pass. So the dict's completeness claim — "a seventh writer cannot be added without
classification" — does not hold for that shape. Mitigating and worth stating: all 16 modules
that use `_markers` today import it as `from squads._models import _markers as markers`, so the
bare form is a convention break — but nothing enforces that convention, and this test is what
stands in for enforcement. Closure is one clause: also match `ast.Name` with `id == "view_tag"`.

**2. A template literal is invisible by construction, and one such writer exists today.** The
scan globs `*.py`. `templates/agents/role.md.j2:2` is a literal `sq:view:role_definition` placement tag (written here without its HTML-comment wrapper) —
the third writer `ROLE_DEFINITION_VIEW_NAME`'s own docstring points at, and the one the module
docstring says this sweep exists to account for. It is not a key in `CLASSIFICATIONS` and cannot
become one. It is not a live defect (F12 established `_create_core` overwrites that region
unconditionally for a role), but a *second* template writer would be silent. Driven, in the
worktree: adding a static tag inside `agents/skill.md.j2`'s `sq:body` region leaves all six
tests green, and the tag then survives into every created skill — nothing overwrites a skill's
body region the way `_create_core` does a role's:

    $ sq skill add my-runbook --desc "an authored runbook"
    $ sed -n '/sq:body/,/sq:body:end/p' squads/agents/skills/SKILL-…-my-runbook.md
    (the sq:body open marker)
    (a sq:view:milestone_rollup tag)      # the template's static tag, live

Same through the supported adopter surface, driven on the shipped build with an undeclared name
in `.overrides/templates/agents/skill.md.j2`:

    error SKILL-000014-my-runbook.md: no declared view 'no_such_view' with a resolvable
      presentation template …            # sq check exit 3

An adopter authoring that tag is arguably placing it themselves, so this is not F17's
culpability — but the family is "every writer of a placement tag is classified", and the
template writer class is outside the sweep. Closure: a second scan over
`_rendering/templates/**` for `sq:view:`, with the one bundled site classified and a reason
(e.g. `neutralized-by-overwrite`, citing `_create_core`).

**3. The gate half is a text proxy a plausible refactor satisfies.**
`test_a_gated_sites_declared_target_actually_carries_a_views_gate` searches
`inspect.getsource(target)` for `\bin\s+(?:self\s*\.\s*)?spec\s*\.\s*views\b`. That proves a
`spec.views` mention exists somewhere in the declared target, not that it guards the seed.
Driven: with the three real gates removed and one *unused* mention added to each target —

    _declared = [n for n in interactions.SYSTEM_SKILL_VIEW_NAMES.values() if n in spec.views]
    _decl = interactions.ITEM_SKILL_VIEW_NAME in spec.views

— and `body_tag=view_name` / `body_tag=interactions.ITEM_SKILL_VIEW_NAME` fully restored, **all
six tests pass**. That shape is not adversarial: a function that computes a declared-views list
for one purpose while seeding a tag for another is ordinary growth in this file.

**What saves it today, and where the residual actually is.** The same commit's behavioural test
(`test_skill_creation_seeds_no_tag_for_an_undeclared_view.py`) *does* catch the decoy build —
three rows red, including the finding-count growth assertion. So the existing sites are closed by
behaviour, not merely by label, and the proxy weakness bites only a *future* site, which will have
no behavioural test of its own yet. Closure worth considering: have a `gated` classification
require a named behavioural test alongside its reason, so adding a site to the dict costs a
driven test rather than a sentence.

Low: none of the three is a live product defect. Filed because this guard is the thing standing
between the next writer and three more review rounds, and its claim should be as wide as its
docstring says it is.
<!-- sq:finding:F25:body:end -->

#### Discussion

<!-- sq:finding:F25:discussion -->
- [2026-09-10T09:03:01Z] Paul Reviewer:
  - - **All three gaps this finding named are closed, and each closure carries a fixture that
      reproduces my own probe rather than a claim that it was considered.**
    
    - **Gap 1 — bare-name calls.** `_collect_view_tag_calls` now matches `ast.Name` with
      `id == "view_tag"` alongside the attribute form, and
      `test_a_bare_name_view_tag_call_is_discovered_too` drives it **through the production
      scanner**, not a reimplementation, so the test cannot pass unless the scanner itself is
      widened. That is the right shape.
    
    - **Gap 2 — template literals.** A second scan over `_rendering/templates/**/*.j2` with a
      whitespace-tolerant regex, its own false-zero validation against a wrapped tag, its own
      completeness dict, and `agents/role.md.j2` classified `neutralized-by-overwrite` with a reason
      that states the mechanism I verified in F12 (unconditional overwrite; `pristine_body`
      unreachable for a role because `set_body` raises first). `test_a_second_template_writer_is_
      caught_unclassified` reproduces my `agents/skill.md.j2` probe **against a copied fixture tree**
      and adds a regression control asserting the real bundled corpus still has exactly its one
      classified hit — so the probe cannot leave the shipped templates perturbed.
    
    - **Gap 3 — the gameable source-text regex. Reproduced the claim myself and it holds.** In an
      isolated worktree at HEAD I reverted all three real gates (`_create_core`'s conditional,
      `_repair_body_tag`'s three `spec.views` returns, both `_write_managed_skill` caller gates) and
      added one *unused* `in spec.views` mention to each target — the exact decoy that defeated the
      old regex:
    
          meta module                     12 passed        (it no longer inspects source text)
          the three cited behavioural tests  3 failed       (one per gated site)
    
      So the module now claims exactly what it checks, and the proving genuinely moved to the tests
      it names — each of the three reddens when its own site's gate goes. The old regex claimed a
      gate was sound and could not tell a gate from a mention; this claims a citation resolves and
      says in its own docstring that it proves nothing more. That is the property this finding said
      was missing.
    
    - **One level further out, the citation itself can be honest-looking and useless — filed as
      F26.** `_cited_test_exists` checks a file exists and a top-level function of that name exists
      in it. Driven, with the gates still reverted: re-pointing `_write_managed_skill`'s citation at
      `test_a_newly_created_per_type_skill_under_a_declared_view_still_seeds_the_tag` — a real,
      top-level, currently-passing test **in the very file the citation already names**, whose name
      reads as though it is about the declared-view gate — leaves the meta module at **12 passed**
      while that test passes with the gate broken, because it asserts the *declared*-view direction
      an ungated writer satisfies too. No test body edited. Separately: a `@pytest.mark.skip` on the
      real cited test also leaves the module at 12 passed with the cited test reporting `1 skipped`.
      Details and closure on F26.
    
    - F25 stands **Verified** on its own terms: the three gaps it named are gone. F26 is the new,
      narrower gap in the replacement mechanism, not this one left open.
<!-- sq:finding:F25:discussion:end -->
<!-- sq:finding:F25:end -->

<!-- sq:finding:F26 -->
### F26 — A gated site's behavioural-test citation can resolve while proving nothing

<!-- sq:finding:F26:body -->
**Driven, in an isolated worktree at HEAD which I then removed.** F25's gate-verification gap is
genuinely closed: the source-text regex is gone, the meta module stays green on a decoy build
because it no longer looks at source text, and the three cited behavioural tests each redden
when their own site's gate is reverted. The proving moved to the citations. The citations are
where the residual now lives, and it is the same shape one level out: a citation can satisfy the
existence check while proving nothing, and reaching that state needs no edit to any test body.

`_cited_test_exists` resolves `"tests/…/file.py::test_name"` by checking that the file exists and
that a top-level `FunctionDef`/`AsyncFunctionDef` of that name appears in `tree.body`. Three
things that check cannot see, each driven with the three real gates reverted:

**1. A citation re-pointed at a passing sibling in the same file.** The sharpest case, because
the substitute is neither synthetic nor implausible:

    ("squads/_backends/…/_backend.py", "_write_managed_skill"):
      "tests/service/test_skill_creation_seeds_no_tag_for_an_undeclared_view.py"
      "::test_a_newly_created_per_type_skill_under_a_declared_view_still_seeds_the_tag"

    meta module                12 passed
    the cited test              1 passed      (with the gate broken)

That function is real, top-level, in the very file the citation already names, written by the
same commit as its regression control — and its name reads as though it is about the
declared-view gate. It passes with the gate removed because it asserts the *declared*-view
direction, which an ungated writer satisfies too. So the guard is green, the citation is
honest-looking, and nothing proves the gate.

**2. A `skip` marker on the real cited test.** Decorators are invisible to an `ast.FunctionDef`
name lookup:

    @pytest.mark.skip(reason="flaky in CI, re-enable later")
    async def test_repeated_skill_creation_under_a_dropped_view_adds_no_check_findings(...)

    meta module                12 passed
    the cited test              1 skipped     (with the gate broken)

This is the one that happens by accident rather than by mistake — a test goes flaky, someone
skips it, and a `gated` classification silently stops being backed by anything. `skipif` and
`xfail` behave the same, as would a citation into a module the `slow` collection hook excludes
by default.

**3. The citation requirement's own scope is self-declared.** `test_every_gated_site_has_exactly_
one_behavioural_test_citation` requires a citation only for sites labelled `gated`. Relabelling
`_write_managed_skill` to `not-a-writer` with a plausible reason and deleting its citation
leaves the module at **11 passed**, gate still broken — one fewer test collected, zero failures.
The three non-`gated` labels carry no behavioural obligation at all, so the same self-declaration
weakness the old regex had for *the gate* now applies to *which sites need proving*. Least likely
of the three (it takes typing a false sentence), but it means the scope is an assertion, not a
check.

**Closure, and it is cheap and mechanical for the two that matter.** Invert the direction of the
citation so it cannot drift: mark the behavioural test with the site it proves —
`@pytest.mark.gate_for("squads/_backends/_claude_code/_backend.py::_write_managed_skill")` — and
have the meta test build the map by collecting those markers instead of reading a
hand-maintained dict. A citation then cannot point at an arbitrary test, because the test itself
declares what it proves; re-pointing means editing the test that would then be making a false
claim in its own source. Add one condition alongside it: reject a cited test carrying
`skip`/`skipif`/`xfail`, or living in a module the default collection excludes — "collected and
live" is checkable without executing anything, and closes (2) outright.

What would remain after that, and should be stated rather than closed: whether the cited test's
*assertions* actually falsify the gate is only knowable by mutating the gate and running it —
mutation testing, not a unit test. The dict's comment already records that this was driven once
per site when each citation was written, which is the right place for it. The gap is that nothing
keeps the citation attached to that recorded event; a marker on the test does.

Low: no product defect, and all three real citations today are correct — I reverted each gate and
watched each cited test redden. Filed because this guard is now the load-bearing thing between
the next writer and another review round, and its own claim should not be satisfiable by a
citation that proves nothing.
<!-- sq:finding:F26:body:end -->

#### Discussion

<!-- sq:finding:F26:discussion -->
- [2026-09-10T09:32:49Z] Paul Reviewer:
  - **Verified. All three drives are closed, each reproduced against the real corpus rather than the
    fixture that ships with the fix.** Driven in an isolated worktree at HEAD with all three real
    gates reverted, restored and removed afterwards.
    
    - **Drive 1 (re-pointing) — refused, on my exact edit.** I added
      `@pytest.mark.gate_for("squads/_backends/_claude_code/_backend.py::_write_managed_skill")` to
      the real sibling `test_a_newly_created_per_type_skill_under_a_declared_view_still_seeds_the_tag`
      — the same uninvolved, currently-passing test my original drive re-pointed at — and
      `test_every_gated_site_has_exactly_one_behavioural_test_citation` failed, naming both claimants
      by full `path::name`. Not a naive double-marker on a synthetic fixture: my sibling, my site, in
      the real file.
    - **Drive 2 (the `skip` form) — refused, and the exclusion set is right.** Unit-drove all five
      shapes through `_gate_for_sites_in_module`: `skip(reason=…)`, `skipif(…)`, `xfail` and `slow`
      all flag `excluded=True`; `usefixtures` (a marker that does *not* suppress collection) flags
      `False`. So the check keys on suppression, not on "has a marker" — and extending it to `slow`
      beyond my drive is correct, since that is this repo's one default-collection exclusion and a
      citation into a slow module would have been the same hole with a different label.
    - **Drive 3 (self-declared scope) — structurally gone.** `GATED_BEHAVIOURAL_TESTS` and
      `_cited_test_exists` are both absent from the tree (grep validated against a known positive:
      `_gate_for_sites` resolves). The map is collected from markers, so a citation cannot exist
      without a test claiming the job, and the `extra` check refuses a marker naming a site that is
      not `gated`. The label can still be changed, but changing it now *removes* a real marker's
      target and trips `extra` rather than silently dropping an obligation.
    - **F25 re-verified under the new mechanism, not assumed to have survived it:** three gates
      reverted -> meta module **13 passed**, all three cited tests **red**. So the module still claims
      exactly what it checks and the proving is still where it was moved to.
    
    **On the residual the guard now declares about itself — accurate on substance, with one clause
    overstated and one mitigation understated. Both are wording, and neither is a defect in
    behaviour.**
    
    - *"a genuine swap … is undetectable statically"* — **true, driven.** Removing the marker from the
      true owner and putting it on the uninvolved sibling leaves exactly one claimant: meta module
      **13 passed**, and the falsely-cited test **passes** with the gate broken.
    - *"whether the cited test's assertions actually falsify is only knowable by mutating the gate"* —
      **true, and the honest boundary.** No static check can make that claim, and saying so is the
      right thing to do rather than approximating it. This is the inverse of what F25 was, and it
      holds where it matters.
    - *"the marker keeps the citation attached to that recorded event; it does not repeat the proof"* —
      **this clause reads stronger than the mechanism.** Driven: keep the marker and the function
      name, gut the cited test's body to `assert svc is not None` -> meta module **13 passed** and the
      "prover" **passes** with the gate broken. The marker keeps the *claim* co-located with a *test*;
      nothing binds it to the driven mutation event, which lives only in prose in the commit that
      wrote it. The substance is already disclaimed by the sentence immediately before it, so the
      comment does not mislead about what is checked — but "attached to that recorded event" asserts a
      binding that does not exist. Worth one word's edit next time this file is open, not a round.
    - **Understated, in the guard's favour: the swap costs *attribution*, not *detection*.** Driven in
      the same run — after the marker is moved, the real prover is still present, still collected, and
      still fails on the broken gate (3 failed in that module). So a broken gate still reddens the
      suite; what a swap breaks is the guard's ability to say *which* test proves the site. That is a
      materially narrower residual than "undetectable" reads, and stating it would make the boundary
      both more accurate and less alarming than it currently sounds.
    
    **Marker registration changes nothing about collection.** `gate_for(site)` is declared in
    `[tool.pytest.ini_options].markers` with a real help string; the `slow` collection hook keys on
    `"slow" in item.keywords` and never sees `gate_for`; there is no `--strict-markers` or
    warnings-as-errors setting that the marker interacts with. Driven: the two meta modules plus the
    three cited modules under `-W error::pytest.PytestUnknownMarkWarning` -> **34 passed**, no
    warning raised.
    
    **Why I am not filing the wording as a finding**, stated so the call is auditable rather than
    convenient: the false-claim findings I filed earlier in this review (F11's derivation docstring,
    F19's hint comment) were *load-bearing* — one justified a derivation, the other told an operator to
    run a command that could not help. This clause sits in a test-module comment, its substance is
    disclaimed one sentence earlier, and no behaviour or operator decision rests on it. Filing it
    would be the grind this review has already paid for four times over.
<!-- sq:finding:F26:discussion:end -->
<!-- sq:finding:F26:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-04T14:31:01Z] Paul Reviewer:
  - Batch review of FEAT-906 recorded as REV-926: 10 findings, 2 high / 4 medium / 4 low. Recommended verdict **ChangesRequested**; the approval transition is not mine.
    
    **Verdict on the three-for-three claim: true of the code.** All three read-time paths now resolve through one declared mechanism and one shared boundary (`read_body` -> `expand_view_tags`), with `role_definition_text`, `skill_definition_text`, `_item_skill_definition_text` and `_cli/_skill.py`'s `if system:` branch genuinely gone. Nothing bespoke is hiding behind a tag. The `_playbook_subject` correction is the shape the third amendment sanctioned (identity-keyed, like `role`), not a seventh resolver in disguise, and the per-item-type emptiness case lands in the presentation template as the amendment required.
    
    **Independent spot-checks, all driven in throwaway squads and worktrees, never in this tree.** The artefact claim holds and is stronger than reported: with the roster held constant and a synthetic `incident` type declared, `.claude/`, `CLAUDE.md`, `AGENTS.md` (the `agents_md` backend, which the dev did not diff) and both `--json` payloads are byte-identical, and the 22 differing item files are one seeded tag line plus timestamps. The destruction-bug fix holds — reverting `strict_empty` reddens three tests including the real destructive integration case. The slug gate is load-bearing — reverting it makes a TASK slugged `sq-bug` resolve the `bug` lane, and the permanent test catches it. The custom-type path is genuinely general.
    
    **The two high findings are what the equivalence proof missed.** F2: `squads` and `sq-memory` skill text now embeds the squad's absolute filesystem path where it embedded `squads/`, because `squad_dir` means the folder name on the backend side and an absolute `Path` on the view side; TASK-922 recorded this as a temp-dir fixture artifact, and no test pins it. F1 is the bigger one: a 0.14 adopter installing 0.15 loses every role and skill definition, with `sq check` clean, `sq sync` reporting success, the version notice pointing at `sq sync`, `sq migrate up` saying nothing to migrate, and `sq repair` the only cure and the one command nothing names. ADR-880 licensed the backfill as a migration; it shipped as an opportunistic sweep, and `test_migration_corpus.py` documents that gap in its own docstring while proving the fix only when `repair` is called by hand. Every corpus fixture below `v0_14` rides `migrate up`'s trailing repair, which is why 4889 tests pass over it.
    
    F5/F6 are the customisation half: `sq repair` re-seeds role and system-skill tags without checking the spec still declares the view (dropping `role_definition` via `[selected]` yields nine unfixable error-level findings), and a declared type whose skill slug is already authored loses its generated guidance with nothing reporting it. F3 breaks an existing adopter `workflow.md.j2` override with a hard render error and no changelog note. F4 is `sq repair` aborting on a raw `AssertionError` traceback against the `SquadsError` convention. F7-F10 are hygiene.
    
    Nothing outside REV-926 transitioned. `sq check` clean. @tech-lead @manager for triage; F1 and F2 want fixing before the release cut.
- [2026-09-04T14:32:46Z] Catherine Manager:
  - ChangesRequested on F1 and F2. F1 is the one that matters most in this release: upgrading 0.14 to 0.15 empties every role and skill definition, with sq check clean, sq sync reporting success, and sq repair the only cure that nothing names. That is every adopters upgrade path, not an edge case. F2 is a real regression the dev recorded as a fixture artifact -- generated skill text now embeds the squads absolute filesystem path where it embedded a relative one; the reviewer caught it by comparing rendered text across all 22 slugs rather than file bytes.
  - Three-for-three accepted as true of the code, on evidence rather than the handbacks: one mechanism, one boundary, the three bespoke functions genuinely deleted rather than wrapped, and _playbook_subject carrying playbooks own resolved value, applicability, --json arm and template contract. ADR-880s central empirical claim holds. The selection rule the reviewer derived is on the board.
- [2026-09-04T14:42:27Z] Olivia Lead:
  - Triage complete. TASK-927 (F1, F4, F5, F7, F8-a, F9) and TASK-928 (F2, F3, F6, F8-b) fix nine findings against FEAT-906; F10 gets its own standalone TASK-929, deferred with a named home per the standing 'treated, not triaged away' rule — reasoning below. All three Draft; promotion at dispatch is mine.
  - F1 ruling: fix lands as TASK-927, NOT folded into FEAT-907 and NOT a new schema migration. The backfill mechanism TASK-922/923 built is sound and already generalized to role+system-skill+per-type-skill — the gap is purely that nothing triggers it when squads_version moves but schema_version doesn't (run_pending_migrations only repairs when a migration actually applies; sync() stamps squads_version without ever touching a body). TASK-927/ST1 wires the existing convergence step into sync() itself, keyed on squads_version drift — scoped narrowly, not the whole of repair(). FEAT-907 stays milestone-only (Draft, unstarted, its own dependency chain via FEAT-898/905); broadening it now would gate a release-blocking fix behind unrelated work for no mechanical benefit, and a schema bump for a non-schema content sweep is against this project's own SCHEMA_VERSION semantics.
  - F4/F5 bundled into TASK-927 alongside F1 because they're the same function family (_repair_body_tag/_converge_body_tag) and F1 makes the sweep run far more often, which is exactly what makes F4's abort-on-one-file and F5's ungated re-seed more dangerous — sequenced explicitly ahead of/alongside F1's wiring in the task body, not after.
  - F2/F3/F6/F8-b in TASK-928: independent surfaces (_views.py context passing, the Jinja filter registration, a new sq check validator, one test docstring), no file overlap with TASK-927 except _interactions/__init__.py, which TASK-927 owns exclusively (F7's constant + F8-a's docstring, same file) so the two tasks never collide.
  - F10 deferred to standalone TASK-929, unparented (purely-technical, per my own role convention) — pre-existing sq repair behaviour, not this feature's doing, orthogonal to the view-tag mechanism, and shipping it inside either fix task would tangle an unrelated index-ordering change into a release-blocking review fix.
  - One thing I think the review may have slightly underweighted: TASK-928/ST3 (F6's new sq check advisory) lands in _services/_validators.py, which is under active uncommitted edit in this tree right now for REV-925 — flagged explicitly in the subtask body as a sequencing gate, not a code note buried in a comment.
  - @manager for the promote-and-dispatch call once you've read the split. Nothing outside these three new tasks changed; sq check clean.
- [2026-09-08T13:42:50Z] Paul Reviewer:
  - Independent confirmation of the manifest/content-store regen `_specs/workflow.toml`'s edit
    required — the check nobody had run, and the one whose failure mode is silent history loss.
    Parsed both artifacts at HEAD, at the commit before the regen, and at the shipped v0.14.0 tag:
    
    - **Manifest version keys:** 17 at HEAD, none lost or added against either revision. All 16
      keys the v0.14.0 tag carries are present.
    - **Historical entries:** every entry except the working `0.15.0` is byte-identical to the
      pre-regen commit, and every one of the 16 entries the v0.14.0 tag carries is byte-identical
      to the tag's own. Inside `0.15.0` the only change is `_specs/workflow.toml`'s hash — no path
      added, none removed.
    - **Content store:** exactly one hash swapped (the previous working-0.15.0 workflow text for
      the new one). Nothing still referenced by any manifest entry was dropped; no surviving
      hash's text mutated; HEAD's manifest resolves 104/104 hashes.
    - **The shipped release is intact and correct, not merely present:** the store's text for
      `0.14.0`'s `_specs/workflow.toml` is byte-identical to `git show v0.14.0:` for that file, and
      `sha256` of the tag's file equals the manifest's hash.
    - **Driven through the consumer:** `sq override diff workflow.md.j2` on a v0.14.0-stamped
      override resolves the base against that history and renders a real Δ-upgrade pane.
    
    The release gotcha was handled, not tripped.
- [2026-09-08T13:43:15Z] Paul Reviewer:
  - Fix verification complete. **All nine fixed findings hold on their own terms and are now
    Verified; F10's WontFix is accepted with TASK-929 as its home. The review stays
    ChangesRequested — I am not approving it**, because verification turned up six new findings in
    the reviewed change, two of them medium, and one of them means F5's reported harm is still
    being produced rather than merely left standing.
    
    Everything below was driven in throwaway squads and `git worktree` builds at `v0.14.0` and
    `e40592e3`, never in this tree; every disproving search was validated against a known positive
    first; per-finding evidence is on each finding's own thread. I did not run the full suite (the
    main loop's gate) — targeted selection of all 14 new/changed test files: 72 passed, 0 failed.
    I falsified F1's trigger, F2's boundary, F3's alias and F6's validator myself rather than on
    the handbacks, and F5's gate by rendering the pre-fix build against the same corpus.
    
    **The two release-relevant ones are genuinely fixed.** F1: a real v0.14.0-built corpus, read by
    this build, has every definition empty and `sq check` clean; one `sq sync` and all 21 render,
    with no `sq repair` in the sequence. Narrow scoping proved by diff, not by reading the call —
    21 item files gain one tag line each and `.squads.json` is byte-identical, so F10 does not
    arrive on sync. F2: all 21 rendered definitions are byte-identical across two very different
    absolute roots **and** byte-identical to the v0.14.0 build's own output, so US5's acceptance
    now holds where it did not when this was filed.
    
    **What is new.** F11 (medium) — the `squad_dir` fix derives the folder name with `Path.name`,
    so a nested `squad_dir` still renders `squad/` in the skill text against `docs/squad/` in
    `CLAUDE.md`; v0.14.0 got that right, so F2's regression is narrowed rather than closed, and the
    generated agent guidance names a directory that does not resolve. F12 (medium) — `_create_core`
    seeds the role tag with no declared-view check, so activating a role under a dropped
    `role_definition` mints a fresh error-level finding every time; `sq check` exits 3 and the count
    grows per role. F13/F14/F16 (low) — a skipped convergence stamps the version anyway so nothing
    retries it and `sq check` stays clean; a non-numeric `squads_version` makes the new comparison
    raise a bare `ValueError` where the CLI's own drift notice tolerates it and v0.14.0 synced
    fine; the new empty-body hint names `sq sync` in the one state the F5 gate makes it a no-op.
    F15 (low) — `sq migrate up` collects the new `skipped` channel and prints none of it.
    
    **F5's disposition, ruled** (full reasoning on F5's thread). The doctrine argument for clearing
    a dangling tag from a tool-owned body is strong and does route around what ADR-880's second
    amendment actually refused — but it is an amendment to a ruling stated in general terms, so it
    is the architect's call, not mine or a dev's. It is also not the question to answer first: two
    closures need no doctrine change and together leave nothing for an amendment to fix — gate
    `_create_core` (F12), and expose `view add`/`view rm` on the `sq role`/`sq skill` addressing
    groups, since ADR-880 already names `view rm` as the sanctioned recovery for exactly this state
    and roster items are the one family whose addressing group never exposed it.
    
    **F3's changelog question: yes, it needs an entry** — the alias is explicitly one-release, and a
    deprecation nobody is told about is a delayed break. The 0.15.0 section has two Added entries
    and no Changed/Deprecated section at all; it also says nothing about `sq sync` now restoring
    role and skill definitions on version drift, which is the entry that tells a 0.14 adopter why
    their definitions came back. @tech-writer for the prose, adopter-facing only.
    
    **Manifest history verified independently** — separate comment above; the release gotcha was
    handled.
    
    One board-hygiene note, not a finding and not mine to change: FEAT-906's five stories are all
    still `Todo` while the feature is InProgress and both fix tasks are InReview.
    
    Nothing outside REV-926 transitioned; no fixes, no commits. `sq check` clean.
    @tech-lead @manager for triage of F11-F16 — F12 is the one I would not ship without, and F11
    is the one that puts a wrong path into generated agent guidance.
- [2026-09-08T13:46:46Z] Catherine Manager:
  - All nine fixed findings verified; six new filed (F11-F16). Two block: F12, because _create_core still seeds the tag with no spec.views check so F5s harm is still being produced rather than merely left standing -- F5s gate reached one of the three writers F7 enumerated; and F11, because _squad_dir_display derives the name with Path.name so a nested squad dir still diverges, and generated agent guidance names a directory that does not resolve. v0.14.0 got that one right.
  - Accepting the reviewers F5 ruling over my own reading. My doctrine argument does route around what the second amendment actually refused, but carving a per-type exception is itself an amendment and therefore the architects call. More to the point it is the wrong question to answer first: gate _create_core, and expose view add / view rm on the sq role and sq skill groups -- ADR-880 already names view rm as the sanctioned recovery for exactly this state, and roster items are the one item family whose addressing group never exposed it. Do both and there is nothing left for an amendment to fix.
  - Also noting F14: a bare ValueError traceback from schema_tuple on a prerelease squads_version, same class as F4 and reintroduced by the very commit that fixed F4.
- [2026-09-08T13:53:53Z] Olivia Lead:
  - Triage complete: TASK-930, TASK-931, TASK-932 (all Draft, parented FEAT-906, `implements`
    ADR-880 + `addresses` REV-926). All six new findings are in-scope-now under FEAT-906 — none
    deferred, per the standing rule (all are low-or-above).
    
    - **TASK-930** — F12 + F16 + exposes `view add`/`view rm` on `sq role`/`sq skill`.
    - **TASK-931** — F11 (nested `squad_dir`).
    - **TASK-932** — F13 + F14 + F15 (sync/migrate version-drift reporting corridor).
    
    **Triage reasoning per finding:**
    - F12 (medium, blocking): gate `_create_core`'s role-tag seed on `ROLE_DEFINITION_VIEW_NAME in
      self.spec.views` — the same condition F5's fix already applies to the other two writers.
      One line, TASK-930/ST1.
    - F11 (medium, blocking): thread `config.squad_dir` (the string) into the view-rendering path
      instead of deriving it with `Path.name` — see the fix-shape ruling below. TASK-931.
    - F13 (low): don't stamp `squads_version` past a reported skip, so a second `sync` retries —
      TASK-932/ST1.
    - F14 (low): same exception class as F4, reintroduced by F4's own fix — swap `schema_tuple` for
      the tolerant `version_tuple` (moved down out of `_cli`) in the drift comparison — TASK-932/ST2.
    - F15 (low): `sq migrate up` doesn't print `run.repair.skipped` — one loop, same wording `sq
      repair` already uses — TASK-932/ST3.
    - F16 (low): depends on the `view rm` ruling below — bundled with F12 in TASK-930 since both
      gate on the identical `spec.views` condition.
    
    **Ruling: `view add`/`view rm` on `sq role`/`sq skill` belongs in FEAT-906, not a separate item.**
    It's a mechanical CLI-wiring gap, not new design — `insert_view`/`remove_view` are already
    item-type-agnostic, and `_cli/_items.py::_cmd_view` is the exact shape to mirror into the two
    roster groups. Reasons it stays in-scope rather than getting its own item: (1) ADR-880's second
    amendment names `view rm` by name as "the recovery path for precisely this state," so FEAT-906's
    own architecture doc already promises it; closing the feature without it means the promise is
    broken specifically for the two item families the feature touches. (2) Without it, F5's already-
    Verified fix has no practical remedy for any corpus that already carries a dangling tag (pre-F12,
    or any future spec edit that drops a view out from under an already-tagged item) — the only
    recourse would be hand-editing the `.md` file, against this project's own marker-safe-edit
    convention. (3) It's cheap: zero new service logic, pure CLI surface reusing existing methods.
    **FEAT-906 should not close without it** — closing without it leaves F5 "fixed" only for new
    instances, with the state it already describes as reachable and stuck.
    
    **F11's fix shape: thread the configured string, not a single-segment constraint on
    `squad_dir`.** v0.14.0 got this right by passing `config.squad_dir` (the string) verbatim, which
    is what the backend templates still do today — the view path is the one that regressed by
    picking up a `Path` instead. Constraining `squad_dir` to one segment would break any adopter
    already running a nested one (the very shape the repro uses), which conflicts with "reason from
    the adopter" and the "squads is multi-user/adoptable" standing guidance — a nested `squad_dir` is
    a legitimate configuration, not an edge case to close off, and its docstring never claimed
    single-segment. Full reasoning in TASK-931.
    
    **Dependency order:** all three tasks are file-independent and can run in parallel — TASK-930
    touches `_base.py`/`_cli/_role.py`/`_cli/_skill.py`; TASK-931 touches `_views.py`; TASK-932
    touches `_maintenance.py`/`_cli/_migrate.py`. No sequencing constraint between them. TASK-930 is
    the one to prioritize if only one slot is available (it's what blocks approval per your own note).
    
    **Story-rollup note, not mine to change:** FEAT-906's five stories (US1-US5) are all still `Todo`
    while the feature is InProgress and both original fix tasks are InReview — flagging per your
    handback, yours to move.
    
    **Where I think the verification is right and worth calling out rather than second-guessing:**
    the F5 residual-question framing (gate the writer first, let the architect rule on retroactive
    clearing later, only if anything's still unclosed after that) is the correct order of operations
    — gating `_create_core` plus exposing `view rm` genuinely leaves nothing for a doctrine amendment
    to fix, so I did not raise it as an open question needing @architect.
    
    No implementation done; no item transitioned outside these three new tasks. `sq check` clean.
- [2026-09-08T13:54:00Z] Olivia Lead:
  - @manager @reviewer triage above: TASK-930/931/932 created (Draft) against FEAT-906, full triage and rulings on the thread.
- [2026-09-08T15:01:54Z] Paul Reviewer:
  - Third verification round. **All sixteen findings now hold — F11-F16 verified and moved to
    Verified, F1-F10 unchanged.** The review stays **ChangesRequested**; I am not recommending
    Approved, because verification turned up five more findings in the reviewed change (F17-F21),
    one of them medium and one of them the same defect F12 blocked the release on, one writer apart.
    
    Everything below driven in throwaway squads built from this build's own CLI, never in this tree;
    every disproving search validated against a known positive first; per-finding evidence on each
    thread. I did not run the full suite (the main loop's gate). Targeted run of the 13
    new/changed test files for these three commits, in the current tree: **73 passed, 0 failed**.
    Three commits landed under me while I worked (`c15336d9`, `73c9242e`, `2a3d0000` — the
    concurrent guidance-guard, skew-canary and validator-grammar work); `git diff` confirms they
    touch none of this feature's source files, so the verdicts below are against the tree as it
    stands.
    
    **Per-finding, briefly.** F11 fixed and class-closed by construction — the split is two
    parameters with two *types*, so collapsing them back is a pyright error; driven on a
    three-segment `docs/nested/squad`, all three surfaces agree, F2's absolute-path criterion still
    0 hits. F12 fixed; the third writer's reasoning holds and I checked the part that had to be
    true rather than the citation — `_create_core`'s `replace_section` is unconditional for a role
    so the template's tag can never survive, and the only other consumer of that template's body
    (`pristine_body`) is unreachable for a role because `set_body` raises first. F13 fixed and
    correctly scoped to this run's own backfill. F14 fixed, and the dev's same-shape audit of the
    other `schema_tuple` sites checks out independently. F15 fixed and the guard the coordinator
    asked about is right — driven bare: 1 on a partial repair, 0 on a clean migration, 0 on
    nothing-to-migrate. F16 fixed, both states, both groups, with dropped-type precedence intact.
    
    **`view rm` delivers F5's residue, and delivers it the way ADR-880 intended.** Driven: it clears
    a standing tag from an already-tagged corpus (`sq check` 12 -> 11 errors, that file gone), it is
    idempotent, `view add` still refuses an undeclared name at exit 1 through the same
    `resolve_view_target` the scan uses, and nothing in the codebase calls `remove_view` except the
    CLI verbs — `sq repair` re-converges an empty body but never strips a standing tag. So "visible,
    never undone" holds and **no amendment is needed**. F5 is closed in substance, not only for new
    instances. Full evidence on F5's thread.
    
    **The question the coordinator actually asked: are these six class-closed, or instance-only?**
    Three closed, three left a sibling.
    
    - **Class-closed: F11** (the type split makes the regression unreachable, and `squad_dir` is the
      only path-shaped value any view template reads — I enumerated every expression in
      `templates/views/*.j2`), **F14** (one comparator, and the other three `schema_tuple` sites
      provably read a different field), **F16** as scoped (both new branches key off the same
      `spec.views` predicate the classifier uses, so hint and behaviour cannot disagree).
    - **Instance-only: F12 -> F17** (medium). The gate went on the role writer. The skill writer,
      `_write_managed_skill`, is still ungated: driven, the `sq check` error count grows +1 per
      newly declared item type under a dropped `item_skill` view, while the role side stays flat
      across two activations and a `dev add`.
    - **Instance-only: F13 -> F18**, **F15 -> F20**, and **F16's third branch -> F19**. Each fix
      changed a command's behaviour and left that command's own message or exit code stating the
      old behaviour. F14 additionally inherited a wrong-direction comparison (**F21**).
    
    **And the pattern, which is what I think matters more than the five.** Round 1: 10 findings.
    Round 2: 6, all six induced by round 1's fixes. Round 3: 5, all five induced by round 2's.
    The count and the severity are both falling (2 high/4 med -> 2 med/4 low -> 1 med/4 low), so it
    is converging — but it is not converged, and every one of the five sits in one of exactly two
    families:
    
    - **(A) A writer enumerated but not swept.** F17's declaration site names its own writers two
      lines above the constant — `_interactions/__init__.py:172-175`, "the two writers this table is
      shared between". F5 gated one of the two. F12 was scoped to the role name and nobody re-ran
      F5's condition against the sibling table. The enumeration existed *in the code*; the sweep of
      it did not happen.
    - **(B) A command's message or exit code not re-derived after its behaviour changed.** F18, F19,
      F20 are three instances, and F19 is the third instance of one sentence ("the hint names an
      action that cannot be taken") across three rounds.
    
    **Recommendation: one more round, but not another round of this shape.** Fixing five instances
    and re-reviewing is what produced the last two layers. Both families are mechanically
    enumerable, so the next task should close them by construction rather than by instance:
    
    1. Enumerate every writer of a `sq:view:<name>` tag — the grep is six lines (`markers.view_tag(`
       under `src/`) — and assert in one test that each is either gated on `spec.views` or
       documented as unreachable, with the reason. That would have caught F17 before it was written,
       and it closes family A for the next view anyone adds.
    2. Table-drive one test over every CLI consumer of a `RepairResult` / of `sync()`'s skip list,
       asserting message-and-exit parity against `sq repair` for each channel (`skipped`,
       `unreadable`, the withheld stamp). Covers F18 and F20 and the next one.
    3. Give the empty-body hint one predicate with three inputs (view declared / tag present /
       version drift outstanding) resolved in a single helper that `sq role show`, `sq skill show`
       and the file scan all read, the way `resolve_view_target` already unifies the placement,
       scan and read-time questions. F19 exists because three call sites each answer part of it.
    
    That is one task, bounded, with a test that fails today. If the operator wants the loop to stop,
    this is the round that stops it; a fourth instance-sweep will find a fourth layer, because
    nothing yet enumerates either family.
    
    **F17 is the one I would not ship.** It is F12's defect on a supported customisation path
    (`docs/overrides.md` documents dropping a view), it puts a squad in a permanently failing gate
    that grows on its own, and board notice 6 is explicit about that class. F18-F21 are all low and
    all cheap; none of them alone would block.
    
    No fixes, no commits, nothing outside REV-926 transitioned. `sq check` clean.
    @tech-lead @manager for triage of F17-F21, and for the call on the three enumerations above.
- [2026-09-08T15:03:51Z] Catherine Manager:
  - Third round: sixteen findings Verified, five new (F17-F21), one medium. Taking the reviewers recommendation over another instance-fix round. His diagnosis is the useful part: all five sit in two mechanically enumerable families -- (A) a writer the code itself enumerates and nobody swept, and (B) a commands message or exit code not re-derived after its behaviour changed. F19 is the third appearance of one sentence in three rounds.
  - The damning detail on F17: the declaration site names its own writers two lines above the constant (_interactions/__init__.py:172-175, "the two writers this table is shared between"). F5 gated one, F12 gated the role one, and nobody re-ran the condition against the sibling the comment pointed at. That is not carelessness, it is a missing enumeration test.
  - And F21 is F14s fix introducing a subtler defect: version_tuple("0.15.0rc1") == (0, 15, 1), so a prerelease sorts above its own release and equal to the next patch -- an rc-stamped squad reads as no-drift and F1s backfill trigger silently would not fire. A loud crash traded for a quiet wrong answer. Fourth fix-induced finding this feature.
- [2026-09-09T14:40:32Z] Olivia Lead:
  - TASK-933 authored on the reviewer's own recommendation: one task, four subtasks, no dev/review dispatched yet (Draft).
  - Triage: F17 in-scope-now (ST1) — the reviewer's ship-blocker, F12's defect one writer over. F18/F20 in-scope-now (ST2), F19 in-scope-now (ST3) — all three cheap and in the same corridor already touched this round. F21 in-scope-now (ST4) — sits directly on F1's guarantee, cheap fix, no reason to leave it live for a fourth round.
  - Shape: ST1/ST2/ST3 map directly onto the reviewer's three prescribed closures — each is a test that enumerates or table-drives a family and fails today, not a per-instance patch. ST4 (F21) doesn't fit either family, so it stands alone rather than being folded into ST1-3's framing.
  - @python-dev not yet dispatched — this is task authoring only, per instruction. @manager for promotion when ready.
- [2026-09-10T08:20:15Z] Paul Reviewer:
  - Fourth verification round. **F17-F21 all hold and are Verified — twenty-one of twenty-one.** The
    review stays **ChangesRequested**; four new findings, F22-F25, two medium.
    
    Method: driven in throwaway squads on the shipped build, and falsified in an isolated
    `git worktree` at HEAD which I then removed — never in this tree, which is clean. Targeted
    selection derived from the diff (`tests/meta` + `tests/cli` + the seven sync/backfill/view-gate
    service modules, the unconditional floor for a `_cli/` change): **1293 passed, 1 skipped, 0
    failed**. I did not run the full suite. Every disproving search validated against a constructed
    known positive first.
    
    **This round was the test of my own recommendation, so the verdict on it first: the method
    worked, and it worked in the half where it was actually applied as an enumeration.**
    
    - **Family A (a writer enumerated but not swept) is genuinely closed, and I proved the closure
      rather than reading it.** Reverting F17's three gates in a worktree reddens exactly one row of
      the meta test, naming the writer and its gate targets — so it *would* have caught the instance
      before it was written. Behaviourally too: the same commit's service test goes red in three
      places on the reverted build, including the finding-count growth assertion I drove by hand last
      round. Independently re-derived the enumeration instead of trusting the dict, and the six
      attribute-style sites are the six. Three gaps between the claim and the check, all driven, all
      filed as F25 (bare-name calls escape the AST filter; a template literal escapes by construction
      and one exists today; the gate half is a text proxy a decoy `spec.views` mention satisfies).
      None is a live defect — the residual is about tomorrow's site, not today's.
    - **Family B was closed by coverage, not by enumeration — and the one consumer outside the
      hand-picked list has the defect.** My recommendation was "table-drive one test over **every**
      CLI consumer of a `RepairResult`". The table covers three commands; there are four. `sq adopt`
      reads `result.repair.strip_notice()` and nothing else — verbatim the shape F15 reported on
      `sq migrate up` — reports neither `skipped` nor `unreadable`, and exits 0. Filed as F23.
    
    **On the question you asked me to be ready for: this is not the enumeration approach failing.**
    F23 is in family B, but it is **not fix-induced** — `sq adopt` has had this hole since before
    REV-926 existed; F15's fix and this round's F20 fix did not create it, they declined to cover it.
    And the reason it was missed is precise and fixable: family A got a self-enumerating AST scan,
    family B got a list of three command names. Finish the method on family B — enumerate the
    consumers of `RepairResult`/`SyncSkips` the way the view-tag sites are enumerated, and let a
    fourth consumer fail the table rather than pass it — and the family closes the same way A did.
    That is one more task of the same kind, not a fifth round of instance-fixing. I would not bring
    "the approach failed" to the operator; I would bring "it was applied to one family and
    approximated for the other".
    
    **F22 and F24 are new ground, as you anticipated the schema module would be.** Not the module
    itself — `version_drifted` is right, and I drove the prerelease, equal and lower cases plus the
    empty and garbage stamps; the fail-safe direction is the correct one and the docstring owns the
    over-trigger. What is wrong is around it: the class check behind the fix enumerated **two**
    `version_tuple` callers where there are **four**, and the copy the handback called
    "cosmetic-only" is the comparator behind `sq migrate chlog`'s range filter. Driven, end to end:
    `sq migrate up` prints `manual steps remain — read them with sq migrate chlog
    v0.14.0rc1..v0.15.0`, and that exact command answers `no manual steps for v0.14.0rc1..v0.15.0`
    for a migration whose steps the truthful window prints. The tool contradicts its own
    instruction, one line apart. The two callers nobody named are in the override-provenance path
    (`_overrides/_manifest.py`'s `artifact_floor` min-by-key and `known_index_versions` sort-by-key);
    `artifact_floor` is a *selection*, not a label, so "informational" undersells it — though it is
    not currently reproducible, every manifest key today being a clean X.Y.Z.
    
    **On the duplicate: filed, not agreed as a cleanup (F24)** — because the reason for deferring it
    is factually wrong. `_cli/_migrate.py` imports `version_tuple` from `_cli/_common`, so the
    duplicate is not "cosmetic-only"; it is the comparator behind the chlog filter. There are now
    three implementations for two semantics, and "grep who compares versions" returns a different
    answer depending on which name you grep — which is the mechanical reason this fix's own class
    check went short. This project has already ruled on the class: the marker-regex meta guard exists
    because a duplicated primitive meant fixing the reported copy left the other blind.
    
    **Per-finding, briefly.** F17 fixed, driven both flavours (per-type and system skill) plus role
    and repair controls, count flat at 11 across two new types; falsified. F18 fixed — the green
    success line is gone, the withheld-stamp sentence is honest, the skip *is* re-reported on the
    retry (checked, because the sentence points "above"), clean sync still says synced; exit stays 0,
    which is what I scoped, and the divergence is now stated at the row that tests it. F19 fixed —
    three states x two groups, and I checked each state's claim for *truth*, not just for being a
    different sentence; one pure predicate, `drift_outstanding` passed in rather than recomputed.
    F20 fixed — the unreadable file is named, bare exit 1, `sq repair`'s own wording; re-verified
    `repair`'s own bare exit rather than through a pipe. F21 fixed — matrix above.
    
    Also checked and clean: `SyncSkips`' zero-breakage claim (exactly one reader, no slicing or
    `list()` round-trip in between, so the list-subclass attribute-erasure hazard is not live).
    
    One thing I found and deliberately did **not** file, for you to route: deleting a managed skill's
    body file and re-syncing restores it with no frontmatter, and that state is permanent — `sq
    repair` exits 1 on it forever while `sq check` reports clean, and neither `sync` nor `repair`
    re-stamps the id. Pre-existing, orthogonal to this feature, and only reachable by a hand edit
    under `squads/` that this project's own rules forbid. Say the word and I will file it.
    
    **Recommended verdict: ChangesRequested.** F23 is the one I would not ship — nothing downstream
    catches it, `sq check` structurally cannot, `adopt`'s own closing line points at `sq check`
    rather than `sq repair`, and the observable result is an adopted squad's agent booting on stale
    body content with a clean bill of health. F22 next: a suppressed manual migration step is the one
    thing squads cannot do on the operator's behalf. F24 and F25 are cheap and neither blocks.
    
    No fixes, no commits, nothing outside REV-926 transitioned, no removals, no hand-edits under
    `squads/`. `sq check` clean. @tech-lead @manager for triage of F22-F25.
- [2026-09-10T08:22:14Z] Catherine Manager:
  - Fourth round: 21 of 21 verified, four new (F22-F25), two medium. Accepting the reviewers diagnosis over the framing I had prepared. The enumeration approach did not fail -- it was applied to family A as a self-enumerating scan and works, and approximated for family B as a hand-written list of three command names. A hand-written list of consumers is the same shape as the hand-written list of writers F17 slipped through, and there are four consumers.
  - F23 is the one not to ship: sq adopt is the fourth RepairResult consumer, and adopt is the entry path for every new adopter. Driven -- a marker-shaped role body prints nothing, bare exit 0, sq check exit 0 with no finding, and sq role manager show renders stale legacy content, so an adopted squads agents boot on it. sq repair on the identical corpus names it at error, exit 1. adopts own closing line points at sq check, the one command that structurally cannot see it.
  - F25 is the sharpest because it is a gap in the closure mechanism rather than another instance: a seventh writer added via a bare-name import passes all six tests, template literals escape the *.py scan with one such writer live today, and the gate half is a text proxy that an unused in-spec.views mention satisfies. The behavioural test is what actually catches the decoy.
- [2026-09-10T08:29:23Z] Olivia Lead:
  - Fourth-round triage complete. **TASK-936** created (Draft, parented FEAT-906, `implements`
    ADR-880, `addresses` REV-926), four subtasks ST1-ST4, full detail in the task body.
    
    - **ST1** — enumerate every consumer of `RepairResult`/`SyncSkips` the way TASK-933 enumerated
      view-tag writers; fix `sq adopt` (F23) to report both channels and exit 1, matching `sq
      repair`'s contract. A fifth consumer with no classification fails the test outright, closing
      family B the same way TASK-933 closed family A.
    - **ST2** — widen the AST filter to also match `ast.Name` (`view_tag` imported bare), not only
      `ast.Attribute` (F25 gap 1).
    - **ST3** — add a second scan over `_rendering/templates/**/*.j2` for literal `sq:view:` tags,
      classifying `agents/role.md.j2:2` as `neutralized-by-overwrite` (F25 gap 2).
    - **ST4** — replace the gate-check's `spec.views`-mention regex (satisfied by an unused decoy
      mention, driven) with a required `behavioural_test` citation per `gated` entry, checked for
      existence only — not re-deriving proof the gate works from source text (F25 gap 3).
    
    Every ST is a test that fails before its fix: ST1 on `sq adopt`'s silent skip/unreadable and
    exit 0; ST2 on the reviewer's own bare-name seventh-writer repro; ST3 on a constructed second
    template writer; ST4 on a dangling `behavioural_test` citation. Testing section carries the
    false-zero rule (both ST1's and ST3's closures are completeness claims over a grep) and the
    `tests/meta`/`tests/integration`/`tests/cli` floor for the `_cli/_main.py` (`adopt`) change.
    
    **F22/F24 ruling: split out of FEAT-906, not authored here.** FEAT-906's scope is the read-time
    render collapse; F22 (chlog silently drops a migration's manual steps on a prerelease bound) and
    F24 (the duplicated `version_tuple` behind it, plus the two unnamed override-provenance callers
    — `artifact_floor`'s `min(...)`, `known_index_versions`' sort) are entirely on the
    version-comparison surface — `sq migrate chlog` and `_overrides/_manifest.py` — not the view
    mechanism ADR-880 governs. Nothing in ADR-880 or FEAT-906's five stories touches version
    comparison. **FEAT-906 can close without them** — none of US1-US5's acceptance depends on
    `chlog`'s range filter or the manifest's version-key ordering.
    
    Recommending, not authoring (task-authoring-only this round): file F22+F24 together as a bug,
    now rather than deferred to MILE-934 — it's cheap (delete the `_cli/_common` duplicate, import
    `_util.version_tuple`, fix its ordering to split a suffix instead of concatenating its digits,
    which closes F22, F24 and both unnamed override-provenance sites in one comparator fix), it's a
    genuine correctness defect (not merely a cleanup — F24's "cosmetic-only" deferral reason was
    factually wrong, since the duplicate feeds `chlog`'s filter), and it's reachable through this
    project's own workflow (prerelease/rc builds get tagged and later upgraded here). @manager /
    QA to author and route.
    
    **The unfiled skill-body issue: recommend a bug, targeted MILE-934, not this release.** Real and
    driven (delete a managed skill's body file, resync — restores with no frontmatter, permanently;
    `sq repair` exits 1 on it forever, `sq check` reports clean, neither re-stamps the id) but
    pre-existing, orthogonal to this feature, and reachable only through a hand-edit under `squads/`
    that this project's own convention already forbids — low reach given that. Worth a name and a
    home given the "treated, not triaged away" standard, but not worth gating 0.15 on, especially
    with scope already being trimmed out of this release. Not authored here per instruction.
    
    **Where I think the diagnosis is right and don't have a correction.** The family A/family B
    framing holds up under my own read of the evidence — family A's closure is structural (an
    unclassified writer fails outright) where family B's was a command-name list that a fourth
    consumer simply wasn't on. F25's three gaps are correctly scoped as guard-hardening, not live
    defects, and the ST4 ruling (behavioural test as the real guard, meta test as citation-checker
    rather than re-derived proof) follows directly from what the reviewer already drove — reverting
    the three gates and adding a decoy `spec.views` mention passes the meta test but fails the
    behavioural one, so asking the meta test to prove more than that citation is honest would just
    reproduce the same gameable shape one level up.
    
    No implementation done; no item transitioned outside TASK-936. `sq check` clean.
- [2026-09-10T08:38:27Z] Mara Tester:
  - Filed both recommended bugs, verified driven rather than transcribed, both targeted MILE-934 (0.16): BUG-937 (F22+F24, the version-comparison defect) and BUG-938 (the unfiled managed-skill body durability hole).
  - BUG-937: reproduced the chlog contradiction end-to-end and confirmed all four version_tuple call sites by reading. Agree not release-blocking for a clean X.Y.Z cut.
  - BUG-938: reproduced the permanent frontmatter loss, but sq check does NOT stay clean on the current tree -- it flags the missing id every cycle (exit 3). Noted as a correction in the bug body; the durability hole itself still stands.
  - @qa work done; no items transitioned beyond the two new bugs.
- [2026-09-10T08:39:18Z] Catherine Manager:
  - F22 and F24 closed WontFix against a home rather than deferred loosely: both are now BUG-937, targeted at 0.16, verified by QA driving the chlog contradiction herself rather than transcribing it -- including version_tuple("0.14.0rc1") < version_tuple("0.14.0") returning False, which is the mechanism in one line. Ruled out of FEAT-906 because they sit on the version-comparison surface ADR-880 never touches and no FEAT-906 story depends on; 906 can close without them.
  - The unfiled durability hole is BUG-938, also 0.16 -- and QA corrected the finding while verifying it. The claim that sq check reports clean did not reproduce: it flags the missing id every cycle and exits 3, because _is_legacy_skill_body only exempts a non-SKILL-prefixed filename and these are already prefixed. So the defect is a permanently broken file sq repair refuses forever, but visibly rather than silently. Filed with the discrepancy recorded rather than the stronger claim.
- [2026-09-10T09:04:04Z] Paul Reviewer:
  - Fifth round. **F23 and F25 both hold and are Verified — every one of the 25 is settled.** But I
    am **not** approving, because the residual you asked me to probe is real: **filed as F26 (low),
    plus F26's sibling half on the corridor scan, recorded on F23's own thread.** You said you would
    rather take one bounded pass at the guard than approve a guard that has learned to look verified;
    on the evidence below, that is the right call, and the pass is small.
    
    Method: driven in throwaway squads on the shipped build; falsified in an isolated `git worktree`
    at HEAD, restored and removed — the repo tree is clean and was never edited. Targeted selection
    (`tests/meta` + the parity module + the three cited behavioural modules): **321 passed, 0
    failed**, with the `^FAILED` pattern validated against a known positive before its zero was
    trusted. I did not run the full suite.
    
    **Your claim, reproduced exactly.** All three real gates reverted (`_create_core`'s conditional,
    `_repair_body_tag`'s three `spec.views` returns, both `_write_managed_skill` caller gates) plus
    one *unused* `in spec.views` mention added to each target — the decoy that defeated the old
    regex:
    
        meta module                        12 passed     (it no longer inspects source text)
        the three cited behavioural tests   3 failed     (one per gated site)
    
    So the module now claims exactly what it checks, and the proving genuinely moved to the tests it
    names. F25's three gaps are closed, each with a fixture that reproduces my own probe rather than
    a sentence saying it was considered — the bare-name test drives the **production** scanner rather
    than a copy, and the template test works on a copied tree with a regression control asserting the
    real bundled corpus is untouched. That is better than I asked for.
    
    **Can a citation be honest-looking but useless? Yes — three ways, all driven with the gates
    still reverted.** Detail on F26; the sharpest, because the substitute is neither synthetic nor
    implausible: re-point `_write_managed_skill`'s citation at
    `test_a_newly_created_per_type_skill_under_a_declared_view_still_seeds_the_tag` — a real,
    top-level, currently-passing test **in the very file the citation already names**, written by the
    same commit as its own regression control, whose name reads as though it is about the
    declared-view gate. Meta module **12 passed**; the cited test **1 passed** with the gate broken,
    because it asserts the *declared*-view direction an ungated writer satisfies too. No test body
    edited. Second: a `@pytest.mark.skip` on the real cited test leaves the module at 12 passed and
    the cited test at `1 skipped` — the accidental version, which is how this actually happens.
    Third: relabelling a `gated` site `not-a-writer` and deleting its citation leaves the module at
    11 passed, gate still broken, because the citation requirement's own *scope* is self-declared.
    
    Closure is cheap and mechanical for the two that matter: **invert the citation** — mark the
    behavioural test with the site it proves (`@pytest.mark.gate_for("…::_write_managed_skill")`) and
    build the map by collecting markers instead of reading a hand-maintained dict, so a citation
    cannot point at an arbitrary test because the test declares what it proves; and reject a cited
    test that is `skip`/`skipif`/`xfail`-marked or excluded by default collection ("collected and
    live" is checkable without executing anything). What genuinely cannot be closed by a unit test —
    whether the cited assertions actually falsify the gate — is only knowable by mutating the gate,
    and the dict's comment already records that this was driven once per site. The gap is that
    nothing keeps the citation attached to that recorded event; a marker on the test does.
    
    **Could a sixth repair-corridor consumer evade the new scan? Yes, and in the most on-point
    shape.** Full evidence on F23's thread. The enumeration is a genuine discovery — it found five
    sites where four were hand-listed, and surfacing `renumber` as a false-positive-by-name
    (classified rather than filtered out by guessed type) is exactly right. But it keys on *reading a
    channel attribute*, while the defect class is *consuming the sweep without reporting it*. Driven
    against the module's own `_sites_in_module`, control validated first: `svc.repair()` with no
    channel read is FOUND (only because `repair` doubles as a channel field name), while
    `svc.sync()`, `svc.run_pending_migrations()` and `svc_adopt(...)` with no channel read are all
    MISSED — each of them precisely `reports-neither-channel`, the state that table declares must
    never exist. Had the real `adopt` discarded its result instead of reading `result.repair`, this
    scan would have missed the very defect it was built for. Closure is the same widening F25 gap 1
    got: add the producer names to `_TARGET_ATTRS` and match the bare-name `svc_adopt` call the way
    the writer scan now matches a bare-name `view_tag`. Worth noting the two scans were written in
    the same commit and only one of them learned the bare-name lesson.
    
    **On the `sync` label: the reason is honest, the label's *name* is the imprecise part.** Checked
    the substance rather than the wording: `SyncSkips` exposes exactly one channel beyond the flat
    list (`backfill_skipped`), `sync` does print it, and `RepairResult`'s `skipped`/`unreadable`
    genuinely do not exist on it because `sync` runs the body-tag-only slice, not the rebuild. So the
    reason string is factually correct, states the divergence instead of hiding it, and declining to
    invent a fourth label for a one-channel result type is the right instinct. And the module's own
    docstring already defines the label channel-count-agnostically — "prints every channel its own
    consumed result type carries for this concern". The only thing wrong is that the label is *named*
    "both" while its definition says "every": rename it to `reports-every-channel` and the reason
    string stops having to apologise for the name. A rename, not new vocabulary — fold it into F26's
    pass if you take it. Not filed.
    
    **Per-finding.** F23 fixed and driven both channels, bare exit 1 each, `sq repair`'s own wording,
    and the generic closing hint correctly suppressed on the failing path (0 occurrences, driven) —
    which was the specific thing my finding called out about `adopt` pointing at `sq check`. F25 fixed,
    all three gaps, evidence above.
    
    **Recommended verdict: one bounded pass, then Approved.** Twenty-five findings are settled and
    FEAT-906's own change is sound — F26 and the corridor-scan widening are defects in the *guard*,
    not in the product, and neither has a user-visible failure behind it. If you would rather ship,
    F26 with a named home (BUG-937's 0.16 slot fits: same "a check that cannot see what it claims"
    concern) is a legitimate disposition under the treated-not-triaged rule and I would not argue.
    What I would not do is approve with F26 open and unhomed, because the whole point of this guard is
    that the next writer does not get three review rounds, and right now a skipped test quietly
    removes its backing.
    
    Nothing outside REV-926's own findings transitioned. No fixes, no commits, no removals, no
    hand-edits under `squads/`. Worktree removed; repo tree clean. `sq check` clean.
    @tech-lead @manager for F26's disposition and the corridor-scan widening.
- [2026-09-10T09:05:30Z] Catherine Manager:
  - F23 and F25 Verified; all 25 settled. Not approving yet -- taking the bounded pass on F26 rather than homing it, and the reason is sequencing: FEAT-907 is the next feature and it will be built and reviewed against exactly these guards. A guard that a pytest.mark.skip silently disarms is worse than no guard, because it is trusted. Fixing it now while the context is hot beats discovering it inside FEAT-907s review.
  - The residual is real and the accidental form is the one that matters: a skip/skipif/xfail marker on a cited behavioural test leaves the meta module green while the gate is broken, because decorators are invisible to an AST FunctionDef name lookup. And the corridor scan keys on READING a channel while the defect class is CONSUMING the sweep without reporting it -- so calls svc.sync() and reads nothing is missed, which is precisely the reports-neither-channel state the table declares must never exist. The reviewers own summary: had the real adopt discarded its result instead of reading result.repair, this scan would have missed the very defect it was built for.
  - Both closures are mechanical: invert the citation so the behavioural test declares what it proves via a marker rather than the map pointing at an arbitrary test, and reject a cited test that is skip/skipif/xfail-marked or excluded by default collection; widen the corridor scan to the producer names and the bare-name call form -- the same lesson F25 gap 1 got, which only one of the two scans in that commit learned. Plus renaming reports-both-channels to reports-every-channel, since the modules own docstring already defines the label channel-count-agnostically.
- [2026-09-10T09:33:31Z] Paul Reviewer:
  - **Approved.** F26 holds; all 26 findings are settled — **23 Verified**, F10/F22/F24 WontFix
    against named homes (TASK-929, BUG-937 x2). FEAT-906's change is sound and I have nothing left
    open against it.
    
    Method: driven in an isolated `git worktree` at HEAD with all three real gates reverted, restored
    and removed — the repo tree is clean and was never edited. Every drive reproduced against the
    **real corpus**, not the fixtures shipped with the fix. Targeted selection (`tests/meta` — the
    floor for a `pyproject.toml` marker change — plus the parity module and the three cited service
    modules): **325 passed, 0 failed**, with the `^FAILED` pattern validated against a known positive.
    Did not run the full suite.
    
    **Drive 1 fires on my exact edit, not on a naive duplicate.** I added the `gate_for` marker to the
    real sibling my original drive re-pointed at —
    `test_a_newly_created_per_type_skill_under_a_declared_view_still_seeds_the_tag`, uninvolved,
    currently passing, in the very file the true citation names — and the uniqueness check failed,
    naming both claimants by full `path::name`. Drive 2 refused, with the exclusion set unit-driven
    across `skip`/`skipif`/`xfail`/`slow` (all excluded) against `usefixtures` (not excluded), so it
    keys on suppression rather than on "has a marker" — extending it to `slow` beyond my drive was
    correct. Drive 3 structurally gone: `GATED_BEHAVIOURAL_TESTS` and `_cited_test_exists` are absent
    (disproving grep validated), the map is collected, and a marker naming a non-`gated` site trips
    `extra`. And F25 re-verified under the new mechanism rather than assumed: 13/13 green, three cited
    tests red.
    
    **The declared boundary: accurate on substance, honest in intent, with one clause overstated and
    one mitigation understated — both wording, neither a defect.** The swap really is undetectable
    statically (driven). The mutation clause really is the honest limit of what a static check can
    claim, and saying it is the inverse of what F25 was. The one clause that reads stronger than the
    mechanism is *"the marker keeps the citation attached to that recorded event"*: driven, keeping the
    marker and the name while gutting the cited test's body leaves the module green and the "prover"
    passing with the gate broken — the marker binds the claim to a *test*, not to the driven event,
    which lives only in commit prose. Its substance is already disclaimed one sentence earlier, so the
    comment does not mislead about what is checked. And in the guard's favour, understated: a swap
    costs **attribution, not detection** — driven, the real prover is still collected and still fails
    on a broken gate, so what a swap breaks is the guard's ability to say *which* test proves the site.
    Stating that would make the boundary both more accurate and less alarming.
    
    I am deliberately **not** filing that as a finding, and the reasoning should be on the record so
    the call is auditable rather than convenient: the false-claim findings I filed earlier here (F11's
    derivation docstring, F19's hint comment) were load-bearing — one justified a derivation, the other
    sent an operator at a command that could not help. This clause sits in a test-module comment whose
    substance is disclaimed a sentence earlier, and no behaviour or operator decision rests on it.
    Filing it would be the grind this review has already paid for four times.
    
    **Corridor scan:** all three shapes I drove as MISSED are FOUND, the two dynamic shapes are
    declared-not-glossed, the negative control stays MISSED, and the real `_cli/` corpus still resolves
    to exactly five sites — so the widening surfaced no hidden sixth consumer and invented no false
    positive. `reports-every-channel` landed and `sync`'s reason now clarifies rather than apologises.
    Marker registration changes nothing about collection: `gate_for` is declared with a help string,
    the `slow` hook never sees it, and the five modules run clean under
    `-W error::pytest.PytestUnknownMarkWarning` (34 passed).
    
    **On the sequencing, since you raised it:** five rounds was expensive, but the last two were not
    waste — round four's findings only existed because the fixes were real enough to reach new ground,
    and the guard being attackable was worth knowing before it became the thing standing between the
    next writer and another review. What I would carry forward is narrower than "enumerate": *when a
    closure delegates its proof, make the delegation unforgeable, and write down what it still cannot
    see.* This guard now does both. Two entries are in my memory notebook against the next one.
    
    Verdict: **Approved**. `sq check` clean. Nothing outside REV-926's own status and findings
    transitioned; no fixes, no commits, no removals, no hand-edits under `squads/`.
    @manager FEAT-906 is clear from my side.
<!-- sq:discussion:end -->
