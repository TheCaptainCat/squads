---
author: reviewer
posted_at: '2026-09-03T14:10:11Z'
---
Narration sweep, part two: reading finds the class, a post-rewrite grep closes the copies. Reading file-by-file structurally cannot see that two files make the SAME claim -- it gets fixed where the reader attention landed and missed where it did not. Evidence: three sibling test controls carried one claim; two were rewritten in the same commit, the third survived two review passes.

So: once you rewrite a sentence, grep a distinctive fragment of the OLD sentence across the whole feature before calling that claim closed. Run the grep AFTER the rewrite over the wording you just removed -- not before it over a guessed vocabulary. That is the opposite direction from the phrase-list grep that does not work.

Scope, generalised: the stranger test applies to any prose this tool or its tests EMIT OR DISPLAY to a human -- docstrings, comments, assert messages, error strings, CLI help. Not prose-shaped fixture data, which is input. An assert message earns it on its own terms: its job is to tell the person staring at a red test which invariant broke, and "must still behave exactly as before" is unresolvable for that person.

Carve-out that keeps this from over-firing: a past-tense sentence passes if the before is a state the READER can still observe -- spec drift a user causes, a corpus state they can reproduce. It fails only when the before exists nowhere but the diff.