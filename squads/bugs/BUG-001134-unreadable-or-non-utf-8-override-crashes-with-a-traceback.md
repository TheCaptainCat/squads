---
id: BUG-1134
sequence_id: 1134
type: bug
title: Unreadable or non-UTF-8 override crashes with a traceback
status: Open
parent: MILE-1051
author: qa
priority: medium
refs:
- REV-1133
created_at: '2026-10-25T05:10:06Z'
updated_at: '2026-10-25T05:10:06Z'
---
<!-- sq:body -->
Expected: an unreadable or non-UTF-8 override file is reported as a clean SquadsError (message plus exit 1, same wording family as the existing unreadable-override error that `sq role list` already gives), never a Rich traceback.

Actual: tracebacks in three places.

1. `sq check` with `squads/.overrides/roles.toml` unreadable (mode 0) raises PermissionError; with non-UTF-8 content it raises UnicodeDecodeError. Both come from `_roles_catalog_override_shadows_bundled` in `src/squads/_overrides/_service.py`, which reads the file itself outside the loader's wrapping.
2. A non-UTF-8 `.overrides/workflow.toml` crashes `sq workflow lint` with UnicodeDecodeError. Other commands report it through the override-load error but quote the raw codec text.
3. A non-UTF-8 `.overrides/playbook.toml` crashes every command (e.g. `sq list`) with UnicodeDecodeError.

Reproduction (fresh scratch squad, never the live one): `printf '\xff\xfe' > squads/.overrides/<doc>.toml`, or `chmod 0` an empty one, then run the command named above.

Cause: the shared loader `src/squads/_specload.py` keeps `OverrideMessages.not_utf8 = None` for the workflow and playbook descriptors, so the error propagates raw.

Suggested fix direction: give the workflow and playbook descriptors a `not_utf8` message like the role catalog has; make the shadow and stamp probes in `_overrides/_service.py` fail soft on OSError/UnicodeDecodeError (the loader's refusal already reports the file); add rows to `tests/unit/test_spec_override_read_errors.py`.

Severity: medium. Predates the module-split refactor (identical output before and after).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
