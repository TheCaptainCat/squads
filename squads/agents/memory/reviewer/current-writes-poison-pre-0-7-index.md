---
summary: Current-code writes on a pre-0.7 corpus index turn every id into UNRESOLVED
created_at: '2026-10-11T20:57:35Z'
---
Creating or editing an item with the current code on a corpus stamped below 0.7 rewrites the
index with every pre-existing id as `UNRESOLVED-n` (those entries store neither `id` nor
`prefix`). With a workflow override present, the next invocation's index cross-check then
refuses with "type X prefix changed" for every type.

So a probe that carries an item into an old corpus through `svc.create` fails on the 0.5
corpus and older for its own reason, in the unchanged and the changed code alike. It looked
like forty identical refusals until the output was read. For those schemas, write the item
file and the index entry by hand in the era's shape, or use a fresh squad restamped to the old
schema and say that it is not era-shaped.

The same rewrite happens for real inside the runners' own index transactions, which is the
dead end recorded as REV-995 F5.