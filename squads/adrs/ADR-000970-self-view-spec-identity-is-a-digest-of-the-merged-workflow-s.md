---
id: ADR-970
sequence_id: 970
type: decision
title: Self-view spec identity is a digest of the merged workflow spec
status: Accepted
author: architect
refs:
- BUG-962:addresses
- ADR-880
- TASK-969
description: The self-view spec block gains an equality-only digest of the merged
  workflow spec; override stays as a display flag
created_at: '2026-09-29T13:41:18Z'
updated_at: '2026-10-25T21:41:21Z'
---
<!-- sq:body -->
## Context

A `self`-source view's `--json` (`sq workflow view <name> <id> --json`) is the host item's own
`show --json` plus a `spec` block, today `{schema_version, override}`, built by
`_spec_identity_json` in `_cli/_workflow_cmd.py`. `override` is
`(squad_dir / ".overrides/workflow.toml").is_file()` (read). The block shipped in 0.15.0 and
is listed in `docs/stability.md` Tier 3, where `--json` shapes change additively only (read).

BUG-962 (driven by QA on a scratch squad): two valid override documents whose merged specs
differ (`Draft` badge `"A"` vs `"Z"`) emit the same block, so a client comparing blocks to
detect a spec change gets a false negative.

Three facts bound the answer:

- **Only the workflow spec resolves this payload** (read). `build_item_json` consults the
  active `WorkflowSpec` alone: badges and the sub-entity kind. Neither the playbook nor the
  role catalog feeds a `self` payload. `playbook` and `role` sources emit their own fully
  resolved data, so a client reading those has no need for an identity to detect change.
- **Loading is fail-closed** (read). `load_workflow_spec` raises on any rejected override
  document, and `open_service`/`get_active_spec` refuse every read that consults the spec.
  A `self` payload is never produced under a rejected override. When one is produced and the
  file is present, that file was merged.
- **The bundled spec changes between releases.** A squad whose override bytes stay the same
  still resolves a different spec after an upgrade, and a squad with no override has no
  override bytes at all.

### Options

1. **Hash the override documents** (workflow, playbook, roles). Rejected. It gives a false
   negative on every upgrade that changes the bundled spec, and a constant value for every
   squad with no override. It gives a false positive on a comment or whitespace edit. It
   also covers two documents that do not resolve this payload.
2. **Digest the merged workflow spec.** Chosen. It changes exactly when the spec that
   resolved the payload changes, whatever caused that: an override edit, an upgrade, or a
   `[selected]` drop.

## Decision

**1. The block carries `digest`, a digest of the merged, validated workflow spec.**

- The input is the spec the payload was resolved against: the service's threaded spec
  (`Service.spec`). It is never re-read from disk and never inferred from file presence.
- Canonical form: `spec.model_dump(mode="json")`, serialised with
  `json.dumps(..., ensure_ascii=False, separators=(",", ":"))` and encoded as UTF-8. Keys are
  **not** sorted. Dict order is the order the merge produced, and it can carry meaning (type
  and badge order). A set-valued field, if one is ever added, is emitted sorted. None exists
  today (read: no `set`/`frozenset` field on the spec models).
- Value: the lowercase hex SHA-256 of those bytes, 64 characters, with no prefix.
- Scope: the workflow spec only. The playbook and the role catalog are out, for the reason
  given in the context.

**2. Clients compare `digest` for equality only.**

- The same digest means the same merged workflow spec. A different digest means the client
  treats the spec as changed and re-reads the catalogs it caches (`sq workflow types --json`
  and its siblings).
- The value is opaque. A client never orders it, parses it, or computes it itself.
- Only one direction is guaranteed: two different merged specs never share a digest. The
  reverse is allowed. A squads release can change a digest with no change in meaning
  (bundled content, serialisation), and so can an override edit that only reorders keys the
  merge then emits in a new order. A client that re-reads once too often is correct.

**3. `override` stays, and its meaning is restated.**

- Removing or renaming it would break the Tier 3 additive rule for no gain.
- It means: a project `.overrides/workflow.toml` was merged into the spec that resolved this
  payload. Fail-closed loading makes the presence check equivalent to that. The docstring's
  "in force" wording is replaced with this sentence.
- It is a flag for display ("customised"), not an identity. A client never uses it to detect
  change. That is what `digest` is for.

Resulting shape: `{"schema_version": <str>, "override": <bool>, "digest": <str>}`.

**4. This decision places the digest only on the `self` block.** It adds no identity key to
any other `--json` surface.

## Consequences

- An additive Tier 3 change. The `self` entry in `docs/stability.md` becomes
  `{schema_version, override, digest}` with the equality-only rule, which is a tech-writer
  refresh, plus a CHANGELOG entry.
- No VS Code code reads this block today (read, per BUG-962 and TASK-969 ST4). When the
  client starts reading it, the exact-key skew canary should cover it.
- Cost: one dump and one hash per `self`-view `--json` call, which is negligible (inferred,
  not measured).
- Test shapes that follow from this: override A vs B differ; A vs A with comments or
  whitespace changed are equal (the merge is unchanged); none vs an override that restates a
  bundled value may be equal, and a test must not assert either way; a rejected document
  refuses the command (exit 1, no payload) and yields no digest; two runs on one squad
  produce identical blocks; a playbook-only or roles-only override leaves the digest
  unchanged.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-29T13:45:25Z] `architect` Robert Architect:
  - @op-pierre for your call: left Proposed. Written to settle the TASK-969 ST4/ST5 questions the tech lead raised.
- [2026-09-29T13:52:52Z] `op-pierre` Pierre Chat:
  - Accepted.
- [2026-10-25T21:41:21Z] `architect` Robert Architect:
  - Audited 2026-10-25: holds. _spec_identity_json in _cli/_workflow_cmd.py emits schema_version, override, digest as decided; docs/stability.md and docs/workflow.md carry the equality-only rule.
<!-- sq:discussion:end -->
