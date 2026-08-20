---
summary: sq <type> <n> body -m REPLACES the body — never probe with it
created_at: '2026-08-06T21:34:53Z'
---
`sq <type> <n> body -m "…"` (and the sub-entity / skill / role variants) overwrite
the entire body region. There is no confirmation and no dry-run. Running one as a
capability probe — "does this verb work on this item?" — silently destroys
everything that was there.

Rules:
- Never use `body` to test whether a verb is permitted. Use `--help`, or read the
  item's `kind:` / metadata, which says whether it is bundled or custom.
- To change part of a body: read the current text first (extract between the
  `<!-- sq:body -->` markers, or `show`), edit that text, write it back with
  `--file`. Use `--append` when you are only adding at the end.
- If you do clobber one and the file is committed, `git checkout -- <path>`
  restores it — then expect `sq` to refuse the next write with "on-disk
  frontmatter has diverged from the index (updated_at)". `sq repair` clears it.
  Note that repair also renormalises item order in `.squads.json`, so the index
  diff can balloon to the whole file for one real change; verify semantically
  (parse both sides and compare) before reporting it as damage.