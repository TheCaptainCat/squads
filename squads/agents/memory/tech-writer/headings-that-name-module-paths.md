---
summary: Headings that name module paths rot; keep the path in the body
created_at: '2026-08-03T13:16:51Z'
---
A doc heading that carries implementation paths — `## 8. Roles and the playbook
(_roles/_catalog.py, _interactions.py)` — rots twice: the paths go stale when the
code moves, AND every inbound anchor link is pinned to the stale spelling, so
fixing it is always a two-file edit that a single-file pass will miss.

Rule: keep headings path-free and put the module paths in the body's first line.
The anchor then stays stable across refactors, and correcting a path is a
one-file edit.

When you inherit a path-bearing heading: grep the whole docs tree (plus README
and PYPI) for the old anchor before changing it, fix every inbound link in the
same pass, and re-grep to confirm none survives. Verify each path you write at
the source — a package that became a directory (`_interactions.py` →
`_interactions/`) and data that moved (`_specs/playbook.toml`) both read as
plausible in prose long after they stopped being true.