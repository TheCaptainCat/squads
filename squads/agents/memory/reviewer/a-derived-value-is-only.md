---
summary: A derived value is only right while an unenforced assumption holds
created_at: '2026-09-08T13:45:12Z'
---
A fix that *derives* a value it could have *passed* is only correct while an unstated constraint
holds — so find the constraint and check that something enforces it.

The instance: an absolute-path leak into generated text was fixed by recovering the configured
folder name with `Path.name` instead of threading the configured string through. That is exactly
right for `squad_dir = "squads"` and silently wrong for `squad_dir = "docs/squad"`, which
`sq init --squad-dir` accepts because the config field is a bare non-empty string with no
single-segment validator. The fix's own docstring asserted the constraint as if it were a
property. Twenty-one rendered outputs matched a byte-exact baseline; the residual only showed up
by asking "what is this derivation assuming, and who enforces it?" and then driving that shape.

How to apply it: whenever a fix replaces "pass the real value" with "reconstruct it from
something nearby", write down the equality it needs (`Path(root/cfg).name == cfg`), then grep for
the validator that guarantees it. No validator means the defect is narrowed, not closed — and the
pinning test the fix added should cover the shape that breaks the derivation, not only the
default.