---
summary: Creating the first item of a type can wake a dormant corpus-wide validator
created_at: '2026-09-01T13:12:01Z'
---
A validator can be declared `inert while the corpus holds no item of the target type`. Creating the first instance of that type switches it on for the whole corpus at once, retroactively, on every already-settled item.

Creating the first contract took `sq check` from clean to 92 warnings — one per Done feature with no `implements` ref to a contract. Nothing regressed; a dormant rule woke up.

Before creating the first item of a new type, measure the blast radius first: read the type's `validators` entries in the workflow spec, work out which existing items would newly match, and count them. Report the number with the work rather than handing back a board that looks broken.