---
summary: A gate that proves an invariant elsewhere cannot be widened by editing its
  tuple
created_at: '2026-09-15T09:01:21Z'
---
Before widening a gate, grep for code that derives an invariant **from** the gate.

`sq repair`'s docstring proves its strip-ordering prohibition "by construction", citing
`require_current_schema` by name: repair can only run at the current schema, so the sweep can
never precede a runner's surface regeneration. Adding `repair` to the exempt tuple would have
silently converted that proof into a convention, with nothing near the change failing — a cost
invisible from the gate's own source, and the deciding one.

Generalised: a guard that has only ever had one member carries no written justification for its
membership, so the first widening has to supply the admission test that was never needed. Write
the test as a property of the **operation** (what may it read, what may it write, what must it
converge toward), not as a longer list of command names — the next migration inherits a property
and cannot inherit a list.

Also: when a remedy is proposed, check it is reachable *in the state the message fires in*, not
in general. Sibling seams naming the same command can all be correct while one is false, because
only one of them is behind the hard stop.