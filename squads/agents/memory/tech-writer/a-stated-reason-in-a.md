---
summary: A stated reason in a docstring is the thing that rots, and it rots outward
created_at: '2026-09-02T13:45:32Z'
---
Three false justifications shipped this release, and each had been copied out of a
docstring into adopter text before anyone checked it: "a removed region reads as 'no
item for this slug'" (two docstrings, then the release note) and "a marker written in
prose is not matched" (one docstring, then CLAUDE.md, then an ADR amendment).

The pattern: a *reason* is never linted, never tested and never rendered, so it is the
one sentence in a file that no gate touches. It then gets quoted by the next writer as
established fact, because it sits next to correct code.

Rules I now work by:

- When correcting a false claim, grep the whole tree for the sentence, not just the
  file you were sent to. Both of these had spread to two or three files.
- Drive the probe with a CONTROL, not just the failing case. "Backticks are not
  matched" only falls apart once you also check that the bare tag matches identically —
  one probe alone looks like a confirmation.
- If the honest answer is "this is a choice with no load-bearing reason", write that.
  Emptying rather than deleting a role's body region turned out to have no observable
  consequence at all (show/check/sync/repair/regen/list/--json/search are identical with
  the marker pair deleted), and saying so is more useful than a plausible invention.
- Where a real mechanism exists, name it precisely and count it rather than repeating a
  number: `reject_markers` is the guard, at ten call sites I listed, and it is a
  stronger guarantee than the false reason it replaced.
- Say why the distinction matters where it diverges. "A quoted tag is safe" and "a guard
  refused it at the door" agree everywhere the guard runs and part company exactly on an
  adopted corpus. That sentence is what stops the next widening.