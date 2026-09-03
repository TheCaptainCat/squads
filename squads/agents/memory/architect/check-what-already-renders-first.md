---
summary: Check what already renders the data before commissioning a successor
created_at: '2026-09-01T08:56:04Z'
---
Twice on the same decision, a clause reading "reissue this projection as a computed view" was
commissioned as build work when the computed rendering it asked for already shipped. The head, then
the roll-up. Both times the correct answer was a deletion with no successor, and both times it was
found by driving rather than by reading the clause.

The check, before commissioning any successor: **enumerate what already renders this data, and ask
what the new declaration adds for an actual reader.** Not "can the mechanism express it" — that is
an adequacy proof and it was already green in both cases. Expressing a shape is not a reason to ship
an instance of it.

Two traps this run:

- **A capability claimed for a declaration must be driven end-to-end, not inferred from the
  mechanism.** "An adopter can re-present it through `templates/views/<name>.md.j2`" was true of the
  view and false of the roll-up: the table a reader actually sees is a Rich table rendered through
  no template, so the override reached only the proof command. One scratch squad with an override
  template settled it in a minute.
- **Distinguish a capability from an obligation.** "`[selected]` can drop it" was offered as what the
  bundled declaration buys; it is the step the adopter is *forced* into to un-brick their squad. If
  the only reason to exercise a capability is damage the thing itself caused, it is not a buy.

And the shape that keeps recurring: **bundled vocabulary named by a bundled declaration couples an
adopter's ordinary customisation to a declaration they never wrote.** The load-time refusal is right
and should not be weakened — the fix is to not ship the declaration. A bundled instance earns its
place only when it is the sole rendering of its data.