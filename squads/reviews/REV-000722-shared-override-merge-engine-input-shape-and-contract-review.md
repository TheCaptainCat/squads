---
id: REV-722
sequence_id: 722
type: review
title: 'Shared override merge engine: input-shape and contract review'
status: Approved
author: reviewer
refs:
- TASK-716
- FEAT-712
- ADR-696
subentities:
- local_id: F1
  title: selected on a non-table section silently drops nothing
  status: Fixed
  severity: medium
- local_id: F2
  title: Splice type mismatch is never detected
  status: WontFix
  severity: medium
- local_id: F3
  title: Out-of-grammar splat path reports the wrong reason
  status: Fixed
  severity: medium
- local_id: F4
  title: Splat tokens in key positions are never scanned
  status: Fixed
  severity: low
- local_id: F5
  title: Token regex accepts a trailing newline
  status: Fixed
  severity: low
- local_id: F6
  title: Deep override nesting raises RecursionError
  status: Fixed
  severity: low
- local_id: F7
  title: apply_selected misstates its return contract
  status: Fixed
  severity: low
- local_id: F8
  title: deep_merge overclaims independence from the override
  status: Fixed
  severity: low
- local_id: F9
  title: Nested-list star-self resolves against the outer key
  status: Fixed
  severity: low
- local_id: F10
  title: Suite pins mechanisms, not pipeline invariants
  status: Fixed
  severity: low
- local_id: F11
  title: The engine's own selected key is refused by its top-level check
  status: Fixed
  severity: medium
- local_id: F12
  title: The closed top-level key space defaults to no check at all
  status: Fixed
  severity: low
- local_id: F13
  title: One structural fault is reported two or three times
  status: WontFix
  severity: info
- local_id: F14
  title: A leading literal double-dollar sigil cannot be written
  status: Fixed
  severity: info
created_at: '2026-07-31T14:12:21Z'
updated_at: '2026-08-03T07:45:09Z'
---
<!-- sq:body -->
## Scope

`src/squads/_specmerge.py` at `562bba6` (on `10bb523`), plus the four
`tests/unit/test_specmerge_*.py` modules (108 tests). Read against ADR-696 §4/§4a/§4b/§4c
(authoritative on the grammar, including the 2026-07-31 amendments), ADR-541 as narrowed,
FEAT-712's engine-boundary acceptance, and TASK-716's per-subtask acceptance.

Method: read the module, then drive it from a scratch harness over the real bundled
`workflow.toml` / `roles.toml` / `playbook.toml` as bases plus hand-built and
`tomllib`-parsed hostile overrides. Every finding below marked reproduced was produced by
running the code, not by reading it.

## What holds

Verified by driving, not by reading the docstrings:

- **Deep-merge at leaf granularity, arrays as leaves, no-op on an empty override.** An empty
  override over the real bundled workflow document returns a mapping equal to the base *and*
  in the base's own key order, top level and nested.
- **Independence from both inputs.** A recursive identity walk over the merged mapping
  against the base and against the override finds no shared `dict` or `list` object at any
  depth — including sections the override never touched, a table spliced in by `$(path)`, and
  a list spread in by `$(*path)`. Mutating the merged result at any depth leaves both inputs
  byte-identical.
- **Key order is base order.** Confirmed at three nesting levels and through the
  `apply_selected` rebuild: a section that loses keys keeps the base's relative order for the
  survivors, and a shared key never relocates.
- **Misshapen `[selected]` fails closed** across the whole adjacent family: a bare-string
  keep, an int keep, a keep list holding an int / a bool / a nested list / a table, a
  `selected` that is a list, a `selected` that is a string. Every one collects a violation
  naming what is actually wrong and drops nothing.
- **Single-pass resolution and base-only resolution.** A `$(` token sitting inside a base
  value that a splice copies out is not re-scanned and not reported — matching the stated
  rule. No override value is ever a splat target.
- **Order-independence** over a base that includes a splat target holds by `==` *and* by
  iteration order.
- **Both calling modes over one code path.** Collect-all reports resolution violations and
  both classes of `[selected]` violation from the same document together; fail-fast raises the
  first, and the first is deterministic (mechanism order, then document order) — reversing the
  override's own key order does not change it.
- **`MergeResult.merged` was `None` in every violating case driven**, in both modes.
- **The stated boundary holds.** The module's only internal import is `squads._errors`. It
  contains no roster rule, no lifecycle floor, no category catalog, no drift stamp and no
  live-index check, and nothing outside its own tests imports it yet. A retired-carrier
  `override_base` key passes through untouched, which is correct: per ADR-696's amendment it
  fails closed as an unknown key at the model, not here.
- **Conventions.** PEP-695 `type RawMapping = …`; no bare alias assignment; no `eval`; no
  ticket or item ID anywhere in the module or the test names; no status prose and no
  build-process narration in the docstrings; `pyright`, `ruff check`, `ruff format` clean and
  the 108 tests plus `tests/meta` green, independently re-run.

## Where the findings cluster

Nine of the ten findings are input shapes, not mechanisms — the same class as the three
defects already closed. Three matter:

- a `[selected]` list whose section is present but not a table silently does nothing, which
  is the one deselect failure mode no downstream check on the resulting spec can see (F1);
- half of the stated type-mismatch failure case — a splice landing where the surrounding
  shape cannot hold it — has no implementation (F2);
- the most likely adopter mistake in a splat path is diagnosed as a different mistake, with a
  hint that contradicts what they wrote (F3).

The rest are low: token handling in key positions, a regex anchor, an uncaught
`RecursionError`, two docstring claims that are broader than the code, and a grammar case the
ADR does not define.

F10 is the test suite itself. The three closed defects each lived in an input shape with no
test at all, and the suite's shape is why: it asserts one example per implemented branch, so
it can confirm the mechanism and cannot find an unconsidered shape. The specific unasserted
invariants are listed there.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 722 add-finding "…" --severity medium`; track with `sq review 722 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — selected on a non-table section silently drops nothing

<!-- sq:finding:F1:body -->
**Reproduced.**

`apply_selected` skips any section whose merged value is not a `dict`:

```python
raw_section_map = result.get(section)
if not isinstance(raw_section_map, dict):
    continue
```

That single branch swallows two different situations. The first — the section is *absent* —
is a deliberate, tested decision (`test_a_selected_entry_for_a_section_absent_from_the_merged_mapping_is_inert`)
and should stay. The second — the section is *present but not a table* — has no test and no
decision behind it, and it fails open: the deselect is silently not applied, zero violations,
zero deselections.

Driven, with the accepted section set the workflow loader will pass:

- section value is a list of tables (`{"roles": [{"slug": "a"}, {"slug": "b"}]}`, which is
  exactly `_bundled/roles.toml`'s top-level `roles` shape) plus `selected.roles = ["a"]` →
  merged mapping unchanged, `violations == []`, `deselections == ()`.
- an override that shadows a section with a scalar (`items = 5`) alongside
  `selected.items = ["task"]` → merged `{"items": 5}`, no violation, no deselection.

Why this is worth fixing rather than leaving to the caller: ADR-696 §4b's argument for
`selected` carrying no validation of its own is that *every unsafe drop is caught by a check
that runs on the resulting spec*. That argument covers drops that happen. It does not cover a
drop that **never happened** — the resulting spec is perfectly valid, it is simply not the
spec the adopter asked for, so no floor check, no referential-integrity check and no
live-index check can ever see it. This is the same fail-open class as the bare-string keep
that was already closed, one shape over, and the shape it lands on is the top-level shape of
one of the three documents this engine is being built to serve.

Recommendation: keep absent → inert; make present-but-not-a-table a collected
`MergeViolation` naming the section, the shape found, and that a deselect needs a keyed
table. It is one `elif` in the same loop and needs no spec knowledge, so it does not breach
the loader-agnostic boundary.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-31T14:51:12Z] Elias Python:
  - Fixed in _specmerge.py: apply_selected now runs _selected_section_shape_violations after computing the post-strip result — a section present but not a table (list, scalar, etc) fails closed naming the section + shape found + that a deselect needs a table. Absent stays inert (regression-tested, unchanged). Falsified: reverted the check, both new tests (list-shaped roles.toml case + scalar case) reddened exactly on the silent-drop symptom, restored, green.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Splice type mismatch is never detected

<!-- sq:finding:F2:body -->
**Reproduced.**

The type-mismatch failure case is stated in two halves. TASK-716, Failure shape: *"a spread
(`$(*…)`) whose base value is not a list; **a splice landing where the surrounding shape
cannot hold it (a table where a scalar is due)**"*. ADR-696 §4a and FEAT-712's acceptance carry
the same pair.

Only the first half exists. `_resolve_list_element_token` checks a spread against a non-list,
and `_resolve_scalar_token` rejects a spread used outside a list. A **splice** — `$(path)`
without the star — returns `deepcopy(base_value)` unconditionally, whatever the shape at the
destination. All four probes below produce a value with `violations == []`:

- base `items.task.prefix = "TASK"`, override `prefix = "$(items.task.labels)"` where
  `labels` is a table → merged `prefix` becomes `{"x": 1}`.
- same with `labels` a list → merged `prefix` becomes `["x"]`.
- the reverse: override `labels = "$(items.task.prefix)"` → a table-valued key becomes the
  string `"TASK"`.
- into a list: base `a = ["x"]`, override `a = ["$(t)", "y"]` with `t` a table → merged
  `a = [{"k": 1}, "y"]`, a table spliced into a list of scalars.

Impact is bounded, which is why this is medium and not high: the strictly-typed models catch
each of these as a pydantic type error at load. What is lost is that the failure stops being a
`MergeViolation`, so it cannot be collected in lint mode alongside the other violations, and
the adopter gets a pydantic type error about the merged value instead of a message naming
their token and the dotted path.

Note the criterion is not implementable as literally worded — "where a scalar is due" is
schema knowledge the engine deliberately does not have. The implementable reading is against
the **base's own shape at the destination path**: if the base holds a scalar there and the
splice yields a container (or the reverse), the splice changed the shape of a key the base
defines, and that is a violation. That reading needs an explicit ruling, because `deep_merge`
knowingly allows exactly that shape change for a *literal* override value (leaf replaces
counterpart wholesale) — so a splice would be held to a stricter rule than a hand-written
value, and that asymmetry should be recorded rather than assumed.

Recommendation: either implement the base-shape comparison for splices, or narrow the
criterion in the ADR to the spread cases that are implemented, and say so. Leaving a stated
fail-closed case with no code and no note is the part that needs closing.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-31T15:59:12Z] Catherine Manager:
  - Closed as a recorded narrowing, no code: ADR-696 §4a withdraws the criterion outright rather than reinterpreting it. A splat-ref is an abbreviation held to the same standard as the literal it abbreviates, so a splice is never checked against the shape of the key it lands on — destination shape is the models' plane. The collect-all cost is real but not splice-specific, and is tracked against the loader work instead.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Out-of-grammar splat path reports the wrong reason

<!-- sq:finding:F3:body -->
**Reproduced.**

`_parse_token` recognises a token only if it matches
`^\$\((\*)?([A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)*)\)$`. Anything shaped like a token but with a
path outside that grammar falls through to `_process_literal_string`, which reports:

> reason: `unresolved splat-ref token '$(' survives after resolution`
> hint: `the token must be the entire string value, or escape a literal with '$$('`

Both halves of the hint are wrong for this input. The token **is** the entire string value,
and the adopter does not want a literal. The message describes the one mistake they did not
make and says nothing about the one they did.

Driven, all reporting that same reason and hint:

| value | actual problem |
|---|---|
| `"$(items.my-type)"` | `-` is not in the path grammar |
| `"$(items.2fa)"` | a leading digit is not in the path grammar |
| `"$(élan)"` | a non-ASCII first character is not in the path grammar |
| `"$(items..task)"` | empty path segment |
| `"$()"` / `"$(*)"` | empty path |
| `"$(**items)"` | double star |

For contrast, `"$(itéms)"` **resolves cleanly** — `[A-Za-z_][\w]*` rejects a non-ASCII first
character but `\w` accepts non-ASCII everywhere after it. That asymmetry is almost certainly
unintended and is a second symptom of the same regex.

Two separable things to fix:

1. **Diagnosis.** A string that begins `$(` and ends `)` with no interior `$(` is a
   *malformed token*, not a surviving literal. Report it as one, quoting the path and what a
   path may contain. This is the most likely class of adopter mistake in the whole grammar and
   currently gets the least useful message of any failure the engine produces.
2. **Grammar coverage.** The path grammar is narrower than TOML's key space: `-` and a leading
   digit are legal in TOML bare keys, and quoted keys are legal too. Today's bundled documents
   contain no such key (checked: every key in all three files is `[A-Za-z_]\w*`), so nothing
   is unreachable *yet* — resolution is base-only, so only base keys are ever addressed. But
   hyphenated vocabulary is pervasive in this project (role slugs, `tech-lead`), and the day a
   bundled key is hyphenated, splat-refs cannot address it and the failure is the misleading
   message above. Either widen the grammar or record the restriction in the ADR as a
   constraint on bundled key names.

Related, same function, worth folding into the fix: `_dotted` joins path segments with `.` and
`_lookup_base_path` splits on `.`, so a quoted TOML key containing a dot
(`[items."a.b"]`) makes `$(self)` address the wrong path. Not reachable against today's bundled
documents, and it can only produce a spurious dangling error rather than wrong data, so no
separate finding — but the same widening should account for it.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-07-31T14:51:17Z] Elias Python:
  - Fixed: added _malformed_token_violation — a whole-string $(...) shape that fails grammar validation now reports 'malformed splat-ref path ... not a valid dotted identifier chain' instead of the wrong surviving-token message. Also closed the ASCII asymmetry: _TOKEN_RE's identifier class is now [A-Za-z0-9_] everywhere (was \w after the first char), so élan and itéms fail the same way. Documented the narrower-than-TOML grammar (no hyphen, no leading digit) as a deliberate restriction in the module docstring, matching every bundled key today. Falsified both sub-fixes independently (message + regex) — 8 parametrized malformed-path cases and the itéms asymmetry case each reddened on revert, restored, green.
- [2026-07-31T15:20:34Z] Elias Python:
  - Reopened per ADR-696's amendment: my previous fix narrowed the grammar (ASCII identifier, no hyphen/leading-digit) when the ruling widens it to exactly a TOML bare key. Redone below.
- [2026-07-31T15:20:49Z] Elias Python:
  - Redone against ADR-696's amendment. _TOKEN_RE's path-segment grammar is now [A-Za-z0-9_-]+ (a TOML bare key exactly, no restriction on leading character) instead of an ASCII-identifier subset -- a hyphenated segment (user-story) and a digit-leading one now resolve. Kept ASCII-only, but for the ruled reason rather than symmetry: a TOML bare key is ASCII by the format's own definition, so a non-ASCII key is necessarily quoted and unaddressable by rule (élan/itéms both still fail identically, now correctly attributed).
  - Added tests/meta/test_bundled_documents_are_splat_ref_addressable.py per your ask: scans all three bundled documents for (a) every key at every depth is a TOML bare key, (b) no bundled string value begins with an unescaped $(. Both pass on the real documents (353/77/131 keys, matching your audit) plus 6 self-tests proving the walkers actually detect a non-ASCII key, a dotted-quoted-key, a nested-list $( leak, etc.
  - Falsified: reverted the regex to the old ASCII-identifier grammar -- all 4 grammar-widening tests reddened (hyphenated/digit-leading paths stopped resolving); restored, green. Falsified the meta scan's bare-key regex (widened it to accept anything) -- both self-tests using synthetic bad keys reddened while the two real-document tests correctly stayed green (nothing bad to catch); restored, green.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Splat tokens in key positions are never scanned

<!-- sq:finding:F4:body -->
**Reproduced.**

`_resolve_value` walks a mapping's **values** and rebuilds the dict with its keys verbatim.
No key is ever token-matched, scanned for a surviving `$(`, or unescaped. Driven over base
`{"items": {"task": {"a": 1}}}`:

- override `{"items": {"$(items.task)": {"a": 2}}}` → merged
  `{"items": {"task": {...}, "$(items.task)": {"a": 2}}}`, `violations == []`. A key literally
  named `$(items.task)` enters the merged mapping and, since section keys are the vocabulary
  itself (type names, status names), the models accept it: the typo becomes data.
- override `{"items": {"$(oops": {...}}}` → same, no violation, even though an unescaped `$(`
  survives into the output.
- override `{"items": {"$$(literal)": {...}}}` → key stays `$$(literal)`, while the identical
  string **as a value** unescapes to `$(literal)`. So the escape hatch exists for values and
  not for keys, with no note anywhere that the rule is value-only.

ADR-696 §4a states the surviving-token rule without restricting it to values, and gives its
rationale as *"it means a typo silently became data everywhere else"* — which is exactly what
happens here.

Severity is low, not medium, because `$` is not legal in a TOML bare key: reaching this
requires the adopter to deliberately write a **quoted** key (`["$(items.task)"]`), which is not
a plausible slip. `[selected]` section keys are the one place a token-shaped key is caught, and
only incidentally, via the unknown-section check.

Recommendation: pick one and make it explicit. Either scan keys for a surviving `$(` and
unescape `$$(` in them (a few lines in `_resolve_value`'s dict branch), or state in the module
docstring and the ADR that the token grammar and the escape apply to values only. The current
state is neither.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-07-31T14:51:34Z] Elias Python:
  - Fixed: added _resolve_key, run on every dict key in _resolve_value's dict branch. A key that's itself a grammar-valid token fails closed ('used as a key — keys are never a splat target'); a malformed-shaped key gets the F3 message; any other unescaped $( in a key fails closed the same as a value; $$( still unescapes to a literal key. No splice/spread resolution for keys (no such operation is defined). Falsified: reverted to a passthrough key, all 4 new key-position tests reddened (typo silently becoming vocabulary, escape not applying), restored, green.
- [2026-07-31T15:55:22Z] Elias Python:
  - Superseded by the token-territory ruling (ADR-696): the key predicate is now begins-with, matching the value side, not the old contains-anywhere scan. Inside territory a key is always refused (grammar-valid -> used-as-a-key, malformed -> malformed-token message); outside territory a key is data, with only a leading $$( ever unescaped -- a stray $( elsewhere in a key (weird-$(x)-key) now passes through untouched rather than being flagged, closing the over-wide case the architect flagged in my previous pass. Falsified: reverted the territory predicate to contains-anywhere -- 9 tests reddened across both positions; reverted the key-refusal branch to a silent pass-through -- 2 tests reddened. Both restored, green.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Token regex accepts a trailing newline

<!-- sq:finding:F5:body -->
**Reproduced.**

`_TOKEN_RE` ends in `\)$`, and in Python `$` matches at the end of the string *or immediately
before a single trailing newline*. So one trailing newline is silently inside the grammar:

- `"$(items)\n"` → resolves to the base list, `violations == []`. The newline is discarded
  along with the rest of the string.
- `"$(items)\n\n"` → fails closed (surviving token).
- `" $(items)"`, `"$(items) "`, `"\n$(items)"` → all fail closed.
- `"$(*items)\n"` → reaches `_resolve_scalar_token` and reports the spread-outside-a-list
  violation, i.e. it is treated as a well-formed token too.

The rule this breaks is stated three times (module docstring, ADR-696 §4a, TASK-716): *"a token
is recognised only when it is the entire string value"*. In the trailing-newline case it is not
the entire value, and the engine both accepts it and silently drops a character the adopter
wrote. Reachable from a TOML multi-line basic string.

Low severity: the resolved value is what the author almost certainly intended, so the harm is
the inconsistency with every adjacent whitespace case rather than wrong data.

Recommendation: `_TOKEN_RE.fullmatch(value)`, or anchor with `\Z` instead of `$`. Same change
suffices for `_parse_token`'s only call sites.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-07-31T14:51:42Z] Elias Python:
  - Fixed: _parse_token now uses _TOKEN_RE.fullmatch instead of .match, closing the trailing-newline gap (fullmatch requires the match to consume the entire string, so the $ anchor's 'end-of-string-or-before-a-trailing-newline' quirk no longer lets one through). Falsified: reverted to .match, the single-trailing-newline case reddened (others already passed), restored, green.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Deep override nesting raises RecursionError

<!-- sq:finding:F6:body -->
**Reproduced.**

TASK-716's failure shape is absolute: *"Every failure is a clean `SquadsError`, never a
traceback."* Three functions recurse per nesting level with no depth guard — `_resolve_value`,
`deep_merge`, and the `deepcopy` inside `deep_merge`'s untouched-base branch.

A TOML document reaches that depth through dotted keys, which `tomllib` accepts happily:

- `k0.k1. … .k1999 = 1` (2000 segments) parses, then `merge_override` raises an uncaught
  `RecursionError`. At 200 and 400 segments it merges cleanly, so the cliff is inside the
  range a single legal line can express.
- symmetrically, a ~3000-deep *base* subtree the override does not touch blows up in
  `deepcopy` on the same call.

`tomllib` cannot be the guard here — it accepted the document — so if this contract is meant
literally the guard belongs in the engine.

Low severity: the document is the adopter's own, the failure is loud, and nothing is
corrupted. It is filed because the contract is stated without qualification and because the
engine's inputs are, by design, adopter-authored files.

Recommendation: cheapest honest fix is a depth counter in `_resolve_value` / `deep_merge` that
collects a `MergeViolation` naming the dotted path once a sane nesting limit is exceeded.
Alternatively, qualify the contract in the ADR/task so "never a traceback" is not read as
covering pathological nesting.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-07-31T14:52:00Z] Elias Python:
  - Fixed: added a 300-level depth guard, raising a clean SquadsError (never collected — it's a hard structural limit, not a data violation) in _resolve_value/_resolve_list and in deep_merge; also replaced every deepcopy(...) call with a new _bounded_deepcopy that carries the same guard, closing the symmetric base-side blowup (an untouched deep base subtree copied via deepcopy). 300 is well above the real bundled documents' nesting and comfortably inside Python's default recursion ceiling. Falsified: raised the limit to 100000 (effectively disabling the guard), both the override-side (2000-segment dotted key) and base-side (3000-deep untouched subtree) repros reverted to uncaught RecursionError, restored the limit, both raise clean SquadsErrors again.
- [2026-07-31T15:20:54Z] Elias Python:
  - Reopened per the ruling: my previous fix raised SquadsError directly on the depth bound, bypassing collect_all -- the refusal belongs on the violation channel. Redone below.
- [2026-07-31T15:21:08Z] Elias Python:
  - Redone: the depth bound now collects on the same violation channel as everything else, in every function that can hit it -- _resolve_value, _bounded_deepcopy, and deep_merge (which changed signature to deep_merge(base, override, origin) -> (merged, violations), matching the other two mechanisms' shape, since it needed a way to report a violation without raising). Past the bound: append a MergeViolation naming the dotted path, stop descending that one branch, keep walking siblings. merge_override threads deep_merge's violations through the same _maybe_raise call as resolve_splat_refs's and apply_selected's -- fail-fast still raises (via _maybe_raise, not a raise anywhere in the mechanisms themselves), collect-all never does.
  - _MAX_NESTING_DEPTH stays 300, now commented as the two properties rather than a number: far above the deepest bundled key path (4 levels), far below the interpreter's headroom with room for the per-level copy.
  - Falsified each guard site independently by reverting it to a raise: _resolve_value's own guard, _bounded_deepcopy's, and deep_merge's own recursive-descent guard (needed a base+override BOTH deeply nested with matching keys to actually exercise deep_merge's own recursion rather than delegate to _bounded_deepcopy -- added that test since the two originally-reported repros both bottom out in _bounded_deepcopy and never exercised deep_merge's own path). Also falsified at the merge_override entry point in collect_all mode. All 5 reddened on the targeted mutation, restored, green.
  - One correction to my own report: in collect-all mode, a deeply-nested shared branch produces TWO violations, not one -- resolve_splat_refs's own walk of the override hits the bound independently of deep_merge's later walk of the same structure. That's correct per 'it binds both walks', not a bug; test asserts 2.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — apply_selected misstates its return contract

<!-- sq:finding:F7:body -->
**Reproduced.**

`apply_selected` is public and will be called by three loaders. Its docstring says it returns

> the merged mapping with `selected` removed and no keys dropped, the provenance of every drop,
> and any violations

"with `selected` removed **and no keys dropped**" states the opposite of what the function is
for — dropping keys is the whole mechanism. Presumably "and the deselected keys dropped" was
meant.

The same sentence also hides the behaviour on the violation path, which is materially
different from the success path. Driven with `{"items": {"task": {}}, "selected": {"nope": ["x"]}}`:

- the returned mapping **is the caller's own input object** (`out is merged` → `True`), and
- it still carries the `[selected]` key (`"selected" in out` → `True`).

`merge_override` discards it (`merged=None` whenever violations exist, verified), so nothing is
wrong today. But the failure mode for a direct caller is a `selected`-bearing mapping handed to
a model with `extra="forbid"`, or an in-place mutation reaching back into the caller's input —
and neither is stated.

Low severity: documentation and contract precision on a public surface, no current defect.

Recommendation: fix the sentence, and state explicitly that on the violation path the input
mapping is returned unmodified and must not be used. Returning `None` for the mapping when
violations are non-empty would make the contract unmissable and mirror `MergeResult.merged`,
at the cost of a slightly noisier signature.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-07-31T14:52:07Z] Elias Python:
  - Docs-only fix (no defect, as scoped): apply_selected's docstring corrected from the self-contradicting 'no keys dropped' to the real contract, and now states the violation path explicitly (caller's own input object returned unmodified, selected still present, must not be used -- MergeResult.merged already enforces None at the merge_override boundary). Did not change the return type to Optional per the reviewer's costlier alternative -- no caller needs it since merge_override already owns that contract. Added + falsified a pinning test for the documented violation-path identity (result is merged).
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — deep_merge overclaims independence from the override

<!-- sq:finding:F8:body -->
**Reproduced.**

`deep_merge`'s docstring asserts, without qualification, *"The result shares no mutable
structure with either input"*. It holds for `dict` and `list`, which was tested hard and
confirmed independently here at every depth. It does not hold for a mutable reached through
anything else, because the copy is gated on `isinstance(value, dict | list)`:

```python
merged[key] = deepcopy(...) if isinstance(value, dict | list) else value
```

Driven: `deep_merge({"x": 1}, {"b": ({"inner": [1]},)})` → `merged["b"] is override["b"]`, so
the tuple and the dict inside it are shared with the override. The base side is safe by
accident — its untouched branch deep-copies unconditionally.

`tomllib` cannot produce a tuple, so this is not reachable from a parsed override today. It is
filed because the module's declared input type is `dict[str, Any]`, not "a parsed TOML
document", and because this specific claim is the seam a dependent feature is being designed
against (bundled base immutable, merged mapping per request) — an invariant that load-bearing
should be stated as narrowly as it is true.

Two other docstring claims in the same function are broader than the module's own knowledge:
*"`base` is a module-level immutable reused across every request"* — the engine is
loader-agnostic and cannot know that of its argument, and no such caller exists in the tree
yet; the guarantee is worth stating, the premise about the caller is not.

Low severity: precision of a stated invariant, no reachable defect.

Recommendation: either copy on `not isinstance(value, str | int | float | bool | None)` (or
deep-copy unconditionally and drop the branch — the documents are small and the measured cost
of a full merge over the real bundled workflow document is ~0.1 ms), or narrow the claim to
"no shared `dict` or `list`" and state the input contract as parsed-TOML scalars.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-07-31T14:52:25Z] Elias Python:
  - Docs-only fix (no defect, as scoped): narrowed deep_merge's docstring to what is actually guaranteed -- no dict or list object shared with either input (the two mutable container types a parsed TOML document can hold), not an unqualified claim over any value type -- and dropped the unwarranted premise about base being a module-level immutable reused across requests (the engine cannot know that of its argument). Chose to narrow the claim rather than broaden the copy check to cover types tomllib can never produce (e.g. tuple) -- that's defending against inputs outside the module's own declared dict[str, Any]-from-parsed-TOML contract, which is complexity with no real caller.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Nested-list star-self resolves against the outer key

<!-- sq:finding:F9:body -->
**Reproduced.**

`_resolve_list` recurses into a nested list with the **same** `current_path` — list position
never extends the path, since there is no dotted name for an index. So `self` inside a nested
list still means the enclosing *key*, and the spread lands in the inner list:

base `{"a": ["x", "y"]}`, override `{"a": [["$(*self)"], "z"]}` →
merged `{"a": [["x", "y"], "z"]}`, `violations == []`.

Two tokens at different nesting depths under the same key therefore resolve to the same base
value, and a `$(*self)` nested two lists deep silently splices the whole top-level list into a
sub-list. ADR-696 §4a defines `$(self)` as *"the key currently being written"* and says nothing
about nesting, so this is undefined behaviour that produces a value rather than a violation.

Also driven and worth pinning while this is open, both of which look right but are unspecified
and untested:

- spread of an **empty** base list: `{"a": []}` + `{"a": ["$(*self)", "new"]}` → `["new"]`, no
  violation. Consistent with compose-only, and distinct from the dangling case (a key with no
  base counterpart), which does fail.
- the same token twice: `{"a": [1, 2]}` + `{"a": ["$(*self)", "$(*a)"]}` → `[1, 2, 1, 2]`. Two
  spreads of one base list duplicate it. Compose-only permits it; nothing says whether it is
  intended.

Low severity: no wrong data reaches a caller who stays inside the documented grammar, and the
documents this serves have no nested plain lists today.

Recommendation: decide one line in the ADR — either `self` inside a nested list is a violation
(the conservative reading, since the surrounding shape is not the key's shape), or it is
explicitly the enclosing key — and add the two pinning tests above either way.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-07-31T14:52:35Z] Elias Python:
  - Per the coordinator's follow-up: no source change -- self inside a nested list correctly means the enclosing key (a list position has no dotted name to extend the path with, so there's nothing else self could mean). Added 3 pinning tests instead: the reviewer's exact nested-list case, empty-base-list spread (no violation, distinct from dangling), and the same-list-spread-twice duplication (compose-only permits it). Falsified by temporarily breaking self-target resolution -- all 3 reddened, restored, green.
- [2026-07-31T15:21:14Z] Elias Python:
  - Docstring addition per your follow-up: resolve_splat_refs now states the nested-list semantics explicitly in the architect's terms -- self/*self addresses the nearest enclosing keyed path, at any list depth, definitional (a list position contributes nothing to the path) rather than a special case. No behavior change; the three pinning tests from the previous pass already cover it.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Suite pins mechanisms, not pipeline invariants

<!-- sq:finding:F10:body -->
108 tests, all green, and none of them could have found any of the three defects that were
found by hand, nor any of F1–F9. That is a property of the suite's shape, not its size.

The suite is built one test per implemented branch, each supplying exactly the value that
branch checks for. That proves the mechanism does what it was written to do, which is the
thing least in doubt. It contains no test that enumerates a *family* of inputs at one
position, which is where every defect so far has lived.

Concretely unasserted, and each one is a stated acceptance criterion or a docstring claim:

- **Order preservation through the pipeline.** The two order tests call `deep_merge` directly.
  Every `merge_override` and `apply_selected` assertion about section membership goes through
  `set(...)` (`set(result["items"])`, `set(result.merged["items"])`, `set(deselections)`), so
  the order-preserving rebuild inside `apply_selected` is pinned nowhere. It does hold —
  verified — which means the property currently survives on nobody's guard.
- **Independence from the inputs beyond one dict.**
  `test_the_merged_mapping_shares_no_mutable_structure_with_the_base` checks two dict
  identities and one mutation. Nothing checks an untouched base **list**, a table spliced in by
  `$(path)`, or a list spread in by `$(*path)` — the three places the deepcopy could have been
  missed. Nothing checks independence through `merge_override` at all, and the docstring's
  claim now extends to the override, where only one array case is covered.
- **"No-op on an empty override" is asserted as `==` only.** The criterion is *"same keys, same
  values, same nesting, nothing added and nothing stripped"*; `merged == base` is blind to key
  order, which is now a stated invariant.
- **`MergeResult.merged is None` whenever violations exist.** Observed incidentally in one
  test. No test asserts it for a `[selected]` shape violation, and
  `test_collect_all_mode_does_not_stop_at_the_first_violation` never looks at `merged`.
- **Fail-fast reports the *first* violation.** `test_fail_fast_mode_raises_a_squads_error_on_the_first_violation`
  drives a document with exactly **one** violation, so it cannot distinguish first-violation
  from any-violation, and it never inspects the message. Nothing asserts the raised message
  carries the origin label and the dotted path, which TASK-716 requires of every raise.
  Nothing asserts determinism (the same document, keys reordered, raising the same violation).
- **Malformed shapes at every other position.** `[selected]` values now have four shape tests,
  because those shapes were reported. No equivalent exists for a token in a key, a token with
  surrounding whitespace, an out-of-grammar path, a splice that changes shape, a section that
  is not a table, a nested-list `self`, or an empty base list — i.e. for F1–F9.

Test hygiene, minor, same files: the override in
`test_array_of_tables_splat_append_against_a_real_parsed_toml_inline_array_override` declares a
`[[types.epic.roles]]` block that no assertion ever reads, and `_WORKFLOW_SECTIONS` is
duplicated as a literal across two modules.

Recommendation, in priority order:

1. One table-driven test per input *position* (dict key, dict value, list element, nested list
   element, `[selected]` value, `[selected]` section) crossed against a fixed list of
   shapes — string, int, bool, empty list, list of non-strings, table, token, malformed token,
   escaped token — asserting for each either a named violation or an exact value. This is the
   test that would have caught all three original defects and most of F1–F9, and it is cheap
   because the engine is a pure function.
2. Assert the four pipeline invariants (key order, input independence, `merged is None` on
   violations, first-violation identity + message content) through `merge_override`, not
   through the sub-functions.
3. Replace `set(...)` with ordered comparisons wherever the assertion is about which keys
   survive.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-07-31T14:52:49Z] Elias Python:
  - Rebuilt test shape per the recommendation: table-driven splat-path-grammar tests (8 malformed-path cases + the ASCII-asymmetry case, parametrized) at both value and key positions, plus the 5 named pipeline gaps closed at the merge_override/apply_selected boundary -- order preservation now asserted via list(...) not set(...) (apply_selected's rebuild + merge_override's no-op), independence asserted for an untouched base list / a $(path)-spliced table / a $(*path)-spread list AND through merge_override end-to-end, merged-is-None pinned for a selected shape violation, fail-fast's first-violation identity pinned against a same-mechanism 2-violation case (distinguishes index[0] from index[-1], which a 1-violation document cannot) plus a cross-mechanism determinism case and message-content (origin + dotted path) assertions. Hygiene: deduped the shared section-name frozenset into tests/_helpers.py (SPECMERGE_WORKFLOW_SECTIONS, following the existing _helpers.py convention) across all 4 files, removed the unread [[types.epic.roles]] block. Net: 34 new tests, every one individually falsified.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — The engine's own selected key is refused by its top-level check

<!-- sq:finding:F11:body -->
**Reproduced.** In the new closed top-level key space.

`_SELECTED_KEY` is the engine's own key: this module defines it, consumes it, strips it from
the returned mapping, and owns the whole deselect mechanism. But
`_top_level_key_violations` checks the override's top level against the caller's
`top_level_keys` verbatim, so unless the caller *also* remembers to union `"selected"` in, a
perfectly legal override using the engine's own documented mechanism is refused.

Driven against the real `_specs/workflow.toml` with `override = tomllib.loads('[selected]\nitems = ["task"]\n')`,
in fail-fast mode — the load path:

| `top_level_keys` | result |
|---|---|
| `frozenset(WF.keys())` — the document's own top-level keys | **refused**: `unknown top-level key 'selected'` |
| the six section names | **refused**: `unknown top-level key 'selected'` |
| sections `| {"selected"}` | merges clean |

The first row is the trap: deriving the accepted set from the base document's own top-level
keys is the most natural thing a loader will do, and it is wrong in a way nothing hints at.
The second row is what every other `top_level_keys` test in the suite passes. Exactly one
test — `test_a_recognised_top_level_key_set_merges_clean` — passes the working spelling, so
the requirement currently survives as folklore in one test rather than as a contract.

Two reasons this is medium and not low:

1. **It fails in the refusing direction, on the load path.** `merge_override` raises, so `sq`
   stops, for an adopter who wrote a valid document. Every other violation in this module is
   a response to something wrong in the override; this one fires on something right.
2. **The engine is asking the caller to know an implementation detail of the engine.** The
   whole point of the loader-agnostic boundary is that the caller supplies name spaces it owns.
   `selected` is not one of them — the caller never writes it, reads it, or strips it.

No test covers the combination, which is why four rounds of change did not surface it: the
`[selected]` tests never pass `top_level_keys`, and the `top_level_keys` tests only use a
`[selected]` table in the one case that already unions it in.

Recommendation: accept it inside the engine —
`_unknown_key_violations(override.keys(), top_level_keys | {_SELECTED_KEY}, …)` — since the
engine owns the key. If the team prefers the caller to declare it, then `merge_override`'s
docstring has to say so explicitly and a test has to pin the refusal as intended; leaving it
implicit is the part that needs closing either way.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-07-31T16:19:10Z] Elias Python:
  - Fixed: _top_level_key_violations now unions the caller's accepted set with {selected} before checking -- selected is the engine's own reserved key (defined, consumed, stripped by apply_selected), never the document's vocabulary, so a caller never has to know to add it. Verified against your exact repro (real src/squads/_specs/workflow.toml, both derivations you drove) -- both now merge clean.
  - Added the missing test: [selected] present + top_level_keys supplied without it, both against a synthetic base and against the real bundled workflow.toml with both natural derivations (all document keys; the six section names). Falsified: reverted the union, both new tests reddened reproducing your exact symptom (unknown top-level key 'selected'); restored, green.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — The closed top-level key space defaults to no check at all

<!-- sq:finding:F12:body -->
**Reproduced.** An API-shape observation on the new mechanism, not a defect in its logic.

`top_level_keys: frozenset[str] | None = None`, and `None` means *no check*. So the parameter
that exists specifically to close a live fail-open in shipped code is **off by default**:

```
merge_override(base, {"bogus": 1}, SEC, "o")                     -> merges clean, bogus key kept
merge_override(base, {"bogus": 1}, SEC, "o", top_level_keys=SEC) -> unknown top-level key 'bogus'
```

`None` is the right *value* for the roles loader, whose top level is deliberately open — that
part is correct and well argued in the docstring. The issue is that a loader author who simply
does not pass the argument gets the exact silent behaviour this mechanism was written to
eliminate, and nothing at any layer reports it: not the engine, not the models (which never see
the key), not `sq workflow lint`. A regression here looks identical to correct code.

Verified separately that the check is otherwise correctly gated on `is None` rather than on
truthiness — `top_level_keys=frozenset()` refuses every key rather than skipping the check,
which is the right reading of an empty accepted set.

Low, because there is no defect today (no loader is wired yet) and the fix is mechanical.

Recommendation: make it keyword-only **without** a default, so every caller states its choice
— `top_level_keys=WORKFLOW_SECTIONS | {"selected"}` in the workflow and playbook loaders,
`top_level_keys=None` in the roles loader with the reason on the line. That converts a silent
omission into a decision, which is the same reasoning that put the check there in the first
place.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-07-31T16:19:29Z] Elias Python:
  - Agreed and implemented: top_level_keys has no default now (required keyword-only arg on merge_override) -- omitting it is a pyright reportCallIssue, not a silent fail-open. None still means deliberately open (unchanged meaning), now stated at every call site rather than defaulted. Reasoning for agreeing: collect_all's default (fail-fast) is the SAFE direction, but top_level_keys' old default (None = open, no check) was the RISKY direction -- a parameter whose default silently picks the less-safe option is exactly the footgun ST5 exists to close elsewhere in this engine, and section_names (the sibling closed-key-space parameter) is already required with no default, so this brings top_level_keys in line with it rather than introducing a new pattern.
  - Cost was real but one-time and mechanical: no loader wires this in yet (FEAT-713/714 are still ahead), so the only call sites were my own 20-ish test calls -- updated every one to state its top_level_keys explicitly (mostly =None, since most of those tests are about a different mechanism entirely and were already relying on the open default).
  - Falsified via a scratch pyright probe: a bare merge_override(base, override, section_names, origin) call (no top_level_keys) now errors 'Argument missing for parameter top_level_keys'; reverted the signature to the old default=None and the identical probe passed clean with zero errors, reproducing the fail-open; restored, error back.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — One structural fault is reported two or three times

<!-- sq:finding:F13:body -->
**Reproduced.** Report quality on the collected channel, not correctness.

Because every mechanism collects and the pipeline keeps walking in collect-all mode, one
structural fault surfaces once per walk that meets it:

- a 400-level dotted-key override → **2** violations: `nesting exceeds 300 levels while
  resolving` and `… while copying`. Same subtree, same cause, two lines.
- a resolver-deep override whose token splices a deep base subtree → **3** violations, same
  cause.
- a top-level key in token territory with `top_level_keys` supplied → **2** violations:
  `unknown top-level key '$(items)'` from the top-level check and `splat-ref token '$(items)'
  used as a key` from the resolver. One mistake, two diagnoses, and the second is the useful
  one.

Fail-fast is unaffected — it raises the first and stops — so this is only a lint-report
concern. It is the direct cost of the design decision to keep walking, which is the right
decision; the noise is a side effect, not evidence against it.

Info severity: nothing is wrong, nothing is missed, and a caller can de-duplicate. Filed
because the collected report is an adopter-facing surface and "three lines for one fault"
reads as three problems.

Recommendation, cheapest first: for the depth case, have the resolver's refusal suppress the
copy-side refusal for the same dotted path (or de-duplicate on `(path, reason-class)` in
`merge_override` before returning). For the token-key case, consider skipping the top-level
name check for a key already in token territory, since the key refusal names the real problem.
Neither is worth a fix on its own — worth doing if this code is touched again.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-07-31T16:22:04Z] Catherine Manager:
  - Not worth a round on its own: duplicate reporting of one structural fault is lint noise, not a wrong verdict, and the reviewer scoped it as worth doing only if this code is touched again. Revisit when a loader wires the engine in and the lint output gets its first real reader.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — A leading literal double-dollar sigil cannot be written

<!-- sq:finding:F14:body -->
**Reproduced.** A documentation obligation, not a code defect — the behaviour follows from the
rulings and I am not re-litigating either.

`_unescape_leading_token` strips one leading `$$(` → `$(` and touches nothing else. Combined
with territory being "begins with an unescaped `$(`", the escape is **not surjective**: no
input produces a string that *begins* with a literal `$$(`.

```
"$$(x)"      -> "$(x)"        (escape applied)
"$$$(x)"     -> "$$$(x)"      (unchanged — not territory, no leading "$$(")
"$$$$(x)"    -> "$$$$(x)"     (unchanged)
"$$($$(x))"  -> "$($$(x))"    (leading escape only)
```

Checked exhaustively over those shapes: nothing yields a leading `$$(`. There is no
double-the-escape rule (`$$$$(` → `$$(`), which is how most escape schemes stay complete.

The related asymmetry, also reproduced and also correct per the narrowing ruling:

```
"$$(docs) here"     -> "$(docs) here"        (offset 0: escape)
"see $$(docs) here" -> "see $$(docs) here"   (any other offset: literal text, kept verbatim)
```

So the same three characters mean "escape" at offset 0 and "two dollars and a paren" everywhere
else. That is the ruled behaviour and the standing `tests/meta` guard proves no bundled string
value begins with the sigil, so the writers' duty stays vacuous. But an adopter reading
"`$$(` escapes a literal `$(`" will write it mid-string and silently get two dollars.

ADR-696's own test for whether a refusal is legitimate is *whether the adopter retains a way to
say the thing*. For `$(` at the start they do. For `$$(` at the start they do not — a gap worth
knowing about even if no document needs it.

Info severity, and it belongs on the adopter-grammar doc obligation rather than on this module:
the doc has to say that the escape applies **only** at the start of a string, that a sigil
anywhere else needs no escape and gets none, and that a leading literal `$$(` is not
expressible. A one-line note in the module docstring pointing at the same fact would keep the
next reader of `_unescape_leading_token` from "fixing" it into a global replace.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-07-31T16:22:06Z] Catherine Manager:
  - Home item is TASK-719 (adopter grammar reference), where the obligation is recorded alongside the leading-sigil escape rule; the two are one paragraph for a reader. Stays open here until that documentation lands.
- [2026-08-03T07:45:09Z] Catherine Manager:
  - Closed: the adopter grammar reference documents the leading-sigil escape rule, including that a value cannot begin with a literal double-dollar form.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-31T14:17:20Z] Paul Reviewer:
  - Verdict: ChangesRequested on 3 medium findings; the mechanism itself is sound. Reviewed 562bba6 on 10bb523 by reading the module and driving it from a scratch harness over the real bundled workflow/roles/playbook documents as bases.
  - All three previously reported defects verified fixed, and fixed beyond the exact case reported: the whole misshapen-selected family fails closed (bare-string, int, bool/int/nested-list/table elements, non-table selected); the merged mapping shares no dict or list object with base OR override at any depth, including splat-spliced tables and spread lists; base key order is preserved at three nesting levels and survives the apply_selected rebuild. Also verified: single-pass and base-only resolution, order-independence over a splat target, collect-all spanning resolution and both selected violation classes, deterministic first violation in fail-fast, merged None in every violating case driven, and no floor check of any kind in the module (only internal import is squads._errors).
  - The three mediums are all input shapes, same class as the defects already closed. F1: a selected list whose section is present but not a table silently does nothing — the one deselect failure mode no check on the resulting spec can see, because a drop that never happened leaves a valid spec. F2: the splice half of the stated type-mismatch failure case has no implementation at all (four shape-changing splices pass through clean); bounded by the models catching it later, but it stops being a MergeViolation and cannot be collected in lint mode. F3: an out-of-grammar splat path is reported as a surviving literal with a hint telling the adopter to do what they already did.
  - F2 and F3 each need one architect line, not just code: F2's criterion as worded needs schema knowledge the engine must not have, so the implementable reading (compare against the base shape at the destination) makes a splice stricter than a hand-written value; F3's second half is that the path grammar is narrower than TOML's key space (no hyphen, no leading digit) while accepting non-ASCII everywhere but the first character.
  - F10 is the suite. 108 green tests could not have found any of the three original defects or any of F1-F9: it asserts one example per implemented branch, never a family of shapes at one position. Unasserted invariants named in the finding — order preservation through the pipeline (every merge_override/apply_selected membership assertion goes through set()), input independence beyond one dict, merged-is-None on violations, and first-violation identity plus message content in fail-fast.
  - @manager @python-dev findings F1-F10 on REV-722 with reproductions in each body. Not approving — the approval transition is a second party's. I would have this Approved once F1 is closed and F2/F3 have either a fix or a recorded narrowing; F4-F9 are low and can ride the same pass.
- [2026-07-31T14:28:19Z] Robert Architect:
  - @reviewer @tech-lead RULING A on F2 — the criterion is narrowed, and your asymmetry objection is the reason rather than a cost to weigh. Recorded as ADR-696 §4a (dated amendment note); F2 can be closed as WontFix-with-a-narrowing once TASK-716's acceptance is restated, not fixed in code.
  - The governing rule I have added: a splat-ref is an ABBREVIATION for a value the adopter could have written literally, and is held to the same standard as that expansion — no stricter, no looser. $(items.task.validators) means 'the value the bundled spec holds there'; the whole purpose is to avoid restating a bundled value that would otherwise stop tracking. An abbreviation refused where its expansion is accepted is a broken abbreviation: the adopter could not express through a splice a value they may write out longhand, and the two forms would produce the same merged mapping with different verdicts. So the base-shape comparison is not the implementable reading to adopt — it is the reading that rule forbids.
  - What the engine owes, exactly four failures and no fifth, each a property of the token and its operator rather than a claim about the destination: (1) dangling path; (2) spread whose base value is not a list; (3) spread with no surrounding list; (4) malformed or surviving token — which is where your F3 lands, reported AS a malformed token quoting the path and what a path may contain, not as a surviving literal. A splice is never checked against the shape of the key it lands on. 'A table where a scalar is due' is withdrawn, not reinterpreted.
  - Nothing is unguarded by that: a splice can only produce a value the bundled document itself holds, landing at the wrong key, and the strictly-typed models reject exactly that with a per-field error. Shape is the models' plane, composition is the engine's — the same boundary that keeps the floor out of this module.
  - On the collect-all cost you named, which I am not waving through: it is real, and it is not specific to splices — a hand-written wrong-shaped value produces the same single opaque finding, and lint's phase 2 stops there. Privileging splice-caused shape errors as the one collectable kind would make lint read as arbitrary. So the concern belongs to a different question: whether the loader translates a pydantic ValidationError into per-field lint findings instead of one blob. Its per-field error list makes that answerable, and answering it fixes the whole class at once. Recorded in §4a as the right home; deliberately not folded into the splat grammar. Worth a finding of its own against the loader work if you want it tracked — that is your call, not mine.
  - F4 answered while I was in the same sentence, since leaving it ambiguous after it was reported would be worse: the token grammar and the $$( escape are VALUE-only. A key is vocabulary — a type name, a status name — never resolved, scanned, or unescaped. Now stated in §4a rather than being neither, which was your objection.
  - F3's second half (path grammar narrower than TOML's key space; non-ASCII accepted after the first character but not at it) and F9 (self inside a nested list) I have not ruled on here — they are separable grammar questions and neither is reachable against today's bundled documents. Flagging that I know they are open rather than leaving you to assume they were folded in.
- [2026-07-31T14:48:51Z] Robert Architect:
  - @reviewer @tech-lead F3 (second half), F6 and F9 are all ruled; recorded as ADR-696 §4a with a dated amendment note. All three were verified by driving the engine, not by reading it.
  - F3 grammar half — WIDEN. A path segment becomes a TOML bare key (A-Za-z0-9_-). Your three symptoms have one cause and one fix: hyphens and leading digits become addressable, and the non-ASCII asymmetry you spotted resolves correctly rather than arbitrarily — TOML bare keys are ASCII, so a non-ASCII key is a quoted key and is unaddressable by rule instead of by accident of a character class. Widened rather than documented as a restriction because of the abbreviation rule now governing §4a: a value the adopter may write literally must stay expressible as a reference.
  - One correction to the exposure, since it changes what the finding is about. Your note said nothing is unreachable yet and the day a BUNDLED key is hyphenated the failure is the misleading message — that is exactly right, and it is the whole of it. Resolution is base-only, so a path can only ever address a bundled key. Driven: hyphenated key in the base + explicit path → malformed-path refusal (the real bite); adopter's hyphenated CUSTOM key with $(*self) → dangling, which is correct and identical under any grammar; hyphenated custom key addressing a bundled path → merges cleanly today, the hyphen being in the destination not the path. So the restriction binds squads' own vocabulary, not an adopter's — which is why the residual quoted-key case needs no adopter-facing documentation.
  - Your related edge (dotted quoted key mis-navigated by _dotted/_lookup_base_path) — the key stays unaddressable by definition, because '.' is the path delimiter and a quoted-segment sub-grammar would be a second nested syntax for a case no document has. But it must not mis-navigate, and the fix is the same standing guard rather than a runtime check: every bundled key is a TOML bare key, folded into the scan that keeps a bundled string value from beginning with the sigil. Audited all three bundled documents — 353 + 77 + 131 keys, every one already a TOML bare key, so the guard passes as written and the mis-navigation becomes unreachable rather than merely unlikely.
  - F6 — DEPTH GUARD, and the contract stays unqualified. Your reasoning is the reasoning I adopted: tomllib accepted the document so it cannot be the guard, and the engine's inputs are adopter-authored by design. Qualifying 'never a traceback' would weaken a stated invariant to match code that could cheaply satisfy it, which is how invariants stop meaning anything. Specified by two properties rather than a number (far above any hand-authored document — the deepest bundled key path is four levels; far below the interpreter's headroom with room for the per-level copy), binding both the resolution and the merge walks, and checked before recursing or copying — that last part matters because your ~3000-deep untouched base fails inside deepcopy rather than in the engine's own frame, so a guard only on the resolver would miss it.
  - F9 — behaviour stands, now definitional. self means the nearest enclosing KEYED path at any list depth, because a list index has no dotted name to contribute; that is what 'the key currently being written' already meant. Note your conservative reading (a nested self is a violation because the surrounding shape is not the key's shape) is already answered by §4a's abbreviation rule — destination shape is the models' plane, not the engine's — so it follows from F2's ruling rather than being an independent call. Your two adjacent cases are pinned as intended: an empty base list spreads to nothing added (a value the base holds, distinct from a missing key, which dangles), and one base list spread twice duplicates it (compose-only permits it; nothing needs set semantics).
  - That closes every finding needing an architect line. F1, F5, F7, F8 and F10 are engineering calls with no grammar question in them, and the loader ValidationError-to-per-field-lint question I raised on F2 is being tracked against the loader work rather than here.
- [2026-07-31T15:27:35Z] Robert Architect:
  - @tech-lead @python-dev F4 settled, and the ambiguity was mine — my sentence bundled a correct claim ('never resolved') with a wrong one ('never unescaped') and left the operative case ('refused') unstated, so both readings were fair. ADR-696 §4a now states it in one place; the dated amendment note records what replaced what.
  - READING B GOVERNS — a token-shaped key is REFUSED. Reading A's pass-through loses on two grounds. The engine's refusal is not it legislating vocabulary, because the escape keeps every name expressible: a project wanting a key spelled with the sigil escapes it and gets it, so the requirement is unambiguous spelling in a document where the sigil is reserved. And 'leave it to the models', which is the right answer for shape, is not available for keys — I drove it: a spec declaring an item type literally named with a token loads CLEAN, takes a prefix-map entry, and resolves a folder. A section's keys are the open vocabulary the models deliberately do not constrain, so deferring to them defers to nobody. That makes the engine the only thing between a typo and a minted vocabulary entry, which is the surviving-token rationale at its strongest.
  - On the tension the tech lead is right to have spotted with my earlier rulings: the test that separates them is whether the adopter retains a way to say the thing. Refusing a splice on the base's shape would have left a value expressible literally but INEXPRESSIBLE as a reference, with no escape — so it lost. Refusing a token-shaped key removes nothing, because the escape recovers it — so it stands. Same principle, opposite outcomes, and the difference is the escape rather than a change of mind about whose plane vocabulary is.
  - Scope of the refusal, answering the three parts separately. (1) A grammar-valid token as a key — refuse, distinctly, as the dev has it: 'used as a key, keys are never a splat target' is the right message because resolving it is undefined rather than malformed. (2) A malformed token-shaped key — refuse, as the dev has it, with F3's malformed-token message. Both follow from one predicate: the key is in token territory because it BEGINS with an unescaped sigil. (3) Any OTHER unescaped sigil in a key — over-wide, and should narrow to leading-only for the same reason values did. Not a key-specific mistake, though: it is the same _process_literal_string predicate, so it is one fix in one place, not two.
  - The escape IS unescaped in keys. My 'value-only' phrasing was the error, not the dev's code — the two go together necessarily: refusing a leading sigil in a key is only legitimate BECAUSE the escape gives the adopter the literal key back. So the dev's behaviour is correct and self-consistent; the sentence describing it was not. A key containing the escape unescapes to a single sigil, exactly as a value does.
  - One live gap found while driving this, and it is not F4 — the token-territory narrowing I ruled for shell safety is NOT in the code. Driven: an override value of 'git commit -m "$(cat msg)"' is still REFUSED as a surviving token, and so is a leading-sigil shell string. _process_literal_string still flags an unescaped sigil ANYWHERE in the string, which is the wide predicate the §4a narrowing replaced. So the playbook shell-content case that narrowing exists for is still failing closed, and the same over-wide predicate is what makes part (3) above wrong for keys. One fix in _process_literal_string closes both. Flagging it rather than assuming it was known, since the ruling has been reported as landed.
- [2026-07-31T15:57:22Z] Catherine Manager:
  - Ruling B's narrowing landed. Residual, not a defect: a value beginning with the sigil is still refused (as malformed rather than as a surviving token), so leading-substitution shell lines need $$(. Legitimate under ADR-696 §4a's own test — the adopter keeps a way to say it — so this closes as a documentation obligation on TASK-719, not code.
- [2026-07-31T16:08:02Z] Paul Reviewer:
  - Delta re-review of 562bba6..6e7a328 (module + its four test modules + tests/meta). Every one of F1-F10 verified closed on the current tree by driving it, not by reading the diff — and verified to still hold after four rounds of change stacked on top of them. Four new findings: F11 medium, F12 low, F13/F14 info.
  - F1 closed and correctly split: a section present but not a table now collects a violation naming the shape, while an absent section stays inert; driven for a list-valued section, an empty-list section, and a section the override shadowed to a scalar. F3 closed at both halves: hyphenated and digit-leading bundled keys now resolve, and nine out-of-grammar shapes all report the malformed-path message with the segment grammar in the hint, including the unclosed-token fallback. F4 closed symmetrically: a grammar-valid token key and a malformed token key are refused distinctly, an escaped key unescapes, and a sigil after the first character is data in a key exactly as in a value. F5 closed by fullmatch. F7/F8 closed as contract precision, and the narrowed independence claim is now exactly as true as the code — the residual tuple case is described rather than overclaimed. F9 unchanged in behaviour and now definitional.
  - F6 is the one I pushed hardest, because a bound guarding two walks is easy to get right in the reported shape and wrong in a composite. It holds. Clean collected refusals at 305, 900, 5000 override levels; 305, 900, 3000 untouched-base levels; 295/305 nested-list levels; and — the shape that would have broken a single-sided guard — merge-recursion 600 plus copy 600, and resolver-recursion 600 plus a deep splice copy, both refusing cleanly with no RecursionError. Fail-fast raises a clean SquadsError naming the dotted path, and merged is None on the depth channel too. The bound is placed on both walks and checked before recursing or copying, as ruled.
  - F11 is the one to act on, and it is in the new mechanism. The engine defines, consumes and strips [selected], but the top-level check tests the override's keys against the caller's set verbatim — so top_level_keys=frozenset(base.keys()) (the most natural derivation a loader will reach for) and top_level_keys=<the six sections> (what every other test in the file passes) both REFUSE a legal [selected] override on the load path. Only sections | {selected} works, and exactly one test passes that spelling, so the requirement lives as folklore rather than as a contract. It fails in the refusing direction on a document the adopter got right, which is why it is medium.
  - The other new mechanism, the closed key space, is otherwise sound: it catches the mistyped section name (the actual fail-open, not just a bogus key), catches the retired override_base stamp, is gated on 'is None' rather than truthiness so an empty accepted set refuses everything, and cannot be bypassed by an escaped key spelling. F12 is only that its default is off — right value for the roles loader, wrong default for a check that exists to close a silent gap.
  - Test suite, against my own F10 standard: honestly closed. All five invariants I named are individually pinned, including the two I said were surviving on nobody's guard — order through the deselect rebuild, and independence through the entry point over an untouched base list plus a spliced table plus a spread list. The empty-override test now asserts key order, not just equality. I falsified the shared _unknown_key_violations helper myself by neutering it at runtime: both callers went to zero violations, so the dev's claim that both depend on it holds. One residual, stated as coverage rather than defect: the shape table (_MALFORMED_PATHS) is parametrized over the dict-value position only, and the key and list-element positions are covered by hand-written tests instead — so it is positional coverage, not the position-by-shape cross product, and the specific uncovered combination is what let F11 through.
  - @manager @python-dev verdict: I would Approve once F11 is closed; F12/F13/F14 need no code before approval — F12 is a signature choice, F13 is lint-report de-duplication worth doing only if this code is touched again, and F14 is a line for the adopter grammar doc. Leaving the status at ChangesRequested for F11 alone; the transition stays with a second party. On your note about weighting: F13 and F14 are filed at info deliberately, and F14 says in its first line that it is a documentation obligation, not a code defect.
- [2026-07-31T16:22:24Z] Catherine Manager:
  - Approved as the second party: the reviewer recorded ChangesRequested for F11 alone and stated he would approve once it closed. F11 is fixed and independently verified against all three derivations of the accepted set (including an empty one), with the mistyped-section fail-open confirmed still closed. Twelve of fourteen findings Fixed, F2 WontFix as a recorded narrowing, F13 WontFix, F14 tracked on TASK-719. Full suite 2243 passed / 6 skipped.
<!-- sq:discussion:end -->
