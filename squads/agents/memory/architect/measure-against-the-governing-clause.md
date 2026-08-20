---
summary: Measure a mechanism against the clause that governs it, not the one it neighbours
created_at: '2026-08-06T20:46:55Z'
---
A mechanism gets measured against the clause it sits *next to* in the code, not the clause that
actually governs it. REV-736 F42 tested an absent-timestamp exclusion against ADR-663 §1's
"exempt from the ordering rule" list, because the constant it neighbours in `_itemfile.py`
implements that list. The governing clause was three paragraphs further down, in the guard's own
design, and it already required exactly that registration and named the failure that follows from
skipping it ("otherwise it becomes a false refusal").

Two habits from it:

- When asked whether something is inside a decision, **re-derive which clause owns the question**
  before answering it. Code adjacency is not clause membership, and a wrong baseline turns a
  compliant mechanism into an apparent widening (or the reverse).
- When a decision's clause **predicts a failure mode**, and that failure mode then happens, the
  clause was not silent — it was unenforced. That is a clarification to write down, not an
  amendment to negotiate. Say so plainly rather than granting a new exemption that lets the next
  contributor argue from the wider baseline.