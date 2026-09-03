---
id: TASK-821
sequence_id: 821
type: task
title: Unknown-key refusals name the running squads version
status: Done
parent: FEAT-791
author: tech-lead
assignee: python-dev
priority: medium
refs:
- REV-817:addresses
- ADR-777:implements
description: The shared merge engine's unknown-key message names the key and the accepted
  set but never the version, leaving FEAT-791's forward-compatibility clause unmet
  for every override kind
subentities:
- local_id: ST1
  title: Name the running version in the shared unknown-key message
  status: Done
  assignee: python-dev
  story: US4
- local_id: ST2
  title: Update every carrier of the old refusal text
  status: Done
  assignee: python-dev
  story: US4
created_at: '2026-08-25T23:00:49Z'
updated_at: '2026-08-26T08:38:05Z'
---
<!-- sq:body -->
## Scope

FEAT-791 US4 — the unmet half of the acceptance clause that closed the role override's top-level
key space.

FEAT-791 states it as: *"A role override naming a key `RoleSpec` does not declare is refused, naming
the key **and version**."* ADR-777 §4 makes the version the load-bearing half of the whole argument
for closing the key space rather than discarding unknown keys: *"the forward-compatibility case is
served by the refusal telling the adopter which key and which version, not by discarding it."*

The refusal names the key. It does not name the version.

## Where it actually lives

Not in the roles layer. `_specmerge.py:523-556::_unknown_key_violations` builds the entire message —
`unknown {what} {key!r}` plus `use one of the accepted {what}s: {sorted(accepted)}` — and
`squads.__version__` appears nowhere in `_specmerge.py`. Both callers route through it:
`_top_level_key_violations` (`:559-581`, the document's own closed top-level key space) and
`_validate_selected_shape` (`:584+`, the `[selected]` section names). Every override kind inherits
the same shape, so this is not a roles defect — the roles catalog is where a promise was written
against it.

Driven output today, both roles key spaces:

    error: .../architect.toml: nonsense: unknown top-level key 'nonsense' — use one of the
    accepted top-level keys: ['agreements','can_spawn','color','description','full_name',
    'is_default','mission','model','responsibilities','selected','slug','title']

    error corpus: could not scan the corpus: .../roles.toml: nonsense: unknown top-level key
    'nonsense' — use one of the accepted top-level keys: ['bundles','dev','roles','selected']

## Whose debt this is

Pre-existing, not new. `_unknown_key_violations` landed in `2f8b1ab` (2026-08-15), before this
review's range begins, and the message has had this shape since. What is new is the promise: the
roles catalog work applied the shared refusal to a fifth key space and wrote an acceptance clause
requiring the version, without adding it. So the code is older debt and the unmet clause is this
release's.

That matters for scoping, not for whether it ships: the fix is one message in one shared helper and
it discharges the clause for every kind at once, which is a better outcome than a roles-only patch.

## Why it is not cosmetic

The accepted-set list alone tells an adopter their key is not accepted. It does not tell them
whether the key is a typo, a key from a newer squads they are running against an older install, or a
key from an older squads that has since been removed. Those three have different remedies. Naming
the running version is what converts the refusal into the forward-compatibility answer ADR-777
already claims it is; as written, the code ships the closure without the compensation the decision
traded for it.

## Acceptance

1. Every unknown-key refusal from `_unknown_key_violations` names the running squads version
   alongside the accepted set, in both key spaces (`top-level key` and `[selected] section`) and for
   every override kind — role, roles catalog, workflow, playbook.
2. The version comes from `squads.__version__`, never a literal. `squads/__init__.py` imports
   nothing from the package's internals, so importing it into `_specmerge.py` introduces no cycle —
   confirm the import graph check still passes rather than taking that on trust.
3. The `empty_accepted_hint` path — a document with no valid entries for a key space at all — still
   replaces the accepted-set menu, and the version still reaches the reader on that path or is
   deliberately omitted with the reason recorded on the subtask.
4. Every test and golden asserting the old message text is updated, and at least one test asserts
   the version is present rather than asserting the whole string, so the assertion does not have to
   be rewritten at each release.
5. Drive one refusal per override kind through the CLI and confirm the wording is identical across
   all of them — a message shared by five kinds that renders differently for one is worse than the
   omission.
6. `sq check` clean; `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` clean.

## Ordering note

This changes a refusal that adopter documentation quotes verbatim. `docs/overrides.md:226-229`
reproduces this exact message as literal tool output, and TASK-815 is already scoped to correct that
block. TASK-815 depends on this task so the writer reproduces the final text once rather than twice.

## Out of scope

Any change to which keys are accepted, to the closure decision itself, or to the `[selected]`
shape validation. Message content only.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 821 add-subtask "<title>"`; track with `sq task 821 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done | python-dev | Name the running version in the shared unknown-key message | US4 |
| ST2 | Done | python-dev | Update every carrier of the old refusal text | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Name the running version in the shared unknown-key message

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US4 — Close the role override top-level key space (align ADR-696 §4b)
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Import `__version__` from `squads` into `_specmerge.py` and fold it into the fix hint built at
`:547-551`, so the accepted set is qualified by the version that accepts it — the review's suggested
reading is "...accepted top-level keys **in v0.14.0**: [...]".

Keep the helper shared. Both callers (`_top_level_key_violations` and `_validate_selected_shape`)
must inherit it without either passing the version in, since neither knows anything the other does
not.

Decide what happens on the `empty_accepted_hint` path, where the caller replaces the menu entirely
because the document has no valid entries for that key space at all. Either the version still
reaches the reader there or it deliberately does not; record which and why on this subtask rather
than leaving it to whoever reads the diff.

Confirm the import introduces no cycle. `squads/__init__.py` imports only `importlib.metadata`, so
it should not — but the repo verifies an acyclic import graph and that check is the proof, not this
note.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Update every carrier of the old refusal text

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US4 — Close the role override top-level key space (align ADR-696 §4b)
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Find every test, golden and fixture asserting the old message and update it. A grep for
`use one of the accepted` finds the assertion sites; run the suite rather than trusting the grep,
because some assertions match on a fragment.

Where a test asserts the whole string, prefer changing it to assert the key, the accepted set and
the presence of `__version__` separately. A golden that embeds a literal version number has to be
regenerated at every release, which is how a message assertion quietly becomes a maintenance tax.

Then drive one unknown-key refusal per override kind — a per-slug role file, the roles catalog
document, `workflow.toml`, `playbook.toml` — through the CLI and read the four messages side by
side. They come from one helper and must render identically apart from the accepted set and the
path.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T08:29:17Z] Elias Python:
  - Fixed at the shared engine — _unknown_key_violations (src/squads/_specmerge.py) now builds the fix hint as: use one of the accepted {what}s in v{squads.__version__}: {sorted(accepted)}, e.g. "use one of the accepted top-level keys in v0.14.0: [...]". Both callers (top-level key space, [selected] section space) inherit it unchanged.
  - empty_accepted_hint path (structurally-empty vocabulary, e.g. the playbook [selected] hint) deliberately omits the version — that hint states a fact true at every version, not a version-bound menu; recorded in the docstring.
  - Import: added `from squads import __version__` to _specmerge.py. squads/__init__.py imports only importlib.metadata, so no cycle; confirmed via a clean `uv run --all-extras pyright` (whole project) plus a direct `import squads._specmerge` — both clean.
  - Drove all four override kinds through the CLI in an isolated worktree (to stay clear of TASK-820s concurrent in-flight _roles/ edits in this tree): per-slug role (`sq role architect show`), roles catalog (`sq role catalog`), workflow, playbook (`sq check`) — all four render the same wording, version included, differing only in the accepted set and path.
  - Tests: existing hint-substring assertions untouched (unaffected fragment), added a version-presence test per key space (top-level + [selected]) asserting `__version__` is in the hint rather than the whole string. Targeted specmerge/workflow/playbook tests + tests/meta: 393 passed. pyright/ruff check/ruff format clean on the touched files and the whole project. sq check clean.
  - No change to docs/overrides.md — that carrier is TASK-815, left for the writer as scoped.
<!-- sq:discussion:end -->
