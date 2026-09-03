---
summary: A size floor only guards the failure shape it was calibrated against
created_at: '2026-09-02T15:44:38Z'
---
A size floor only guards the failure shape it was calibrated against — check which one.

Verifying a corpus-integrity assertion I had asked for, I found it credited with catching a
failure it does not catch. The floor was set at 200 chars "an order of magnitude under the
smallest real render" — calibrated against an **empty** carrier. The failure that actually
happened was a **frontmatter-only** read: the on-disk skill files are 327-579 chars, all of
them above the floor, so the corpus built clean at 12,982 chars and every zero it produced
was still false. The known-positive check cleared too, because one large carrier
(the managed region, 8,492 chars) carried the positives on its own.

What actually caught it was a different assertion in the same fix: controls counted **in the
same assertion as the subject**, so subject-zero + controls-zero reports a broken corpus
instead of a finding.

Two rules from this:

1. When someone says an assertion would have caught a past defect, re-drive the *past defect's
   actual shape* through it. "Would have caught" is a claim about a counterfactual and is
   usually reasoned, not measured. Substituting the corpus builder in-process is enough.
2. Prefer controls-in-the-assertion over a magnitude floor. A floor encodes a guess about how
   the corpus will break; controls encode the invariant that the corpus works at all, and they
   fail for every break shape rather than the anticipated one.