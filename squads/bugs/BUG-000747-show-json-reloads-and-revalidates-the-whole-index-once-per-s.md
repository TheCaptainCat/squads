---
id: BUG-747
sequence_id: 747
type: bug
title: show --json reloads and revalidates the whole index once per sub-entity
status: Verified
author: qa
description: 216 Service.get calls and 55 full index validations for one 51-sub-entity
  item; ~2.3s, scaling with sub-entity count
created_at: '2026-08-20T18:49:18Z'
updated_at: '2026-08-21T16:57:38Z'
---
<!-- sq:body -->
Reported by op-pierre from the extension dev host: some item previews take about three seconds to load. Driven and profiled.

`sq show REV-000736 --json` — a review with 51 sub-entities, 20 comments and 118 KB of sub-entity body text — takes **2285 ms**, against **992 ms** for a small item and a **576 ms** floor for `sq --version` (interpreter and imports). So roughly 1.3 s is real work, and it is the slowest of the eight calls the VS Code preview fans out in parallel, which makes it the wall-clock cost of opening that page.

cProfile, sorted by self time:

```
   ncalls  tottime  cumtime  function
       55    0.821    1.212  pydantic_core SchemaValidator.validate_json
      216    0.081    1.775  _services/_base.py:758 get
    70345    0.144    0.176  _models/_subentity.py:34 _tolerate_loose_frontmatter_spellings
       55    0.089    0.433  _index/_store.py:144 _validate_badge_codes
    39545    0.065    0.111  _models/_item.py:193 _derive_prefix_from_id
   109998    0.054    0.105  _models/_item.py:245 id (computed field)
   109890    0.054    0.176  _index/_store.py:101 _check_field_codes
```

`Service.get()` is called **216 times** for one item, and the index is fully deserialised and revalidated **55 times** — 715 items each pass. That is an N+1 over the sub-entities: something in the show path resolves per sub-entity through `get`, and every `get` pays a whole index load. The 110k `Item.id` and `_check_field_codes` calls are that multiplication.

**Not a regression.** Driven on a d0ca7b5 (0.12.3) worktree against a copy of this same corpus: 2258 / 2272 / 2319 ms across three runs, against 2285 ms on 0.13. The cost is pre-existing and this release neither introduced nor worsened it. Filed for that reason as 0.14 work rather than a release blocker.

Not the hover directory either: `sq list --all --json` is 708 ms and runs inside the same `Promise.all`, so it adds no wall time. The eight preview calls together take 899 ms when none of them is the slow one.

The shape of the fix is a request-scoped index read — one load per command invocation, reused by every `get` — rather than optimising any single validator. Worth checking at the same time whether `_validate_badge_codes` and `_check_field_codes` need to run on every load or only when the spec or corpus changed.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-20T18:49:46Z] Catherine Manager:
  - Measured after op-pierre reported three-second previews. Recording that my first three attempts to establish whether this was a 0.13 regression were all broken probes -- a removed worktree, a --dir that resolved to a missing index and exited fast, and a cp that nested the corpus inside the worktrees own squads directory. I reported a 3x regression off the second one before checking it. The fourth probe is the one the numbers above come from.
- [2026-08-21T12:35:55Z] Pierre Chat:
  - In scope for 0.14.0: op-pierre pulled all five open bugs into the next release, overriding the earlier per-bug deferral to a later cycle.
- [2026-08-21T12:51:26Z] Robert Architect:
  - Design settled on ADR-753 (Proposed): one index load per invocation via an explicitly entered read scope; transactions always read from disk under the lock, so invariant 8 holds by construction. Driven numbers correct the ticket: 55 loads at 26.4 ms each is the 1.45 s, `get` is called 54 times not 216 (cProfile counts async resumptions), and the item-file re-reads are 10 ms and stay. The badge/vocab validators keep running every load — at one load they cost 3.3 ms.
- [2026-08-21T16:45:30Z] Catherine Manager:
  - Fix landed in 9bd3560 on release/0.14 (TASK-752). Measured independently: instrumenting IndexStore._read_from_disk gives exactly 1 disk read for sq show REV-000736 --json (was 55) and 2 for the sq review 736 show --json alias; wall time 0.92s across three runs against the 2285ms recorded here. The VS Code client invokes the canonical show id --json form, so the preview path that prompted this report is on the 1-load path.
- [2026-08-21T16:57:25Z] Mara Tester:
  - Verified by counting, not timing: instrumented IndexStore._read_from_disk in-process (CliRunner against the real app) against this repo's own index. sq show REV-000736 --json (51 sub-entities) now makes exactly 1 disk read (was reported 55); sq review 736 show --json alias form makes exactly 2 (matches the two-anyio.run-crossings note in the fix commit).
  - Wall time for the canonical form: ~137-167ms in-process across runs, well under the 2285ms recorded on the ticket.
<!-- sq:discussion:end -->
