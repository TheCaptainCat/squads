---
id: BUG-962
sequence_id: 962
type: bug
title: self --json spec identity can't distinguish two override documents
status: Open
author: qa
severity: low
refs:
- MILE-934:targets
- REV-920
created_at: '2026-09-24T09:57:16Z'
updated_at: '2026-09-24T09:57:31Z'
---
<!-- sq:body -->
## Summary

`sq workflow view <name> <id> --json` for a `self`-source view emits the host item's JSON
plus a `spec` identity block, `{schema_version, override}` (`_spec_identity_json` in
`src/squads/_cli/_workflow_cmd.py`). `override` reports only whether
`.overrides/workflow.toml` exists on disk (`.is_file()`), not what it contains or what the
merge produced. Two squads with different override documents — or the same squad before and
after an override edit — report an identical identity block. A client comparing this block
across two payloads to detect a spec change would miss the change.

This also affects the `override` field's own claim: the docstring says it reports whether an
override is "in force" (i.e. applied), but the code only checks file existence, so a present
but unstamped or partially-rejected override document reads the same as a fully-applied one.

## Reproduction (driven, scratch squad, deleted after)

```
sq workflow views
  -> greeting_skill  self   (no name)
```

Baseline, no override:

```
sq workflow view greeting_skill ROLE-1 --json | jq .spec
{ "schema_version": "0.15", "override": false }
```

Scaffolded `.overrides/workflow.toml` with `[statuses.Draft]\nbadge = "A"`, valid load
(`sq workflow lint` clean):

```
sq workflow view greeting_skill ROLE-1 --json | jq .spec
{ "schema_version": "0.15", "override": true }
```

Changed the override's only content to `badge = "Z"` (still a different, valid document,
`sq workflow lint` clean):

```
sq workflow view greeting_skill ROLE-1 --json | jq .spec
{ "schema_version": "0.15", "override": true }
```

Identical block for two override documents whose merged spec genuinely differs (`Draft`'s
badge is `"A"` in one, `"Z"` in the other). A client polling this block to detect that the
spec changed gets a false negative.

## What's reported vs what a client needs

Reported: a boolean (file presence) plus the fixed schema version.

Needed for the stated purpose ("enough of the active spec's identity for a client to tell
which spec resolved the payload"): something that changes when the *merged* result changes —
not just this squad's `workflow.toml`, since `playbook` sources also read
`.overrides/playbook.toml` directly and `role` sources read `.overrides/roles/*.toml`.

## Open question for the fix (not decided here)

This is a contract decision, not a mechanical fix — flagging for @architect:

- what to carry: a digest of the merged spec result, vs. a hash over the override document
  set (workflow + playbook + roles)?
- what a client is entitled to compare it against (equality only, or something ordered)?
- whether `override` stays a presence boolean (rename/reword to match) or is replaced
  entirely by the digest.

No VS Code client consumes this block today (checked in REV-920's own review — zero hits for
`workflow view`/`milestone_rollup`/a `spec` identity key under `clients/vscode/src`), so
there's no existing consumer to break; the decision is about the contract's first real use.

## Provenance

Raised as REV-920 F10 (Open, info). TASK-959 ruled it out of that task's scope (see
TASK-959 discussion, Olivia Lead) — it needs its own ruling. Filed for 0.16 (MILE-934) per
operator ruling (op-pierre).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
