---
summary: Make a delegated proof unforgeable, and audit what the guard says it cannot
  see
created_at: '2026-09-10T09:34:03Z'
---
A delegated proof needs the delegation to be **unforgeable**, and the guard needs to **write down
what it still cannot see**. Check both, and reproduce every drive against the real corpus, not the
fixture that shipped with the fix.

The final shape REV-926 converged on, after a hand-maintained citation dict proved gameable:

- **Invert the citation.** The proving test marks *itself* with the site it proves
  (`@pytest.mark.gate_for("path::function")`); the guard *collects* the map from markers instead of
  reading a dict. A citation then cannot exist without a test claiming the job, and re-pointing
  leaves two claimants — ambiguity the guard refuses — rather than a silent swap.
- **Require "collected and live".** Reject a cited test marked `skip`/`skipif`/`xfail` or carrying
  the repo's default-collection exclusion (`slow` here). Check it keys on *suppression*, not on
  "has a marker": drive `usefixtures` as the negative and confirm it is not excluded.
- **Declare the rest.** A marker *moved* off the true owner onto an unrelated test, and whether a
  cited test's assertions actually falsify, are both invisible to any static check. Saying so is
  the inverse of the defect — but only if the statement is true, so read it clause by clause.

Two clause-level errors to look for in that kind of self-declaration, both found here:
**overstatement** ("the marker keeps the citation attached to the driven event" — it does not; gut
the test body, keep the marker, everything stays green) and **understatement in the guard's own
favour** (a swap costs *attribution*, not *detection* — the real prover is still collected and
still fails, so a broken gate still reddens the suite).

And the disposition call worth reusing: a false claim in a comment is a finding when it is
**load-bearing** (it justifies a derivation, or sends an operator at a command that cannot help)
and a note when its substance is already disclaimed beside it and no behaviour rests on it. Say
which, and why, rather than filing on reflex — after several rounds, filing wording is the grind,
not the rigour.