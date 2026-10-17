---
summary: 'An identity check against a default-built fixture cannot fail: mutate the
  hand-off'
created_at: '2026-10-11T20:57:34Z'
---
A test asserting "the consumer was handed the resolved value" proves nothing when its fixture
resolves to the default: both sides of the identity are the same singleton, whoever fetched it.

Seen on REV-995. The test built `Service(paths)` on a squad with no override and asserted
`ctx.spec is svc.spec` and `ctx.playbook is svc.playbook`. Both are the bundled singletons, so
the assertions held when the context was built from a direct `bundled_spec()` call, and
handing every migration runner the bundled playbook left the whole suite green while changing
a generated file for a squad with a playbook override.

How to apply it on any "one resolution, handed to everyone" change:

1. Check the fixture produces a value distinguishable from the default (an override on disk,
   a service opened under it). If it does not, the identity check is decoration.
2. Mutate the hand-off to pass the default and run the suite, not only the new tests. Each
   carried value needs its own mutation: the spec half was pinned by fifty table rows, the
   playbook half by nothing.
3. Find one output byte the value controls and name it in the finding, so the fix has
   something to assert. A row called "with a playbook override" that only reads back what the
   workflow override decides is not that.