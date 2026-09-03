---
summary: 'A check whose remedy does not exist yet is noise: gate it on its premise,
  never suppress per item'
created_at: '2026-08-26T13:52:10Z'
---
ADR-320's currency check would have fired on 90 Done features on day one, in a repo where a clean
`sq check` is a must-pass gate — because the collection the finding points at did not exist yet.
The task forbade a suppression or grandfather clause, correctly: every one of those is a place a
team learns to put things.

The move that resolves the tension without one is to gate the check on **its own premise**, not on
a class of items. "Inert while the corpus holds no item of the parameterised target type" names no
date, no item, nothing storable, and cannot be cleared with a fake ref; the day the collection is
seeded, every settled item is evaluated, the pre-existing ones included. It is the shape
`supersedes_incoming` already has (it runs only for a type that declares a supersession rule),
moved one step from declaration to corpus state.

Test to reuse: **is the finding's remedy available?** A finding whose remedy does not exist yet is
noise by construction, and noise is what teaches people to stop reading warnings. Distinguish it
from a suppression by asking whether the condition is per-item (suppression) or per-premise
(precondition), and state the cost — behaviour that varies with corpus state surprises the first
time one item turns on a batch of findings.