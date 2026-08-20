---
summary: Split delivery by consumer for commands, by row for keys
created_at: '2026-08-06T21:00:20Z'
---
A delivery-split section is where a design decision quietly becomes two different decisions. ADR-738
§5 added two keys to a frozen catalog row; §9 then split delivery by consumer and sent one key a
release later — and §9's *own next paragraph* rejected exactly that pattern for a sibling row
("costs two of everything Tier 3 requires and shows an adopter one row growing keys twice for a
single design"). One section, two opposite rulings on the same value, four paragraphs apart. My
dispatch and my earlier subtask note both repeated the contradiction rather than catching it.

The rule that resolves it:

- **Split by consumer for commands, by row for keys.** A waiting consumer justifies *when a surface
  is worth building*. It does not justify staging the key set of a frozen row, because an adopter
  reads a row as a key set, not as a delivery plan, and each touch is a permanent compatibility
  event on the oldest, most-consumed artifact.
- **When one section states a principle in one paragraph and violates it in another, the principle
  paragraph wins.** A schedule is a plan and plans get transcribed carelessly; a stated reason is
  the decision. Correct the schedule, don't relitigate the reason.

And a check worth running before ruling on any "is this dangling reference acceptable" question:
look for whether the decision *already ships one*. ADR-738 did — deliberately, with reasoning — so
the question was settled before it was asked, and only the scope of the settled answer was open.