---
summary: Brief the operator on an ADR's commitments and challenge its exceptions before
  acceptance
created_at: '2026-10-28T21:41:34Z'
---
Before the operator accepts an ADR, give them a short brief per decision: what 
it commits them to, what it rules out, and what will be hard to undo later. 
Never pass an architecture choice through as one line among several operator 
questions.

Why: ADR-1052's API shape (one command endpoint, the CLI's argv and output as 
the API contract) was accepted on 2026-10-25 from a one-line question. Its 
consequences (a web front building sq command lines, no resource model) surfaced
only on 2026-10-28, after TASK-1217 was built on it, and the decision was 
reversed.

Challenge every exception a design carves out before relaying it ("X stays local", "Y is out of the rule", "Z keeps the old path"): name the reason and check it against the design's own principle. On 2026-10-28 I relayed "the TUI stays on LocalApi" from the draft ADR-1224 although the Api abstraction exists so that every client selects local or HTTP; the operator had to catch it.