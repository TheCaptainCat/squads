---
id: TASK-716
sequence_id: 716
type: task
title: Shared override merge engine over raw spec mappings
status: Done
parent: FEAT-712
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-696:implements
- ADR-541
- EPIC-538
description: 'Loader-agnostic dict-level engine: splat resolution, deep recursive
  merge, selected deselect'
subentities:
- local_id: ST1
  title: Splat-ref resolution pass against the bundled base
  status: Done
  story: US3
- local_id: ST2
  title: Deep recursive merge at leaf granularity
  status: Done
  story: US1
- local_id: ST3
  title: 'selected deselect: apply, strip, record provenance'
  status: Done
  story: US2
- local_id: ST4
  title: Ordered entry point with fail-fast and collect-all modes
  status: Done
  story: US2
- local_id: ST5
  title: Closed top-level key space for the override document
  status: Done
  story: US2
- local_id: ST6
  title: Declared nesting bound on both recursive walks
  status: Done
  story: US3
created_at: '2026-07-31T13:19:12Z'
updated_at: '2026-07-31T16:22:46Z'
---
<!-- sq:body -->
## What to build

One shared, loader-agnostic override-merge engine that turns a bundled base document and a
project override document into the effective merged document. It operates entirely on **raw
parsed-TOML mappings** (`dict[str, Any]` in, `dict[str, Any]` out) and completes before any
pydantic model validation — the strictly-typed spec models set `extra="forbid"`, so an
unresolved splat token or a stray `[selected]` table sitting where a typed value is due would
be rejected as a type error before the engine ever got to resolve it (ADR-696 §4a, §4b).

Four mechanisms, the first three applied in one fixed order:

1. **Resolve splat-refs** against the bundled base only.
2. **Deep-merge** the override's declarations over the base.
3. **Apply each section's `selected` deselect**, then strip the `[selected]` table.
4. **Refuse an unrecognised top-level key** in the override document, on the same collected
   violation channel.

The caller then builds its spec model, runs its own validation, and runs the live-index
cross-check. That ordering is the whole reason `selected` needs no rulebook of its own: every
unsafe drop is caught by a check that already runs on the *resulting* spec (ADR-696 §4b).

### The closed top level closes a live fail-open

Mechanism 4 is not a guard for new behaviour — **it fixes a fail-open in the override system
that ships today**. Each loader hand-builds its spec model from an explicit payload of named
sections (`raw.get("items")`, `raw.get("statuses")`, …), so any *other* top-level key is dropped
in the gap between the parsed document and the model and `extra="forbid"` never sees it.
`_roles/_loader.py::_build_catalog` has the same shape, and `_roles/_resolver.py` skips unknown
keys by explicit design. Driven against the real loader: an override containing only
`override_base = "0.13.0"` plus a bogus section loads clean, with zero lint findings.

The consequence that makes it urgent is not the retired stamp key — it is that **a mistyped
section name is silently ignored**. `[item.task]` instead of `[items.task]` gives the adopter no
error and no effect: their entire override quietly does nothing, against a spec that is
perfectly valid and simply not the spec they wrote. Nothing downstream can see it, because the
mistake is a change that never happened. Build mechanism 4 as the fix for that case, not just as
a check on a key nobody writes any more (ADR-696 §4b).

### Home and dependencies

A new flat private module — `src/squads/_specmerge.py` — whose only internal dependency is
`squads._errors`. Three loaders will import it (`_workflow/_loader.py`,
`_roles/_loader.py`, and the playbook loader), so it cannot live inside any one of them
without a cycle. ADR-696 §5 places the merge "in `_loader.py`"; §4c is the more specific
statement — one engine shared by three loaders — and a shared module is the only home that
satisfies both. A different filename is acceptable; `squads._errors` as the sole internal
dependency is not negotiable.

Nothing in this task edits `_workflow/_loader.py`, `_roles/_loader.py`, or the playbook
loader. `_collect_additive_conflicts` / `_merge_override` stay exactly as they are; they are
retired by the dependent features, not here. Mechanism 4 is built and unit-tested at the
engine's boundary here; the loaders start *passing* their accepted top-level key set when they
are wired up, which is the dependent features' scope.

### The engine is loader-agnostic

It takes a base mapping, an override mapping, and the closed key sets its caller owns — the
deselectable section names and the accepted top-level keys — and knows nothing about which
document produced them, or what any of those names mean. In particular it does **not** own any
loader's floor checks — the roster-locked rule, the R1/R1′/R2 lifecycle floor, category-catalog
membership, drift stamping, the live-index cross-check. Those live in the loaders and are the
scope of the workflow-overridability and playbook-override features. Do not add a roster special
case, a category special case, or any spec-shaped knowledge to this module.

## Mechanism detail

### Deep recursive merge (US1)

- Tables recurse per key; a leaf value replaces its counterpart.
- Plain arrays are **leaves** — replaced wholesale, never element-merged. A `transitions` map
  recurses because it is a table; a `badges`, `fields`, `parents`, or `validators` list is
  replaced whole. Splat-refs are the opt-in for appending (below).
- An override supplies only the fields it changes; every other field of the shadowed entry
  survives untouched.

### Splat-refs (US3)

- `$(path)` splices the base value at *path* in as a single element.
- `$(*path)` spreads a base list's elements into the surrounding list — the idiom that makes
  `["$(*self)", <new>]` mean append.
- `$(self)` / `$(*self)` addresses the key currently being written, so the resolver must carry
  the current dotted path as it walks the override. Dotted paths address keyed tables
  elsewhere (`$(*items.task.validators)`).
- **`self` means the nearest enclosing *keyed* path, at any list depth.** A list position
  contributes nothing to the path, because a list index has no dotted name to contribute — so
  `self` inside a list, or inside a list inside a list, still means the key those lists hang from.
  This is definitional, not a special case: it is what "the key currently being written" already
  says. Three consequences, all intended — two `self` tokens at different list depths under one
  key resolve to the same base value; a `$(*self)` nested inside a sub-list spreads the key's list
  into that sub-list, permitted because the destination's shape is the models' plane and not the
  engine's; and spreading a base list that is **empty** yields just the new elements, since an
  empty list is a value the base holds and composes to nothing added, which is distinct from a
  *missing* key, which dangles. Compose-only also permits the same base list to be spread twice,
  duplicating it; nothing needs it to behave as a set (ADR-696 §4a).
- **A path segment is a TOML bare key** — `A-Za-z0-9_-`, one or more characters — so a path
  addresses exactly what TOML can key without quotes. A hyphenated key (`user-story`, `tech-lead`,
  the natural spelling for multi-word vocabulary here) is addressable, a leading digit is
  addressable, and a non-ASCII key is *not* — TOML bare keys are ASCII, so such a key is a
  **quoted** key and falls under the next bullet rather than being an arbitrary asymmetry. Anchor
  on TOML's own key definition rather than on an identifier shape: by the abbreviation rule a value
  the adopter may write literally has to stay expressible as a reference, and a path grammar
  narrower than the vocabulary the spec may declare silently withdraws that for a class of legal
  names.
- **A key that requires TOML quoting is not addressable, and that constraint binds *this
  project's* bundled documents rather than any adopter.** `.` is the path delimiter, so a key
  containing a dot is irreducibly ambiguous in a path, and a quoted-segment sub-grammar would be a
  second nested syntax for a case no document has. Leaving it out costs nothing for a structural
  reason: **resolution is base-only, so a path can only ever address a key of the bundled
  document.** An adopter's own vocabulary is never a path target — a brand-new key has no bundled
  counterpart and dangles by design however it is spelled, and an adopter declaring a hyphenated
  type addresses bundled paths from inside it perfectly well, because the hyphen sits in the
  destination and not in the path. So this is a constraint on squads' own key names, discharged by
  the standing guard in Testing rather than by a runtime check. What the guard buys is that an
  unaddressable key can never silently **mis-navigate** — `_dotted` joins on `.` and the lookup
  splits on `.`, so a dotted key would otherwise address the wrong path.
- Resolution targets the **base only**. No override value is ever a splat target, so there are
  no cycles and the merge is order-independent.
- Compose-only: a splat adds, never removes. Removal is `selected`'s job.
- **Token territory: a string is in token territory only if it *begins* with an unescaped `$(`** —
  one predicate, every string position in the document, keys as well as values. A string that
  merely *contains* `$(` somewhere after its first character is **data in both positions**: left
  verbatim, no violation, no escape required. This is the detection predicate, and it is narrower
  than "contains the sigil" on purpose — the sigil *is* POSIX command substitution and one of the
  three documents this engine serves carries command lines, so a playbook entry's
  `git commit -m "$(cat msg)"` has to merge through inert (ADR-696 §4a).
- **What territory *means* differs by position.** In a **value** it means the string is resolved or
  refused as malformed. In a **key** it means the string is **refused** — never resolved, never
  passed through. There is no defined splice-into-a-key operation: a path addresses a *value*, and
  a value is not a key, so a token in key position is not a feature being declined but a construct
  with no meaning, and the only thing it can be is a mistake.
- **A token is recognised only when it is the entire string value**, and the whole value means
  the whole value: leading or trailing whitespace, or a trailing newline, does not make a token.
  A value in token territory that is not a whole-value token is a *malformed token* (see
  Failure shape), not data and not a surviving literal.
- **An interpolation attempt stays literal.** `prefix = "text $(items.task.prefix)"` is data,
  not a violation — the grammar never offered interpolation, and the alternative is the shell
  collision above.
- `$$(` at the start escapes a string that must literally begin `$(`, unescaping to `$(` in the
  merged output **in both positions**; an escaped occurrence is never reported as surviving.
  Because only a **leading** `$(` ever needs escaping, no tool that writes a bundled string into an
  override file owes an escape duty — see the standing guard in Testing, which is what keeps that
  true.
- **Refusing a token-shaped key is a spelling requirement, not a restriction on vocabulary**, and
  that is what keeps the engine out of judging vocabulary, which it must never do. A project that
  genuinely wants a key spelled `$(items.task)` writes `$$(items.task)` and gets it; nothing is
  withdrawn, the requirement is only that vocabulary be spelled unambiguously in a document where
  `$(` is reserved. This is also the line between this refusal and the splice-shape criterion that
  was withdrawn: there, the adopter would have been left with a value writable literally but
  *inexpressible* as a reference and no escape to recover it. The test is whether the adopter keeps
  a way to say the thing — here they do, there they did not (ADR-696 §4a).
- **Deferring the key case to the models is not available.** For a value the models are a real
  backstop — fields typed, extras forbidden — which is exactly why shape belongs to them. For a key
  they deliberately are not: a section's keys *are* the open vocabulary, so the models accept any
  string. Driven: a spec declaring an item type literally named `$(items.task)` loads clean, mints a
  prefix and resolves a folder, and nothing downstream is in a position to notice. A token-shaped
  key is therefore the one place the engine's own refusal is the only thing standing between a typo
  and a minted vocabulary entry.

### `selected` deselect (US2)

- One top-level `[selected]` table keyed by section name. The key space is closed and
  code-supplied by the caller; an unknown section key fails closed.
- Each list is the **surviving** set with replace-wholesale semantics: keys of that section not
  named in the list are dropped from the merged mapping.
- `selected` carries no validation of its own. An entry naming a key absent from the merged
  section is inert — the engine adds no existence check, because the guardrail is the check
  that runs on the resulting spec.
- The `[selected]` table is consumed and stripped from the returned mapping.
- The engine returns **provenance**: which keys were dropped, from which section, by which
  `selected` list. The caller uses it so a floor violation traced to a deselect can say a
  missing key was dropped from a `selected` list rather than never declared. The engine does
  not format the caller's messages.

### The document's own top level is a closed key space (US2)

- The override document may carry only the top-level keys its caller declares — for the workflow
  and playbook documents, the section names. The **caller supplies the accepted set**; the engine
  knows nothing about what those names mean, exactly as it already knows nothing about
  `[selected]`'s section names. Same check, one key space up.
- **`[selected]` is accepted unconditionally, whether or not the caller names it.** It is the
  engine's *own* reserved key — the engine defines it, consumes it and strips it — so it is not part
  of the document's vocabulary and is not the caller's to declare. The general form, worth stating
  because it is what a caller cannot be expected to remember: **a key the engine reserves is never
  subject to the caller's accepted set.** Same principle as the sigil being reserved in every string
  position (ADR-696 §4b).
- An unrecognised top-level key is a **collected `MergeViolation`** naming the key and the
  accepted set. Keeping it on the engine's violation channel rather than letting a model raise it
  is deliberate: that is how the failure stays collectable in collect-all mode instead of
  arriving as a model error that stops the pass.
- It must be checked **at the raw-mapping layer, on the override's own top level, before the
  merge**. After the merge every base key is present, so there is nothing left to distinguish;
  and `extra="forbid"` is never reached at all, which is the whole reason this exists.
- A caller that does not close its top level supplies no accepted set and gets no check. **The
  roles loader is that caller**: a role override's top-level keys are the *fields of a role*, a
  set that grows release to release, so its resolver skips unknown keys on purpose for forward
  compatibility — an override written against a newer squads keeps working on an older one. The
  asymmetry is structural, not a harmonisation debt (ADR-696 §4b). Do not close the role
  override's top level and do not "fix" the resolver's skip.
- Consequence of that asymmetry, stated rather than smoothed: the retired `override_base` key
  written into a *role* override is ignored rather than refused, and the adopter learns of it
  from `sq check` reporting the file unstamped. That is the fail-safe direction, and nothing
  depends on the key because the stamp is a comment.

## Failure shape

Every failure is a clean `SquadsError`, never a traceback, and every message carries the
override path/origin the caller supplied plus the dotted path of the offending key.

Four of the splat failures are what the **grammar** can be wrong about, each a property of *the
token and its operator* rather than a claim about what shape a destination ought to hold
(ADR-696 §4a):

- **Dangling path** — `$(path)` / `$(*path)` naming a path absent from the base. `$(*self)` on a
  key with no base counterpart dangles too, and must fail: a brand-new custom key has no base
  list to append to, so `["$(*self)", x]` there is a mistake, not an empty append.
- **A spread whose base value is not a list** — `$(*path)` where the base holds a non-list.
  "Spread these elements" is undefined for a non-list, so the operator itself is unsatisfiable.
- **A spread with no surrounding list** — `$(*path)` as a whole value rather than a list element.
  Same reason: nothing to spread into.
- **A malformed or surviving token** — a value in token territory that is not a well-formed
  whole-value token: an unparsable path, an unclosed token, a double star, surrounding
  whitespace, a stray token left after resolution. Report it **as a malformed token**, quoting
  the path and what a path may contain — *not* as a surviving literal, which describes a
  different mistake and tells the author to do the one thing they already did. This is the most
  likely class of adopter mistake in the whole grammar, so it gets the most precise message.

Those four are about a **value** in token territory. A **key** in token territory is refused
outright, with two messages: a grammar-valid token used as a key reports *"used as a key — keys are
never a splat target"*, because resolving it is undefined rather than malformed; a malformed
token-shaped key reports the malformed-token message. Both are collected violations on the same
channel as everything else, carrying the dotted path of the key. Consistency argues the same way as
the reasoning above: an unrecognised key at the document's *top* level already fails closed, so
passing the identical mistake at a nested level would make the verdict a function of depth.

A fifth refusal is owed for a reason that is not about the grammar at all:

- **Nesting beyond a declared bound** — a document nested deeper than the engine will walk is
  refused, naming the dotted path where the bound was hit. This is not a policy about how deep a
  spec may be; it is what keeps an interpreter recursion limit from surfacing as a traceback.
  Specify the bound by **two properties rather than a number**, and leave the constant to the
  implementer with a comment stating both: far above anything a hand-authored document reaches
  (the deepest key path in any bundled document is four levels), and far below the interpreter's
  own headroom, with room for the copy the merge performs at each level. It binds **both** walks —
  the override's resolution and the merge's traversal of the untouched base — and it must be
  checked *before* recursing or copying, because a deep base subtree fails inside the copy rather
  than in the engine's own frame, so a guard on the resolver alone would miss it. The refusal goes
  on the same collected violation channel as everything else, so it collects in a lint-style report
  instead of aborting the pass.

**The no-traceback contract above stays unqualified, and this is why.** "Either it succeeds or it
is refused cleanly" is a promise about what an invocation does to the person running it, and a wall
of Python satisfies neither branch. The engine's inputs are adopter-authored files by design, and
the TOML parser accepts a document far deeper than the walk survives — a single legal line of
dotted keys reaches it — so nothing upstream can guard this and the guard has to live here. The fix
is one counter and one comparison, so the honest move is to make the contract true rather than to
narrow it: weakening a stated invariant to match code that could cheaply satisfy it is how
invariants stop meaning anything (ADR-696 §4a).

**A splice is never checked against the shape of the key it lands on.** A splat-ref is an
abbreviation for a value the adopter could have written literally, and is held to the same
standard as that expansion — no stricter and no looser. An abbreviation refused where its
expansion is accepted is a broken abbreviation: the adopter could not express through a splice a
value they may write out longhand, and the two forms would produce the same merged mapping with
different verdicts. `deep_merge` knowingly lets a hand-written leaf replace its counterpart with
a different shape, so a shape criterion on splices would be strictly stricter than the literal.
Nothing is unguarded by this: a splice can only ever produce a value the bundled document itself
holds, landing at the wrong key, and the strictly-typed models reject exactly that with a
per-field error. Shape is the models' plane, composition is the engine's — the same boundary
that keeps the loaders' floor out of this module (ADR-696 §4a).

Two more cases on the same collected channel:

- **An unrecognised top-level key** in the override document — named, alongside the accepted set.
- **A misshapen `[selected]` declaration** — an unknown section key, or a keep value that is not
  a list of strings.

And the one case that must *not* fail: **`$$(` escaping a literal**, which resolves to `$(` and
is never reported as surviving.

Both calling modes must be expressible without duplicating a line of logic, mirroring the
two-mode shape `_collect_additive_conflicts` already has: fail-fast (raise on the first
violation, for the `open_service` load path) and collect-all (every violation returned, one
per offending path with a fix hint, for a lint-style report).

## Acceptance

Each line below is FEAT-712's acceptance criterion read at the engine's own boundary, since
wiring the engine into a loader is explicitly out of this feature's scope.

- **Deep-merge, not replacement.** An override touching one field of a base entry produces a
  merged entry in which every other field of that entry is unchanged.
- **Arrays are leaves.** An override supplying a plain array replaces the base array wholesale;
  no element is unioned in.
- **Append is one line.** `["$(*self)", <new>]` yields the base list's elements followed by the
  new one, and a change to the base list flows through on the next merge without touching the
  override.
- **No-op on an empty override.** Merging an empty override over a base returns a mapping equal
  to the base — same keys, same values, same nesting, nothing added and nothing stripped.
- **Order-independence.** Two overrides of unrelated keys, applied in either order, produce
  equal merged mappings. Assert this over a base that includes a splat target, so the property
  is exercised where it could actually break.
- **Deselect shrinks.** A section's `selected` list leaves exactly the named keys and drops the
  rest; the `[selected]` table is absent from the returned mapping; the provenance record names
  each dropped key and the list that dropped it.
- **Unknown `[selected]` section key fails closed** with a `SquadsError` naming the key and the
  closed set of accepted section names.
- **Unknown top-level key fails closed as a collected violation.** An override whose top level
  carries a key outside the caller's accepted set — a mistyped section name, or the retired
  `override_base` — produces a violation naming the key and the accepted set, and is reported
  beside the other violations in collect-all mode rather than raised from a model. Assert the
  mistyped-section case explicitly: `[item.task]` for `[items.task]` must not merge clean.
- **No accepted set, no check.** Called without an accepted top-level set, the engine passes
  every top-level key through untouched.
- **`[selected]` survives the top-level check without being declared.** An override carrying a
  `[selected]` table merges and deselects normally when an accepted set is supplied that does *not*
  list `selected` — asserted against both derivations a loader will actually reach for: the base
  document's own top-level keys, and the six section names.
- **Keys and values share one token-territory predicate**: a string is in token territory iff it
  begins with an unescaped `$(`.
- **A string containing `$(` after its first character is data in both positions**, left verbatim
  with no violation. A real playbook command line (`cmd = 'git commit -m "$(cat msg)"'`) merges
  byte-identical; an interpolation-shaped value (`"text $(items.task.prefix)"`) stays literal; a key
  such as `weird-$(x)-key` passes through.
- **A key in token territory is refused**, never resolved and never passed through: a grammar-valid
  token reports *"used as a key — keys are never a splat target"*, a malformed token-shaped key
  reports the malformed-token message, and both are collected violations carrying the key's dotted
  path.
- **`$$(` unescapes to `$(` in a key exactly as in a value**, so a project can still declare a key
  literally named `$(…)` — the refusal is a spelling requirement, not a restriction on vocabulary.
- **A shape-changing splice is accepted.** A splice whose base value is a table landing on a key
  the base holds as a scalar (and the reverse) produces the merged value with no violation — the
  shape question belongs to the models.
- **A malformed token is diagnosed as one.** A value in token territory that is not a whole-value
  token reports a malformed-token violation quoting the path, not a surviving-literal violation.
- **A path addresses any TOML bare key.** A hyphenated and a digit-leading base key are both
  addressable by an explicit path; a base key needing TOML quotes is refused as a malformed path
  rather than resolved against the wrong path.
- **`self` is the nearest enclosing keyed path at any list depth.** Two `self` tokens at different
  list depths under one key resolve to the same base value; spreading an empty base list adds
  nothing; spreading one base list twice duplicates it.
- **Nesting past the bound is refused cleanly, from either side.** A deeply nested override *and* a
  deeply nested untouched base each produce a violation naming the dotted path — never a
  `RecursionError`, and never from inside the copy.
- **Each of the five splat failure cases fails closed**, and in collect-all mode every violation
  in one override is reported together rather than stopping at the first.

## Testing

Unit tests at the engine boundary plus tests driven off the **real bundled mappings** as the
base (`src/squads/_specs/workflow.toml`, `roles.toml`, `playbook.toml`, read as raw dicts) —
that is what proves the engine is loader-agnostic while still being exercised against the
documents it will actually merge. The playbook base is where `["$(*self)", { … }]` on an array
of tables gets its coverage: the override must use TOML's **inline-array** form, because the
`[[…]]` header form has no slot for a token. Heterogeneous arrays are valid TOML 1.0 and
`tomllib` accepts the mixed string-and-table list, so assert against a real parsed override
string rather than a hand-built dict for at least one case. The playbook base is also where the
inert-shell-content case belongs: take a `commands` entry as it actually ships.

Prefer a table-driven test per input *position* (dict key, dict value, list element, nested list
element, `[selected]` value, `[selected]` section, document top level) crossed against a fixed
set of shapes — string, int, bool, empty list, list of non-strings, table, token, malformed
token, escaped token, sigil-after-first-character — asserting for each either a named violation
or an exact value. One example per implemented branch proves the mechanism, which is the thing
least in doubt; a family of shapes at one position is what reaches the shapes nobody considered,
and it is cheap here because the engine is a pure function.

The ask is the **cross-product**, and the distinction is not pedantic. A table parametrised over the
dict-value position with the other positions covered by hand-written examples is *positional*
coverage: every position appears, but only one of them is crossed against the shape family, so the
combinations nobody thought of stay unreachable — and a missing crossing at the document's top level
is exactly how a legal `[selected]` override came to be refused. Parametrise the positions and the
shapes as two axes, and let the table produce every pair.

Add one `tests/meta` scan over the bundled documents asserting **two** properties, the same shape
as the existing stray-ticket-reference and module-level mutable-state scans:

1. **No bundled string value begins with an unescaped `$(`.** Walk every string value in each
   bundled TOML. Zero today across all three, verified.
2. **Every bundled key is a TOML bare key** (`A-Za-z0-9_-`). Walk every key at every depth. Already
   true of all three documents — 353, 77 and 131 keys respectively — so the guard passes as
   written.

**Comment both properties as load-bearing**, because each is the only thing standing under a rule
stated elsewhere as free. Property 1 is what keeps the writers' escape duty vacuous: remove it and
the duty reappears at every writer (`sq override scaffold`, the diff path, the playbook writers),
along with a written file that differs from its bundled source on every such line. Property 2 is
what makes an unaddressable key unreachable rather than merely unlikely: remove it and a quoted or
dotted bundled key can silently mis-navigate a path instead of failing.

`tests/meta`'s module-level mutable-state guard fires on any new module-level dict or list —
if a closed key set or a token pattern lands as one, allowlist it as a code constant rather than
restructuring around the guard, and run `tests/meta` before handing back.

## Conventions

- Name tests by behaviour. No ticket or item IDs anywhere in `src/` or `tests/` — the pointer
  belongs in this task's discussion, not in the code.
- No `eval` and no user-supplied code path. Splat-refs are a closed-grammar path splice
  resolved in a single pass (ADR-541 Axis B, ADR-696 §4a).
- Strict gate, with the extras: `uv run --all-extras pyright && uv run --all-extras ruff check
  . && uv run --all-extras ruff format --check .`.
- Type aliases use PEP-695 `type X = …`, not bare assignment.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 716 add-subtask "<title>"`; track with `sq task 716 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Splat-ref resolution pass against the bundled base

<!-- sq:subtask:ST1:body -->
The resolution pass that walks an override mapping and replaces every splat token with a value
read from the **base** mapping, before any merging and before any model validation.

Grammar (closed, no `eval`):

- `$(path)` splices the base value at *path* in as a single element.
- `$(*path)` spreads a base list's elements into the surrounding list; `["$(*self)", <new>]` is
  therefore append.
- `$(self)` / `$(*self)` addresses the key currently being written, so the walker carries the
  current dotted path. Dotted paths address keyed tables elsewhere, e.g.
  `$(*items.task.validators)`.
- **`self` means the nearest enclosing *keyed* path, at any list depth** — a list position
  contributes nothing to the path, because a list index has no dotted name to contribute. So `self`
  inside a list, or a list inside a list, still means the key those lists hang from; two `self`
  tokens at different depths under one key resolve alike; and a `$(*self)` nested in a sub-list
  spreads the key's list into that sub-list, which is permitted because destination shape is the
  models' plane. Definitional, not a special case (ADR-696 §4a).
- **A path segment is a TOML bare key** — `A-Za-z0-9_-`, one or more characters. Hyphenated
  (`user-story`, `tech-lead`) and digit-leading keys are addressable; a non-ASCII key is not,
  because TOML bare keys are ASCII, so it is a quoted key and unaddressable by rule rather than by
  accident of a character class. Do not re-derive a narrower identifier shape: by the abbreviation
  rule, a value the adopter may write literally must stay expressible as a reference.
- **A key requiring TOML quotes is unaddressable, and the constraint binds the bundled documents,
  not any adopter.** `.` is the path delimiter, so a dotted key is irreducibly ambiguous in a path.
  Resolution is base-only, so a path can only ever address a bundled key: an adopter's own
  hyphenated type is never a path target (it dangles by design, however spelled) and addresses
  bundled paths from inside itself perfectly well, the hyphen being in the destination not the path.
  The protection against silent **mis-navigation** — `_dotted` joins on `.`, the lookup splits on
  `.` — is the standing `tests/meta` guard that every bundled key is a bare key, not a runtime
  check here.
- **The sigil is reserved in every string position — keys as well as values — and token territory
  is one predicate in both: a string is in token territory iff it *begins* with an unescaped
  `$(`.** A string that merely *contains* `$(` after its first character is data **in both
  positions**, left verbatim, no violation, no escape required. The sigil is POSIX command
  substitution and the playbook's `commands` entries are command lines, so
  `cmd = 'git commit -m "$(cat msg)"'` must merge through inert (ADR-696 §4a).
- **What territory means differs by position.** In a **value**: resolve, or refuse as malformed. In
  a **key**: **refuse** — never resolved, never passed through, never substituted. There is no
  splice-into-a-key operation to define, because a path addresses a value and a value is not a key,
  so a token in key position is a construct with no meaning rather than a feature being declined.
  Two messages: a grammar-valid token used as a key reports *"used as a key — keys are never a
  splat target"* (undefined, not malformed); a malformed token-shaped key reports the
  malformed-token message. Both are collected violations carrying the key's dotted path.
- Refusing a token-shaped key is a **spelling requirement, not a restriction on vocabulary** — the
  escape works in key position too, so a project wanting a key literally named `$(items.task)`
  writes `$$(items.task)` and gets it. Nothing is withdrawn, which is exactly why this refusal
  stands where the splice-shape criterion fell: that one would have left a value writable literally
  but inexpressible as a reference with no escape to recover it. And the key case cannot be left to
  the models: a section's keys *are* the open vocabulary, so they accept any string — a type
  literally named `$(items.task)` loads clean and mints a prefix and a folder. This refusal is the
  only thing between a typo and a minted vocabulary entry.
- A token is recognised only when it is the **entire** string value, and the whole value means
  the whole value — leading or trailing whitespace, or a trailing newline, does not make a token.
  Match the pattern against the full string, not to a `$`-anchor that a trailing newline slips
  past.
- An interpolation attempt stays literal: `prefix = "text $(items.task.prefix)"` is data, not a
  violation. The grammar never offered interpolation.
- `$$(` at the start escapes a string that must literally begin `$(`, unescaping to `$(` in the
  output **in both positions**; an escaped occurrence is never reported as surviving. Only a
  **leading** `$(` ever needs escaping, so no writer of override files owes a standing escape duty.

Rules that constrain the implementation:

- Resolve against the base only — no override value is ever a splat target. This is what
  removes cycles and makes the merge order-independent; it must not be relaxed for
  convenience.
- Compose-only: a splat adds and never removes an element.
- Single pass. A resolved value is not itself re-scanned for tokens.
- **One predicate, changed in one place.** The wide "an unescaped `$(` anywhere in the string" check
  in the literal-string path is what the narrowed predicate replaces, and today it refuses a value it
  must pass: a `commands` entry such as `git commit -m "$(cat msg)"`, which does not begin with the
  sigil and is therefore data. Note the contrast, because it is easy to over-correct: a value like
  `$(date +%s) --flag` *does* begin with the sigil, so it is in token territory and is not a
  whole-value token — it is a **malformed token** and stays refused. Moving that one check from
  "contains" to "begins with"
  fixes the value side and narrows the over-wide key side in the same edit — the key side then needs
  its position's *meaning* wired up (refuse, with the two messages above), not a second predicate of
  its own. Do not fix the two positions separately.

Fails closed with a `SquadsError` naming the offending dotted path on **four cases** — everything
the grammar itself can be wrong about, each a property of the token and its operator rather than a
claim about the destination (the fifth refusal, nesting past the walk's bound, is not a grammar
question and lives in ST6):

1. a dangling path — including `$(*self)` on a key with no base counterpart, since a brand-new
   custom key has no base list to append to, so that is a mistake and not an empty append;
2. a spread whose base value is not a list;
3. a spread with no surrounding list — `$(*path)` as a whole value rather than a list element;
4. a malformed or surviving token — a value in token territory that is not a well-formed
   whole-value token (unparsable path, unclosed token, double star, surrounding whitespace, a
   stray token left after the pass). Report it **as a malformed token**, quoting the path and
   what a path may contain; reporting it as a surviving literal names a different mistake and
   tells the author to do what they already did.

**A splice is never checked against the shape of the key it lands on.** A splat-ref is an
abbreviation for a value the adopter could have written literally and is held to the same
standard as that expansion — no stricter, no looser. Shape is the models' plane, composition is
this pass's (ADR-696 §4a).

Acceptance: append via `["$(*self)", <new>]` yields the base elements followed by the new one;
a later change to the base list flows through with the override untouched; each of the four
failure modes fails closed rather than producing a value, and the fourth reports a malformed
token rather than a surviving literal; `$$(foo)` survives as the literal `$(foo)`; a real
playbook command line containing `$(cat msg)` after its first character survives byte-for-byte
with no violation; a shape-changing splice (a table spliced onto a key the base holds as a
scalar, and the reverse) is accepted with no violation.

Then the two positions, asserted against the one predicate:

- a string containing `$(` after its first character is data **in both** — `cmd = 'git commit -m
  "$(cat msg)"'` merges byte-identical as a value, and a key such as `weird-$(x)-key` passes
  through;
- a key in token territory is **refused**: a grammar-valid token as a key reports *"used as a key —
  keys are never a splat target"*, a malformed token-shaped key reports the malformed-token message,
  and neither is resolved or passed through;
- `$$(items.task)` **as a key** unescapes to the literal key `$(items.task)`, exactly as the same
  string does as a value;
- every key-position refusal is a collected violation carrying the key's dotted path, reported
  beside the others in collect-all mode.

Also pin the grammar's edges, since each was reachable and undecided:

- an explicit path addressing a **hyphenated** base key and one addressing a **digit-leading** base
  key both resolve;
- a path segment that is not a TOML bare key is refused as a malformed path — never resolved
  against a different path;
- `$(*self)` inside a nested list spreads the **enclosing key's** list into that sub-list, and two
  `self` tokens at different list depths under one key resolve to the same base value;
- spreading an **empty** base list adds nothing (distinct from a missing key, which dangles), and
  spreading one base list twice duplicates it.

Cover the array-of-tables case against a real parsed TOML override using the inline-array form
(`roles = ["$(*self)", { … }]`) — the `[[…]]` header form has no slot for a token.

Built first even though it maps to the third story: steps 2 and 3 both consume its output.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Deep recursive merge at leaf granularity

<!-- sq:subtask:ST2:body -->
The recursive merge of a resolved override mapping over the base mapping.

- Tables recurse per key. A leaf value replaces its counterpart.
- Plain arrays are **leaves** — replaced wholesale, never element-merged. A `transitions` map
  recurses because it is a table; a `badges`, `fields`, `parents`, or `validators` list is
  replaced whole. Appending without restating is the splat-ref's job, not a silent union: a
  unioned list is a value nobody declared and nobody can read back from the TOML.
- The override declares only what it changes; every other key of a shadowed entry survives.

Acceptance: an override touching one field of a base entry leaves every other field of that
entry unchanged in the result; an override supplying a plain array replaces the base array
wholesale with no element unioned in; merging an empty override over the base returns a mapping
equal to the base — same keys, values, and nesting, nothing added and nothing stripped.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — selected deselect: apply, strip, record provenance

<!-- sq:subtask:ST3:body -->
Applying the deselect after the merge, then removing its declaration from the mapping.

- One top-level `[selected]` table keyed by section name. The accepted key set is closed and
  supplied by the caller (the workflow loader's is `items`, `statuses`, `lifecycles`,
  `collections`, `subentity_kinds`, `roles`); the engine holds no section vocabulary of its own.
  An unknown key fails closed with a `SquadsError` naming it and the accepted set.
- Each list is the **surviving** set, replace-wholesale: keys of that section not named in the
  list are dropped from the merged mapping. The point of the mechanism is to shrink.
- No validation of its own. An entry naming a key absent from the merged section is inert — the
  guardrail is the check that runs on the resulting spec, which the caller runs after the
  engine returns.
- The `[selected]` table is consumed and stripped, because the spec models set `extra="forbid"`
  and would otherwise reject it.
- Return **provenance** alongside the merged mapping: which keys were dropped, from which
  section, by which list. This is the one thing `selected` genuinely owes — a caller's floor
  violation traced to a deselect has to be able to say the missing key was dropped from a
  `selected` list rather than never declared, or the adopter cannot see their own line caused
  it. The engine supplies the record; the caller formats its own message.

The unknown-section-key check here and the document's closed top level (ST5) are the same check
over two key spaces — a mapping, a caller-supplied accepted set, one collected violation naming
the key and the set. Factor one helper and call it twice rather than writing the rule twice; the
engine's ignorance of what the names mean is what makes that possible.

Acceptance: a `selected` list leaves exactly the named keys and drops the rest; the returned
mapping has no `[selected]` key; the provenance names each dropped key against the list that
dropped it; an unknown section key raises.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Ordered entry point with fail-fast and collect-all modes

<!-- sq:subtask:ST4:body -->
The public surface of `src/squads/_specmerge.py`: one entry point that runs the steps in the
fixed order and reports failures in either of the caller's two modes.

Order, which is the guarantee the dependent loaders are built on: check the override's own top
level against the caller's accepted key set (ST5), resolve splat-refs against the base,
deep-merge, apply `selected`, strip `[selected]`, return. The caller then builds its spec model,
runs its own validation, and runs the live-index cross-check. Nothing later in the pipeline may
be reordered ahead of the resolution pass — the strictly-typed models would reject an unresolved
token as a type error before it could be resolved. The top-level check goes first because it is
the only point at which the override's own top level is still distinguishable from the base's.

Signature is the implementer's call, but it takes the base mapping, the override mapping, the
closed set of deselectable section names, the accepted set of top-level keys (omitted by a caller
whose top level stays open — see ST5), and an origin label for messages (the override path, which
the engine never reads from disk itself), and it returns the merged mapping plus the provenance
record plus the collected violations.

Two calling modes, expressible without duplicating a line of logic — the same shape
`_collect_additive_conflicts` already has: fail-fast raises on the first violation for the load
path, collect-all returns every violation, one per offending dotted path with a fix hint, for a
lint-style report. Every raise is a clean `SquadsError` carrying the origin label and the
dotted path; never a traceback.

Acceptance: two overrides of unrelated keys applied in either order produce equal merged
mappings — assert it over a base that includes a splat target, so the property is exercised
where it could actually break; an empty override is a no-op; an override carrying several
independent violations reports all of them together in collect-all mode and stops at the first
in fail-fast mode, and a top-level-key violation is collected beside the others rather than
short-circuiting the rest of the report.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Closed top-level key space for the override document

<!-- sq:subtask:ST5:body -->
The override document's top level becomes a closed key space, checked at the raw-mapping layer
(ADR-696 §4b).

This closes a fail-open in the override system as it ships today, and the case that matters is
not the retired stamp key — it is the mistyped section name. Each loader hand-builds its spec
model from an explicit payload of named sections, so any other top-level key is dropped in the
gap between the parsed document and the model and `extra="forbid"` never sees it: `[item.task]`
written for `[items.task]` produces no error and no effect, and the adopter's entire override
quietly does nothing against a spec that is perfectly valid and simply not the one they wrote.
Nothing downstream can catch it, because the mistake is a change that never happened. Driven
against the real loader, an override containing only `override_base` plus a bogus section loads
clean with zero lint findings.

The mechanism:

- The caller supplies the **accepted set of top-level keys**; the engine knows nothing about what
  those names mean. For the workflow and playbook documents that is the section names. Same shape as
  `[selected]`'s closed section-name set one key space down (ST3) — factor one helper, call it twice.
- **`[selected]` is accepted unconditionally, without the caller having to include it in the
  accepted set.** It is the engine's own reserved key: the engine defines it, consumes it and strips
  it, so it is not part of the document's vocabulary and it is not the caller's to declare. Do not
  satisfy this by documenting that callers must remember to add it — a caller passing the obvious
  accepted set must not be punished for it.
- **The general rule, because that is why this was missable: a key the *engine* reserves is never
  subject to the caller's accepted set.** It is the same principle as the sigil being reserved in
  every string position — the engine's own reservations bind everywhere and are not vocabulary.
  Stating it means the next reserved key does not repeat this (ADR-696 §4b).
- Check the **override's own top level, before the merge**. After the merge every base key is
  present and there is nothing left to distinguish.
- An unrecognised key is a **collected `MergeViolation`** naming the key and the accepted set,
  deliberately on the engine's violation channel rather than left to a model: that is what keeps
  it collectable in collect-all mode instead of arriving as a model error that halts the pass.
- A caller that supplies no accepted set gets no check, and every top-level key passes through.
  **The roles loader is that caller.** A role override's top-level keys are the *fields of a
  role*, a set that grows release to release, so `_roles/_resolver.py` skips unknown keys on
  purpose for forward compatibility — an override written against a newer squads keeps working on
  an older one. That asymmetry is structural, not a harmonisation debt: do not close a role
  override's top level and do not change the resolver's skip.
- Consequence of the asymmetry, stated rather than smoothed: the retired `override_base` key in a
  *role* override is ignored rather than refused, and the adopter learns of it from `sq check`
  reporting the file unstamped. That is the fail-safe direction and nothing depends on the key,
  because the stamp is a comment.

Acceptance: an override whose top level carries `[item.task]` instead of `[items.task]` produces
a violation naming `item` and the accepted set, and does not merge clean; a retired
`override_base` key at the top level of a document with a closed top level does the same; the
violation is reported beside other violations in collect-all mode and raised as a clean
`SquadsError` in fail-fast mode; called with no accepted set, the same override passes every
top-level key through untouched.

And the reserved key, asserted against the two derivations a loader will actually reach for rather
than against a spelling that happens to work: an override carrying a `[selected]` table merges and
deselects normally when the accepted set is **the base document's own top-level keys**, and again
when it is **the six section names** — neither of which contains `selected`. A requirement that only
one spelling of the accepted set satisfies is a requirement living in the tests' folklore, not in the
engine.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Declared nesting bound on both recursive walks

<!-- sq:subtask:ST6:body -->
A declared nesting bound on both of the engine's recursive walks, so a document deeper than the
engine can walk is refused instead of raising a `RecursionError` (ADR-696 §4a).

It sits here rather than under either walk because **it binds both**: the override's splat
resolution and the merge's traversal of the untouched base. Splitting it would leave the copy side
easy to forget, and the copy side is the half that fails outside the engine's own frame.

- **Two properties, not a number.** The constant is the implementer's call, with a comment stating
  both: far above anything a hand-authored document reaches — the deepest key path in any bundled
  document is four levels — and far below the interpreter's own headroom, with room for the copy the
  merge performs at each level.
- **Checked before recursing or copying**, on every level of both walks. This is load-bearing, not a
  detail of placement: a deep *untouched base* subtree blows up inside the copy rather than in the
  engine's own frame, so a bound applied only to the resolver misses it entirely.
- **On the collected violation channel**, naming the dotted path where the bound was hit, so it
  reports beside the other violations in a lint-style pass instead of aborting it.
- Reachable from an ordinary document: `tomllib` accepts a single legal line of dotted keys nesting
  thousands deep, so the parser cannot be the guard and nothing upstream of the engine can be.

The reason this is a bound rather than a caveat: the no-traceback contract in Failure shape stays
**unqualified**. "Either it succeeds or it is refused cleanly" is a promise about what an invocation
does to the person running it, and a wall of Python satisfies neither branch. The inputs are
adopter-authored files by design, and the fix is one counter and one comparison — so make the
contract true rather than narrowing it. Weakening a stated invariant to match code that could
cheaply satisfy it is how invariants stop meaning anything.

Acceptance: an override whose nesting exceeds the bound produces a violation naming the dotted path
where it was hit, in both calling modes, and no `RecursionError` escapes; a base subtree deeper than
the bound that the override never touches does the same, refused before the copy rather than from
inside it; a document at the bundled documents' own depth, and well beyond it, merges normally; the
constant carries a comment stating the two properties that fix it.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-31T13:46:18Z] Elias Python:
  - Built src/squads/_specmerge.py: merge_override(base, override, section_names, origin, collect_all=) runs resolve_splat_refs -> deep_merge -> apply_selected in order; only internal dep squads._errors.
  - MergeViolation/Deselection/MergeResult dataclasses; all three mechanisms always collect violations, merge_override alone decides raise-first vs return-all — no duplicated logic.
  - 4 new test files under tests/unit/ (100 tests incl. real bundled workflow.toml/playbook.toml fixtures, incl. the inline-array  playbook case). tests/meta clean, no allowlist entry needed (no module-level mutable state added).
  - Falsified 5 targeted mutations (star-spread append-not-extend, array-union-not-replace, selected keep/drop inverted, fail-fast/collect-all inverted, escape-scan disabled) — each reddened the expected tests, reverted, back to green.
  - Gates clean: pyright/ruff check/ruff format all --all-extras. Did not touch any loader; TASK-716 left InProgress for you to move to InReview.
- [2026-07-31T13:46:32Z] Elias Python:
  - Correction: previous comment lost the token to shell expansion — the playbook test covers the inline-array $(*self) case, e.g. roles = ["$(*self)", { slug = "custom-role", ... }].
- [2026-07-31T13:48:35Z] Catherine Manager:
  - Full suite green on the engine (2175 passed, 6 skipped) and all four fast gates clean, but two defects found by reading and driving the code, neither caught by the new tests.
  - A misshapen `[selected]` value fails OPEN. `apply_selected` does `set(keep)` without checking that `keep` is a list, so `selected.items = "task"` (a bare string, the obvious typo for `["task"]`) becomes the character set {t,a,s,k}, matches no key, and silently drops every item type — zero violations, three deselections, `task` itself gone. A shape mismatch in an adopter's override must fail closed, and this is the most damaging direction it could fail in.
  - The merged result aliases the bundled base. `deep_merge` starts from `dict(base)`, a shallow copy, so any table the override does not touch is the same object as the base's. Mutating the merged mapping mutates the bundled spec for the process lifetime — verified. This directly undermines the seam FEAT-714 is built on (bundled stays a module-level immutable, merged lives in the request context), so it has to be closed here rather than in the loaders.
- [2026-07-31T13:55:31Z] Elias Python:
  - Fixed both defects in src/squads/_specmerge.py.
  - 1) apply_selected: added _validate_selected_shape — fails closed (collected) on selected not a table, a keep value not a list, or a keep list with a non-string element — before set(keep) ever runs. A bare-string keep (items = "task") now reports a MergeViolation naming the shape problem instead of dropping every key.
  - 2) deep_merge: rebuilt to never alias base — untouched base values are deepcopy'd in, recursed tables are fresh by construction, and an override value that wins outright (leaf or wholesale-replaced array) is deepcopy'd too. Cost: one deepcopy per leaf value ever produced, no compounding across recursion depth — spec docs are small and loaded once per request, so this is the honest fix, not a contortion.
  - Added 6 regression tests (2 in test_specmerge_deep_recursive_merge.py, 4 in test_specmerge_selected_deselect.py) reproducing both reports verbatim (bare-string keep dropping everything; merged["items"] is base["items"]). Falsified both fixes: reverted each to the reported-broken behavior, watched the new tests redden with the exact symptom described, restored, watched green.
  - Gates clean (--all-extras): pyright 0 errors, ruff check clean, ruff format clean, pytest tests/unit/test_specmerge_*.py + tests/meta = 106 passed. No disagreement — both were real, worth fixing exactly as described. Left TASK-716 InProgress; did not touch any loader or anything under squads/ by hand.
- [2026-07-31T14:00:40Z] Elias Python:
  - Fixed the key-ordering regression in deep_merge: it now walks base first (all base keys, in base order — untouched ones deep-copied, shared ones merged/overwritten in place) then appends override-only keys in override order. Verified one level down too — the recursion has the same two-loop shape, so a nested table was reordering the same way; fixed by the same construction (it's the same function, called recursively).
  - Reproduced your probe (['a','items','z'] -> ['a','z','items'] before the fix) plus a nested-table case; both now preserve order.
  - Added 2 regression tests to test_specmerge_deep_recursive_merge.py pinning order at the top level and one level down. Falsified: reverted to the old base-loop-then-override-loop construction, both tests reddened with the exact symptom (shared key relocated to the end / nested table reordered), restored, both green.
  - Gates clean (--all-extras): pyright 0 errors, ruff check/format clean, pytest tests/unit/test_specmerge_*.py + tests/meta = 108 passed. Ordering does matter here per your reasoning (FEAT-713 will iterate the merged mapping) — no disagreement, fixed as scoped. TASK-716 left InProgress; no loader or squads/ file touched by hand.
- [2026-07-31T14:17:29Z] Paul Reviewer:
  - Reviewed on REV-722 (ChangesRequested): 10 findings, 3 medium, 7 low, every one reproduced by driving the module. The three defects reported earlier are all verified fixed, and fixed wider than the exact case reported.
  - The mediums: a selected list whose section is present but not a table silently does nothing (F1, the one deselect failure mode nothing downstream can see); the splice half of the stated type-mismatch failure case is unimplemented (F2); an out-of-grammar splat path is misdiagnosed as a surviving literal (F3). F4-F9 are low: tokens and escapes in key positions are never scanned, the token regex accepts a trailing newline, a pathological nesting depth raises RecursionError rather than SquadsError, two docstring claims are broader than the code, and nested-list $(*self) is undefined.
  - F10 concerns the test suite's shape rather than any line of it: one example per implemented branch, so it confirms the mechanisms and cannot reach an unconsidered input shape — which is where all three original defects and F1-F9 live. Table-driven shapes per input position is the concrete ask.
  - @python-dev the findings carry reproductions; @architect F2 and F3 each need one ADR-696 line before they can be closed as code. Nothing edited in src/ or tests/ and nothing committed by me.
- [2026-07-31T14:40:31Z] Olivia Lead:
  - Restated the spec against ADR-696 §4a/§4b. §4a: the splice-shape criterion is withdrawn — a splat-ref is an abbreviation held to the same standard as its expansion, so the failure set is exactly four (dangling path; spread against a non-list; spread with no surrounding list; malformed or surviving token, reported AS malformed), and shape stays with the models.
  - Token territory narrows to a value that BEGINS with an unescaped sigil: a value containing it later is data, verbatim, no escape. That is what keeps a playbook commands line inert. Interpolation stays literal; only a leading sigil is ever escaped, so no writer owes an escape duty; grammar and escape are value-only, keys are never resolved (closes the key-position question).
  - New ST5: the override document top level becomes a closed key space per §4b — caller-supplied accepted key set, unrecognised key as a collected MergeViolation, checked at the raw-mapping layer before the merge. This closes a fail-open in the shipped loaders, and the case to build against is the mistyped section name that silently does nothing, not the retired stamp key. A role override top level stays open by design.
  - Testing gained a tests/meta guard: no bundled document holds a string value beginning with an unescaped sigil, commented as load-bearing (remove it and the escape duty reappears at every writer). Plus table-driven shapes per input position. ST1/ST3/ST4 bodies updated to match; ST1 and ST3 carry acceptance that has no code yet, so their Done marks are stale for the new lines — @manager that reopening is yours to sequence.
- [2026-07-31T14:43:12Z] Catherine Manager:
  - Reopened ST1: the token-territory narrowing (ADR-696 §4a) corrects behaviour ST1 already delivered, so its Done was stale — it carried acceptance with no matching code.
- [2026-07-31T14:53:50Z] Elias Python:
  - Addressed REV-722's F1, F3-F10 (F2 left Open, hands-off per your instruction).
  - F1: apply_selected fails closed on a present-but-not-a-table selected section (was a silent no-drop). F3: malformed splat paths now report the real problem + closed the ASCII first-char-vs-rest asymmetry in the grammar. F4: dict keys now scanned/unescaped for surviving $( same as values; a token-shaped key fails closed (undefined operation). F5: fullmatch closes the trailing-newline gap. F6: 300-level depth guard (SquadsError, not RecursionError) in resolve + deep_merge + a new _bounded_deepcopy used everywhere deepcopy was. F7/F8: docstring-only fixes (apply_selected's contract, deep_merge's independence claim narrowed to dict/list). F9: no source change per your follow-up -- added 3 pinning tests for the intended self-in-nested-list behavior.
  - F10: rebuilt test shape -- table-driven grammar-validity tests at value+key positions, and closed the 5 named pipeline gaps (order via list() not set() through apply_selected/merge_override, independence for an untouched list/spliced table/spread list and end-to-end through merge_override, merged-is-None pinned for a selected violation, fail-fast first-violation pinned same-mechanism + cross-mechanism + message content). Deduped the shared section-name set into tests/_helpers.py.
  - 34 new tests, all individually falsified (broke the fix, watched red, restored, watched green) -- reported in full to you separately. 142 specmerge+meta tests pass; pyright/ruff check/ruff format all clean (--all-extras). sq check clean. Left TASK-716 InProgress.
- [2026-07-31T14:54:51Z] Olivia Lead:
  - Folded the three new ADR-696 §4a clauses in. Path segments widen to a TOML bare key (A-Za-z0-9_- , one or more): hyphenated and digit-leading base keys become addressable, and a non-ASCII key is unaddressable by rule as a quoted key rather than by accident of a character class. Widened rather than restricted because a value the adopter may write literally must stay expressible as a reference.
  - Corrected the framing on the quoted-key residue: resolution is base-only, so a path can only ever address a bundled key. An adopter custom key is never a path target (it dangles by design however spelled) and addresses bundled paths from inside itself fine, the hyphen being in the destination. The constraint binds our own bundled vocabulary, so no adopter-facing note is owed — TASK-719 carries the positive statement only.
  - self is now definitional: the nearest enclosing keyed path at any list depth, with the three intended consequences pinned (two tokens at different depths resolve alike, a nested star-self spreads into the sub-list, an empty base list adds nothing; one list spread twice duplicates). The conservative reading follows from the abbreviation rule rather than being an independent call.
  - Fifth failure case added: nesting past a declared bound, specified by two properties and not a number, binding BOTH walks and checked before recursing or copying — a deep untouched base fails inside the copy, so a resolver-only guard misses it. The no-traceback contract stays unqualified, and the body says why. New ST6 holds it rather than ST1, since it spans the resolution and merge walks; the landed 300 plus bounded copy satisfies both properties.
  - The tests/meta scan now asserts two properties, both commented as load-bearing: no bundled string value begins with an unescaped sigil, and every bundled key is a TOML bare key (353 / 77 / 131 keys, all already bare) — the second is what makes a mis-navigating path unreachable rather than unlikely.
- [2026-07-31T14:56:23Z] Catherine Manager:
  - ST6 accepted as its own subtask: the nesting bound binds the merge walk as well as the resolver, so filing it under splat-resolution would hide the copy-side check from anyone reading for it (ADR-696 §4a).
- [2026-07-31T15:21:35Z] Elias Python:
  - REV-722 F3/F6/F9 pass landed (details on REV-722). Noted: tests/_helpers.py stayed unflagged as an edit last round -- flagging now per your ask, and again here since I touched it again this round only to add SPECMERGE_WORKFLOW_SECTIONS (no new edit beyond what you already saw).
  - Scope flag, please triage: TASK-716's own body has been substantially rewritten since I last read it in full -- it now specifies a 4th mechanism (a closed top-level key set, refusing an unrecognised override key) and a 'token territory' redefinition (a value is only in token grammar if it BEGINS with unescaped $(; F4's key-scanning is reversed -- 'keys are never touched' is now a stated acceptance criterion). Neither was in your F3/F6/F9 brief, so I did not implement either -- implementing an unbriefed redesign risked conflicting with whatever sequencing you have planned, same lesson as this pass. I only did the two things your message explicitly asked that overlap this territory: widened the grammar (F3) and added the two tests/meta scans you specified. If mechanism 4 and the token-territory/F4-reversal are meant for a dispatch now, let me know and I'll pick it up as its own pass rather than fold it in unbriefed.
  - Gates clean (--all-extras): pyright, ruff check, ruff format, pytest tests/unit/test_specmerge_*.py + tests/meta = 155 passed. TASK-716 left InProgress.
- [2026-07-31T15:34:51Z] Olivia Lead:
  - Corrected the key-position rule per ADR-696 §4a, superseding the value-only reading in my earlier comment: the sigil is reserved in EVERY string position and token territory is one predicate in both (a string begins with an unescaped sigil). In a value that means resolve-or-refuse-as-malformed; in a key it means REFUSE — never resolved, never passed through. The escape unescapes in both positions.
  - Two messages for a key in territory: a grammar-valid token reports used-as-a-key/keys-are-never-a-splat-target (undefined, not malformed), a malformed token-shaped key reports the malformed-token message; both collected, carrying the key dotted path. My previous acceptance said a key passes through untouched — that bullet is gone.
  - Carried the two reasons that make it non-arbitrary into the body: the refusal is a SPELLING requirement, not a vocabulary restriction (a project wanting a key named with the sigil writes the escaped form and gets it), which is also the line between this and the withdrawn splice check; and the models cannot be the backstop for keys, because a section keys ARE the open vocabulary — a type literally named as a token loads clean and mints a prefix and a folder.
  - Stated plainly for the dev in ST1: the data-in-both-positions rule is failing for VALUES today, not just keys — the literal-string path still flags the sigil anywhere, so a commands entry and a date-substitution value are both refused. It is one predicate moved from contains to begins-with in one place, which also narrows the over-wide key case; the key side then needs its meaning wired up, not a second predicate. Do not fix the two positions separately.
- [2026-07-31T15:55:48Z] Elias Python:
  - Read ADR-696's amendment notes in full (last-first) plus the current task body before starting -- both consistent with your message, no disagreement between them this time.
  - 1) Predicate narrowing, one change: _in_token_territory replaces the old contains-anywhere scan with begins-with, shared by _resolve_string (values) and _resolve_key (keys). Outside territory: data, with only a LEADING $$( ever unescaped (_unescape_leading_token) -- fixes the value-side defect (git-commit / date-substitution examples) and narrows the key side in the same edit, per your instruction not to fix them separately. Inside territory a key is always refused (grammar-valid -> used-as-a-key, malformed -> malformed-token), never resolved or passed through. Removed _process_literal_string entirely (dead once territory replaced contains-scanning) and _malformed_token_violation no longer returns None -- it's called only once territory + a failed parse is already known, so it always constructs a violation now.
  - One flag: your repro '$(date +%s) --flag' literally begins with the sigil, so by the begins-with rule it IS in territory and is NOT a well-formed whole-value token -- it's malformed, not pass-through. I could not find a reading of the ADR or task body where this one passes through unchanged; the git-commit example is the one that survives (it does not begin with the sigil). Implemented per the ADR text; flagging rather than guessing since you said both must pass through.
  - 2) ST5: new optional top_level_keys param on merge_override (None = no check, the roles-loader case). _unknown_key_violations is the shared helper ADR-696/ST3 asked for, used by both apply_selected's unknown-section check and the new _top_level_key_violations -- checked first, before splat resolution, per ST4's stated ordering. Mistyped-section and retired-override_base cases both fail closed; omitting the param passes everything through.
  - 3) ST6: no new code (already landed last pass) -- added the acceptance framing tests you asked for are already in place (both-sides refusal, the two-violations-from-one-shared-deep-branch case) and the constant's comment states the two properties.
  - Falsified every changed behaviour, both directions: begins-with vs contains (9 tests, incl. the exact shell-content/mid-key cases), key-refusal-in-territory (2 tests), ST5's catch + ordering + no-accepted-set default (4 separate mutations), and the shared unknown-key helper (reddened both callers at once, confirming it's genuinely shared not duplicated). All reverted, all green.
  - Gates clean (--all-extras): pyright, ruff check, ruff format, pytest tests/unit/test_specmerge_*.py + tests/meta = 166 passed. sq check clean. ST1/ST5/ST6 moved to Done; REV-722 F4 commented (superseded implementation, same Fixed status). TASK-716 left InProgress.
- [2026-07-31T16:08:12Z] Paul Reviewer:
  - Delta re-review recorded on REV-722. All ten earlier findings verified closed on 6e7a328 by driving the code, and verified to still hold under the four rounds stacked on them — including F6's depth bound in the composite shapes a single-sided guard would have missed (merge 600 + copy 600, resolver 600 + deep splice copy: clean collected refusals, no RecursionError).
  - One new medium, in the new closed key space: the engine owns [selected] but does not accept it in the top-level key space it enforces, so top_level_keys derived from the base document's own keys — or set to the six section names — refuses a legal [selected] override on the load path (F11). Plus F12 low (the check's default is off), F13/F14 info (duplicate reporting of one structural fault; the escape cannot express a leading literal double-dollar sigil, which is a line for the adopter grammar doc).
  - Suite judged again against F10: honestly closed. The five invariants I named are individually pinned and I falsified the shared unknown-key helper myself — both callers depend on it. Residual is coverage, not defect: the shape table is parametrized over the dict-value position only, and that missing crossing is what let F11 through.
  - @python-dev F11 is the only one blocking my approval. @manager still ChangesRequested for that one finding; nothing edited in src/ or tests/ and nothing committed by me.
- [2026-07-31T16:15:17Z] Olivia Lead:
  - Repointed the one stale document path in Testing: the raw-dict bases are src/squads/_specs/{workflow,roles,playbook}.toml, not the retired src/squads/_bundled/. No other dead-path mention in this body (REV-723 F2).
  - Also corrected my own ST1 example, which @python-dev was right to flag: "$(date +%s) --flag" BEGINS with the sigil, so it is in token territory, is not a whole-value token, and is therefore a malformed token that stays refused — not a pass-through. The git-commit line is the pass-through case, because the sigil is not at position 0. ST1 now states the contrast explicitly so the predicate is not over-corrected.
- [2026-07-31T16:18:04Z] Olivia Lead:
  - Closed the ST5 spec gap behind REV-722 F11 (ADR-696 §4b): the top-level check accepts [selected] UNCONDITIONALLY, without the caller naming it in the accepted set — it is the engine own reserved key, defined, consumed and stripped by the engine, so it is not document vocabulary and not the caller to declare. The accepted set for the workflow and playbook documents is now stated as the section names, full stop.
  - Wrote the general rule down in ST5 as well, since that is why this was missable: a key the ENGINE reserves is never subject to the caller accepted set — the same principle as the sigil being reserved in every string position. Next reserved key should not repeat this.
  - Acceptance now pins it against the two derivations a loader actually reaches for — the base document own top-level keys, and the six section names — rather than a spelling that happens to work; a requirement only one spelling satisfies lives in the tests folklore, not the engine.
  - Testing now says the shape table must be the position x shape CROSS-PRODUCT, not positional coverage: parametrising the dict-value position and hand-writing the others leaves every position present but only one crossed, and the uncrossed document-top-level cell is exactly how a legal [selected] override came to be refused.
- [2026-07-31T16:19:51Z] Elias Python:
  - REV-722 F11/F12 addressed (details on REV-722; TASK-716 status left at InReview as instructed).
  - F11 (medium, live defect): _top_level_key_violations now unions the caller's set with {selected} before checking -- selected is the engine's own reserved key, never the document's vocabulary, so a caller never has to know to add it. Verified clean against both derivations the reviewer drove on the real src/squads/_specs/workflow.toml. Added the missing test (both synthetic and against the real bundled spec); falsified by reverting the union, both reddened with the exact reported symptom, restored.
  - F12 (judgement call, agreed): top_level_keys is now a required keyword-only arg on merge_override -- no default, so omitting it is a pyright error rather than a silent fail-open; None still means deliberately open. Agreed because the old default picked the risky direction (unlike collect_all's safe fail-fast default), and section_names (the sibling closed-key-space param) is already required with no default. Updated ~20 test call sites (the only call sites -- no loader wires this in yet). Falsified via a scratch pyright probe: a bare call now errors, reverting the default makes the identical probe pass clean, restored.
  - Gates clean (--all-extras): pyright, ruff check, ruff format, pytest tests/unit/test_specmerge_*.py + tests/meta = 168 passed. sq check clean. Touched only src/squads/_specmerge.py and tests/unit/test_specmerge_ordered_entry_point.py.
<!-- sq:discussion:end -->
