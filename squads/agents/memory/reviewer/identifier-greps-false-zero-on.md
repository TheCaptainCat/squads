---
summary: Identifier greps false-zero on line-wrapped docstrings
created_at: '2026-09-08T13:28:26Z'
---
A docstring can wrap an identifier mid-token, so an identifier grep silently misses it and the sweep reports a clean zero.

Found in REV-925: `effective_validator_names`' docstring still asserted the retired rule over
``PARAMETERIZED_VALIDATOR_ / NAMES`` — the name split across a line break inside the double-backtick
span. `grep -rn PARAMETERIZED_VALIDATOR_NAMES src/` returned four hits and this was not one of them,
so both the dev's sweep and my own first pass called the criterion clean. It only surfaced from
reading the prose of every function that shares the changed concept.

So when a finding is "a comment/docstring claims X", the verification is reading the docstrings of
every function in the concept's neighbourhood, not grepping the identifier. If a grep must carry the
claim, also grep the token halves (`VALIDATOR_$`, `` ``[A-Z_]*_$ ``) to catch wraps, and validate the
pattern against a known positive first.