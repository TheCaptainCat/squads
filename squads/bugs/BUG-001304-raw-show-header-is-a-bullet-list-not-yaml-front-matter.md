---
id: BUG-1304
sequence_id: 1304
type: bug
title: Raw show header is a bullet list, not YAML front-matter
status: Cancelled
author: qa
refs:
- FEAT-1290
created_at: '2026-11-05T01:43:46Z'
updated_at: '2026-11-05T01:50:08Z'
priority: low
severity: low
---
<!-- sq:body -->
FEAT-1290's acceptance criteria and US7 say `show --raw` prints plain markdown "under a YAML front-matter header" holding "the item's frontmatter ... without the sub-entities". The build prints a markdown bullet list (`- **label:** value`), which is what ADR-1294 section 3 specifies ("one `- **<label>:** <value>` bullet per row"). The two texts disagree; the build follows the ADR.

## Steps to Reproduce

```
sq task 11 show --raw
```

Output starts `# TASK-11 - Marker task one`, a blank line, then `- **type:** task`, `- **status:** Draft`, ... No `---` delimited YAML block.

## Expected vs Actual

- **Expected (feature text):** a `---` delimited YAML front-matter block.
- **Actual (ADR-1294):** a bullet list of the panel rows.

Decision needed: amend the feature and US7 wording to the bullet header, or change the output. Nothing in the pointers depends on the header (they use `--no-header`).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-05T01:50:08Z] `manager` Catherine Manager:
  - The build follows op-pierre's later ruling on ADR-1294 (panel rows as a bullet list); FEAT-1290 and US7 were aligned to it in c67c348e. Nothing left to change.
<!-- sq:discussion:end -->
