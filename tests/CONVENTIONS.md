# tests/ — authoring conventions

**Status: Phase 1 scaffold (FEAT-231).** This document governs `tests/unit/`, `tests/service/`,
`tests/cli/`, `tests/integration/` — the new tree Phase 2 authors into. The old flat `tests/test_*.py`
suite predates this document and is unaffected by it; it is retired wholesale in Phase 3, not
edited to comply. `tests/COVERAGE_LEDGER.md` is the companion artifact: it maps every contract the
old suite protects to a target layer/pillar below — read it before authoring a new test so you
land it in the right place and don't re-derive a home that's already decided.

## 1. The four layers

Each test lives in exactly one layer, chosen by what it needs to exercise its claim — not by
which file happened to already test something nearby.

| Layer | Scope | Needs `project`/`svc`? | Asserts on |
|---|---|---|---|
| `tests/unit/` | Pure functions, models, spec logic. No filesystem, no CLI. | No — in-process values only (build a `WorkflowSpec`/`Item`/etc. directly) | Return values, raised exceptions |
| `tests/service/` | The `Service` facade + `IndexStore` — real filesystem, no CLI | `svc` (and `project`, which `svc` depends on) | Return values **and** on-disk frontmatter/index state |
| `tests/cli/` | The public command surface, via `CliRunner` | `project`, `runner` (or `invoke` for async tests) | Exit code, stdout/stderr text, `--json` shape, generated files |
| `tests/integration/` | Multi-step workflows and migration round-trips — explicitly cross-layer | Composites of the above | End-to-end behaviour a single layer can't observe alone (e.g. init → migrate → no dangling pointers) |

Repo-artifact/packaging self-tests that read static repo assets (ref-hygiene scans, the docs
registry, "ships in the wheel" checks) still count as unit — "no filesystem" means no squad tmp
dir, not never opening a file.

**Placement rule of thumb:** if a unit test would prove the claim, it belongs in `unit/` even if a
`cli/` test *could* also exercise it — see §5 (dedup discipline). A test only belongs in
`integration/` when the claim genuinely requires chaining two or more operations that no single
layer's fixture set can express alone (a migration round-trip, an init-then-sync-then-migrate
sequence, a backend's full scaffold→write→remove lifecycle).

### Adding a fifth layer

Don't. If a new kind of test doesn't fit unit/service/cli/integration, it's a sign the claim needs
decomposing into pieces that do, not a sign the taxonomy needs to grow. If a genuine new layer
becomes unavoidable, it needs its own row in this table (scope + fixture contract) and a note in
the feature/task that added it — not a silent new top-level directory.

## 2. The four pillars

Layers are *where* a test lives; pillars are *what portfolio of tests* a contract area needs. Every
contract area in the ledger should have some presence in each relevant pillar, not just exhaustive
per-type coverage:

- **P1 — generic-engine-once.** The mechanism is tested once, against the spec-driven engine, not
  once per configured type. E.g. `can_transition`/`fields_for`/badge resolution/the sub-entity
  head-render mechanism each get one focused unit/service test of the mechanism itself, keyed on a
  spec, not N near-identical per-type copies.
- **P2 — spec-as-artifact + goldens.** The bundled workflow/playbook/role spec is a tested,
  versioned artifact: shape validation, reserved-vocab guards, and a byte-identical golden of its
  rendered/loaded form. A golden here pins what "the shipped spec" means, the same way a rendered
  template golden pins what "the shipped output" means.
- **P3 — thin behavioral spine.** A small set of tests proving one concrete configured type (or
  one concrete backend) behaves correctly end-to-end through the generic engine — `sq check`,
  retype, skill-gen, a full lifecycle. One instance is enough to prove the mechanism reaches the
  surface; don't multiply it per type, that's what P1 already covers generically.
- **P4 — failure/edge surface.** First-class, not an afterthought: invalid/unknown vocab at the
  load boundary, malformed spec, reserved-vocab violations, override-merge conflicts, custom-type
  edge cases, force-bypasses-edge-not-vocabulary, dropped-type no-crash. This is the pillar the old
  per-type-enum suite structurally couldn't have (bad vocab was impossible when types were enums) —
  budget for it explicitly rather than treating it as leftover coverage.

A single ledger row often names a specific pillar; when it doesn't, infer it from the claim's
shape (mechanism-once → P1, spec/golden → P2, one-type-proves-it-works → P3, anything about
rejection/malformed input/no-crash → P4).

## 3. Naming rules

A test name (file, class, or function) must complete the sentence **"This system guarantees
that…"** without requiring the reader to know anything about this project's development timeline.

**Banned, no exceptions:**
- `layer_a` / `layer_b` — ADR framing vocabulary, not system vocabulary.
- `golden_lock` — a technique name, not a behavior name. Name what's pinned, not how it's pinned
  (`test_bundled_spec_is_byte_identical_to_the_golden`, not `test_golden_lock_spec`).
- Any `FEAT-`, `TASK-`, `ADR-`, `REV-`, `BUG-` reference (file name, test name, or docstring).
  Ticket pointers belong in commit history, not the test tree — this is the same project rule that
  bans ticket IDs from source (`tests/test_squad_ref_hygiene.py` enforces it for `src/`+`docs/`;
  Phase 2 extends that scan to cover `tests/` too, closing the loop mechanically).
- A ticket ID embedded in a *filename* specifically (e.g. the old suite's
  `test_workflow_renderer_261.py`) — same rule, just the file-level instance of it.

**Discouraged, use judgment:** a `*_characterization` suffix names the technique ("pin today's
behaviour before a refactor") rather than the behaviour. Prefer folding the test into the ordinary
behavior-named file for its contract area. It's a legitimate general testing term, not a
squads-internal acronym, so this is a softer call than the four bullets above — but default to a
behavior name unless there's a specific reason the characterization framing earns its keep.

**Correct form** (from FEAT-231 itself):
```
test_item_id_is_globally_unique
test_cli_json_output_has_no_ansi_escapes
test_migration_preserves_ref_kinds_across_schema_versions
```

## 4. Fixtures

- **Cross-layer fixtures live in the root `tests/conftest.py`** — `frozen_time`, `project`, `svc`,
  `runner`, `invoke`, `run_in_thread`, and every autouse leak-guard (clock, actor,
  `_active_spec`/`_active_dir` + custom-command caches, the rendering-engine ContextVar/env-cache,
  the `FORCE_COLOR`/`COLUMNS` neutralization). Pytest's normal conftest resolution makes these
  visible in every subdirectory automatically — nothing needs re-importing per layer.
- **Per-layer `conftest.py` files exist under each of `tests/unit/`, `tests/service/`,
  `tests/cli/`, `tests/integration/`** as the documented home for a fixture that only that layer
  needs. They start empty (a docstring only) — add to them, don't invent a fifth location.
- **Never construct a `project`/`svc`/`runner` fixture by hand inside `tests/unit/`.** If a unit
  test needs one, that's a sign the claim belongs in `service/` or `cli/` instead.
- `tests/fixtures/corpus/*` (the frozen migration-input snapshots, v0.1 through v0.8) are
  layer-agnostic shared assets, not fixtures in the pytest sense — they stay under `tests/fixtures/`
  regardless of which layer's test consumes them, and are never edited by hand. The standing rule
  in `tests/fixtures/corpus/README.md` ("add a fixture on every schema bump") carries forward
  unchanged.

## 5. Dedup discipline: assert each invariant once, at the lowest meaningful layer

The core rule from FEAT-231 Principle 4: **a contract about `Item.id` format belongs in a unit
test, not in five CLI smoke tests.** A CLI test proves that a command exits cleanly and produces
parseable output — not that the underlying model fields are well-formed (that's already proven at
the unit layer). Before adding a test, ask: *does an existing test at a lower layer already prove
this specific fact?* If yes, either the new test is proving something genuinely different at its
own layer (e.g. "the CLI reaches the validator" vs. "the validator itself is correct" — both are
legitimate, at different layers) or it's a duplicate.

`tests/COVERAGE_LEDGER.md`'s "Duplicate-invariant clusters" section is the worked reference for
this — e.g. "repair idempotency" was independently re-asserted per feature (seeding, skill
migration, custom-type paths, repad) instead of once, generically, parametrized over setups. When
in doubt, match the shape of one of those clusters:
- **Genuine duplicate** → consolidate to one test (possibly parametrized) at the lowest layer that
  can express it.
- **Deliberate repetition at a wiring point** → keep it, but say so. The ledger's slug-validation
  cluster is the model: the *validator* gets one unit test, but each CLI surface that calls it gets
  its own thin test, because each surface is an independent place the wiring could regress. Don't
  collapse a "this call site remembers to check" claim into the "the check itself is correct" claim.

## 6. Golden / snapshot protocol

- **Pin all inputs.** A golden test fixes the full roster (which roles, which dev), every relevant
  flag, and the frozen clock (`frozen_time`). Never "whatever init defaults to today" — an
  unpinned input is how a golden ends up silently anchored to the very artifact it's meant to
  guard.
- **Source of truth is a manually-reviewed reference render, not a prior run's output.** A golden
  file is derived from a known-good render that a human (or the reviewing agent) actually read and
  approved — never generated from the code under test without that review, and never regenerated
  silently. Updating a golden is always an intentional, reviewed act.
- **One golden per distinct rendering path.** Two goldens that differ only in one flag value are
  redundant — parameterize the flag inside one test instead of duplicating the golden file.
- **Location:** goldens live under `tests/goldens/` (rendered artifacts) or `tests/fixtures/`
  (structured input/output pairs) — never inline in the test body; a golden belongs in its own
  file so a diff on update is reviewable on its own terms.

## 7. Determinism

Carried forward from the existing suite's hard-won guards (see the root `tests/conftest.py`
docstrings for the specific bugs each one fixes):
- Clock: `frozen_time` / `clock.now()`, never `datetime.now()`.
- Filesystem: `tmp_path` isolation via `project`/`svc`; no writes outside the fixture directory.
- Environment: `FORCE_COLOR`/`CLICOLOR_FORCE`/`PY_COLORS` are stripped both at import time and
  per-test (an autouse fixture); `COLUMNS` is pinned to 80 so help-text wrapping is
  terminal-independent.
- Ordering: every autouse leak-guard exists because a real cross-test order-dependence bug was
  found and fixed — don't remove one because a test "doesn't seem to need it."

## 8. Scale / slow tests

The `@pytest.mark.slow` marker and `--run-slow` opt-in (root conftest) carry forward unchanged.
Phase 1 does not flip `addopts` to `-m "not slow"` by default — that flip, plus marking the actual
scale tests, is Phase 2's job (it lands together with the tests it's marking, not ahead of them).
