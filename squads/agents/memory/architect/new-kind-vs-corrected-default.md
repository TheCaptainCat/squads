---
summary: A new grammar value is warranted when a new resolver is needed, not when
  the same resolver needs a corrected default
created_at: '2026-09-04T13:00:10Z'
---
Two rulings on the view source grammar turned on the same pair of tests, and both are reusable
whenever a declared mechanism is asked to cover one more case.

**A new `kind` is warranted when a new *resolver* is needed — never when the same resolver needs a
corrected subject.** The per-item-type skill did not fit `playbook`'s tabled answers ("`name`, or
the host's own type"), and the obvious move was a seventh `source.kind`. But its resolved value, its
applicability predicate, its `--json` payload and its template contract were all `playbook`'s; only
the derivation of *which type* differed. A row that copies another row in every column but its
default is not a new source — it is the same source with a wrong default, and shipping it as a kind
buys two resolvers/predicates/payload arms to hold in agreement forever. The test came from the
decision's own definition of the key ("`kind` means which resolver"), which is where to look first:
the grammar usually already says what warrants a new value.

Corollary worth carrying: before proposing a new value, check whether an existing one already
derives its subject from the **host's identity** rather than from the declaration. `role` did
(`resolve_role_for_item` reads the item's slug; `item.type` is only its precondition), which made
the new case the second instance of a shipped, reviewed shape instead of a novelty.

**A declaration *name* that embeds vocabulary puts that vocabulary into corpus bytes.** The rejected
alternative was one synthesized view per declared type. The cheap arguments against it were the
usual ones (declaring what is derivable; a template-name indirection). The decisive one was
different and would generalise to any name-keyed artifact: a tag naming `<type>`-derived view names
dangles on every document carrying it the moment a type is renamed or deselected, and a dangling
name is an error-level finding — so an adopter's ordinary customisation produces corpus-wide errors
from a declaration they never wrote. One shared name never dangles: the type goes, the render goes
empty, the scan stays clean. Ask of any name that will be written into a corpus: what happens to
these bytes when the vocabulary they quote is renamed?

And a smaller one: when ruling that a derivation may read the host item, check what the host's
*identity field* can be for hosts you did not have in mind. `Item.slug` is the filename slug segment
for every item, so a slug-keyed derivation left ungated would resolve another type's data for a work
item whose title happened to slugify into the reserved shape. Gate on the type, not on care.