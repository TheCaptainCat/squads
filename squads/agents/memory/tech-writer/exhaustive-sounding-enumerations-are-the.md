---
summary: Exhaustive-sounding enumerations are the rot point — drive the CLI, don't
  trust the list
created_at: '2026-08-03T08:40:19Z'
---
Sentences of the shape "the frozen surface is X, Y, Z", "commands that stay
table-only: …", "the closed vocabulary: …" or "the frozen field set:" are the
highest-risk lines in a contract doc. They read as exhaustive, so an adopter
builds against the gap — and they rot silently every time a feature adds one
more member.

Rule: never carry such a list forward on trust, even when the surrounding prose
is correct. Drive the live CLI (`--help` on the group, then each subcommand) or
grep the emit sites, and reconcile the doc against what the tool actually does.

Watch out for the code's own hand-maintained lists: they can be stale too, and
two of them can disagree with each other and with reality. Docstrings and
`--help` strings are not evidence — the emit/registration sites are.

When a list genuinely cannot be made complete from the code, say what IS
knowable and where to read the rest, rather than promising a join that does not
exist.