---
summary: A decision's invariant and its proposed mechanism are ruled on separately
created_at: '2026-08-15T14:20:21Z'
---
Two decisions this session hinged on the same move: a decision names a mechanism, the mechanism turns
out not to produce the result the same decision states, and the right ruling is that the *headline*
survives and the mechanism is withdrawn.

ADR-163 §2 said "derived from the playbook, never duplicated" and then offered two mechanisms — a
prose scan of guide `do` bullets, and a declarative map co-located with the playbook. The scan could
not yield a lane §2's own bullet list asserts (`tech-writer` authors `guide`; that guide carries no
create verb in any bullet). The map was a second artifact held in agreement by a test, and being a
literal table it could only describe the bundled document. Both failed the headline; a declared flag
on the playbook's own guides met it by construction.

- **Separate a decision's invariant from its proposed mechanism, and rule on them independently.**
  A developer who breaks the mechanism to satisfy the invariant is complying, not departing. Say so
  in those words — it changes how the next one reads a decision.
- **Test a named derivation against the decision's own stated result before defending it.** Both
  times, the fastest disproof was to take the ADR's own expected table and run its own rule over the
  real document. A mechanism that cannot reproduce the result stated four bullets above it was
  broken on the day it was written, not degraded later.
- **Hosting rule for a new key:** the decision that owns the key's *meaning* hosts it; the decision
  that owns the *key space* gets a declared extension in the host's body plus reciprocal `related`
  refs. A separate ADR for one additive key orphans the meaning to buy a record you can get with an
  edge.
- When ruling on a departure, also read the **neighbouring clauses for the same defect**. §5 had the
  identical bundled-literal-for-a-declaration problem and nobody flagged it; amending only the
  clause raised would have left the ADR describing a mechanism we had just stopped building.