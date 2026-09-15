---
summary: Template manifest gotcha is automated by bump_version.py
created_at: '2026-09-04T10:17:19Z'
---
Dev-time regens of scripts/gen_template_manifest.py corrupt the LAST release's manifest entry
(keyed by [project].version) if run while pyproject still names the shipped version.
scripts/bump_version.py's step 5 already does the fix (checkout the prior tag's manifest entry,
THEN regen, after the bump) -- use it directly, don't hand-roll the checkout.

Verify after: every version key except the new one must be byte-identical (diff before/after
JSON, or confirm the git diff on templates_manifest.json is purely additive lines).

seed_content_store.py --rebuild is a separate step for content-store orphans/drift and is
normally reserved for right before tagging, not every dev-time bump -- a correct-order bump
does not by itself orphan any blob (both the old and new version's entries stay referenced).