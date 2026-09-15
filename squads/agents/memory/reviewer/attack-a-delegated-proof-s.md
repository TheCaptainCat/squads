---
summary: 'Attack a delegated proof''s naming: a citation can resolve and prove nothing'
created_at: '2026-09-10T09:04:36Z'
---
When a guard's proof is delegated to a *named* test, attack the naming, not the test: a citation
can resolve, look honest, and prove nothing.

REV-926 replaced a gameable source-text gate check with a citation map — each `gated` site names
the behavioural test that proves it, and the meta test checks only that the citation resolves
(file exists, top-level function of that name exists). That is a real improvement and it survived
the obvious probe: with all three gates reverted and decoy mentions added, the meta module stayed
green and all three cited tests reddened. Three ways it still fails, all driven with the gates
reverted and none needing a test body edited:

1. **Re-point the citation at a passing sibling in the same file.** The regression control the
   same commit wrote (`…_under_a_declared_view_still_seeds_the_tag`) is real, top-level, in the
   cited file, plausibly named — and passes with the gate broken, because it asserts the direction
   an ungated writer also satisfies. Guard green, nothing proved.
2. **`@pytest.mark.skip` the real cited test.** Decorators are invisible to an `ast.FunctionDef`
   name lookup, so the citation resolves and the prover never runs. This is the accidental
   version — a test goes flaky, someone skips it, a classification silently loses its backing.
   Same for `skipif`/`xfail` and for a citation into a module the default collection excludes.
3. **Relabel the site out of the class that requires a citation.** The requirement applies only
   to self-declared `gated` sites, so one label change deletes the obligation.

The generalisation: **a delegated proof needs the delegation to be unforgeable, not merely
present.** Invert the direction — mark the proving test with the site it proves and build the map
by collecting markers, so the test declares what it proves and a re-point means editing the test
into a false claim. Then add "collected and live" (not skip/xfail-marked, not excluded by
default) which is checkable without executing anything.

And say what remains rather than closing it: whether the cited assertions actually falsify is only
knowable by mutating the gate and running it. That belongs recorded once, per site, in the commit
that writes the citation — the gap is that nothing keeps the citation attached to that event.