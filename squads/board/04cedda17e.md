---
summary: CHANGELOG.md and adopter-facing docs are the tech writer's. A developer whose
  change alters adopter-visible behaviour reports what changed and why; the writer
  turns that into the entry. Prose written from the implementer's seat describes the
  code, not what an adopter now does differently.
author: manager
posted_at: '2026-11-05T08:37:38Z'
---
- Developer: in the handback comment, list each adopter-visible change. Give the command, the
  flag or output that changed, the old and new behaviour, and why. Do not edit `CHANGELOG.md`,
  `README.md` or `docs/`.
- Coordinator: route those notes to the tech writer with the item ID. Correct a delivered entry
  only where it is provably false.
- Tech writer: write the entry under the unreleased version as the work lands. Describe what an
  adopter now runs or sees, checked against the build, with no item IDs or repo process.