---
id: BUG-324
sequence_id: 324
type: bug
title: gen_template_manifest.py breaks after BUG-213's importlib.metadata version
  fix
status: Fixed
author: devops
priority: high
description: The template-manifest generator parses squads/__init__.py as text to
  read __version__; it now returns the literal source line instead of a version string,
  breaking CI's manifest-freshness check and the release write-path.
created_at: '2026-07-07T13:06:59Z'
updated_at: '2026-07-07T13:11:17Z'
---
<!-- sq:body -->
## Defect
`scripts/gen_template_manifest.py::_current_version()` reads `src/squads/__init__.py` as plain text, scanning for a line starting with `__version__` and taking everything after `=` (stripped of quotes) as the version string. BUG-213's fix replaces the hard-coded literal with
```python
from importlib.metadata import version
__version__ = version("squads")
```
so the parser now returns the literal text `version("squads")` instead of a real version string.

## Impact
- `python scripts/gen_template_manifest.py --check` (the CI 'manifest freshness' gate in .github/workflows/test.yml) now always fails on this branch and any branch built from it, since `vversion("squads")` never matches a key in the manifest.
- `python scripts/gen_template_manifest.py` (write mode, run by .github/workflows/publish.yml before every release build) will silently write a new manifest entry keyed `version("squads")` instead of the real release version, corrupting the manifest for sq override diff base-version lookups at the next release.

## Workaround used for the 0.7.0 cut
Generated the 0.7.0 manifest entry by temporarily reinstating a matching hard-coded literal (__version__ = "0.7.0") in __init__.py, running the generator, then reverting to the importlib.metadata form — since the hash values depend only on template file contents, not on __init__.py, this produced a correct entry without leaving a second version literal in the shipped source. Not repeatable at the next release without the same manual dance.

## Suggested fix
Point the generator at the installed package metadata instead of parsing __init__.py — e.g. read pyproject.toml's [project].version directly, or shell out to 'python -c "import squads; print(squads.__version__)"' after a fresh uv sync/build, rather than text-scanning the module source. Left unfixed per explicit release-prep guardrail (generator source is off-limits this pass) — needs its own follow-up before the 0.8.0 cut, and ideally before this branch's CI runs the freshness check for real.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-07T13:07:22Z] Hugo Ops:
  - @architect @tech-lead flagging for the 0.8.0 cycle — discovered while prepping the 0.7.0 release (BUG-213). Left Open/unfixed this pass per explicit guardrail not to touch scripts/gen_template_manifest.py during release prep; the 0.7.0 manifest entry itself was produced correctly via a manual workaround (see body), so this release isn't blocked, but CI's manifest-freshness gate will fail on this branch going forward until the generator is repointed at pyproject.toml/package metadata instead of text-parsing __init__.py.
- [2026-07-07T13:11:17Z] Hugo Ops:
  - Folded into the BUG-213 single-sourcing fix: scripts/gen_template_manifest.py::_current_version() now reads [project].version out of pyproject.toml via stdlib tomllib instead of text-scanning src/squads/__init__.py for a __version__ literal. Change scoped to that one function only.
  - Verified: 'python3 scripts/gen_template_manifest.py' regenerates a 0.7.0 entry byte-identical to the one produced by the earlier one-off workaround (no manifest churn), and 'python3 scripts/gen_template_manifest.py --check' now exits 0. The CI manifest-freshness gate (.github/workflows/test.yml) is green again.
<!-- sq:discussion:end -->
