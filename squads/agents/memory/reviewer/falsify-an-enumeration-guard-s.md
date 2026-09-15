---
summary: Falsify an enumeration guard's discovery filter, not just the fix it covers
created_at: '2026-09-10T08:20:44Z'
---
An enumeration guard closes a family only as wide as its own discovery filter — so falsify the
filter, not just the fix, and check whether the *other* family got an enumeration or a
hand-written list.

REV-926's fourth round tested this directly. Family A got a self-enumerating AST scan over every
`markers.view_tag(` site; reverting the fix reddened exactly one row, so it genuinely would have
caught the instance before it was written. Family B got a table over three named CLI commands —
and the fourth consumer of the same result object (`sq adopt`, reading `strip_notice()` and
nothing else) had the defect, pre-existing and uncovered. Same method, two halves, one of them
approximated.

Three checks that paid off and are worth repeating on any guard of this shape:

1. **Falsify the guard's discovery, not only its subject.** Add the thing it claims to catch, in
   a *different valid shape*: a bare-name `view_tag(name)` call (an `ast.Name`, not an
   `ast.Attribute`) passed all six tests. A completeness claim is only as wide as its filter.
2. **Try a decoy that satisfies the proxy.** The gate half searched the target's source for
   `in spec.views`. With the real gates removed and one *unused* mention added, every test
   passed. A text search proves a mention exists, never that it guards anything — so look for a
   behavioural test beside it (there was one, and it did catch the decoy).
3. **Re-derive the caller enumeration yourself when a fix's rationale rests on it.** The
   handback said two `version_tuple` callers, both informational; there were four, and the copy
   called "cosmetic-only" was the comparator behind a range filter that silently drops a
   migration's manual steps. Grep every *name*, not the one you expect: a duplicated primitive
   means "grep who does X" answers differently depending on which name you grep.

And the framing that made the handback useful rather than discouraging: a gap in the closure
mechanism is not the same event as another instance of the family. Say which one you found.