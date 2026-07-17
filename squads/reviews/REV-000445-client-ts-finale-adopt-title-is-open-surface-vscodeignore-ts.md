---
id: REV-445
sequence_id: 445
type: review
title: 'Client TS finale: adopt title/is_open surface + .vscodeignore + TS 6.0.3 bump'
status: Approved
author: reviewer
refs:
- TASK-440:addresses
- TASK-444:addresses
created_at: '2026-07-17T08:36:13Z'
updated_at: '2026-07-17T08:38:54Z'
---
<!-- sq:body -->
Round-4 review of the final clients/vscode changes: TASK-440 (adopt the enriched title/is_open surface, drop the multi-fetch workarounds, add .vscodeignore) and TASK-444 (TypeScript 5.9.3->6.0.3 + @types/node 22->26). Scope: clients/vscode/** only (git diff -- clients/vscode); src/squads and .github ignored as separate committed work.

Gate run by the reviewer: npm run check clean (tsc strict + eslint --max-warnings 0 + prettier), npm test 66/66 green — on TypeScript 6.0.3.

VERDICT BY TASK:
- TASK-440 (adoption): APPROVE, no findings.
- TASK-444 (TS6 bump): APPROVE, no findings. Strict gate independently confirmed intact (details below).

=== TASK-444: STRICT GATE INTACT ON TS 6.0.3 (independent check) ===
- package.json: typescript ^6.0.3 (NOT TS7 — correct; typescript-eslint 8.64 peer-caps <6.1.0), @types/node ^26.1.1. package-lock.json resolves typescript 6.0.3 (node_modules/typescript reports 6.0.3).
- The ONLY non-package change is one added line in eslint.config.mjs: '/// <reference types=node />' (line 1). This is a benign type-AVAILABILITY directive — it pulls in the @types/node ambient types so the config file's own import.meta.dirname type-checks under TS6/node26. It ADDS types; it suppresses nothing (no @ts-ignore, no eslint-disable, no any, no skipLibCheck toggle). NOT a relaxation.
- No strictness dropped: tsconfig.json is UNCHANGED (all strict-plus flags intact — strict + noUncheckedIndexedAccess/noImplicitReturns/noImplicitOverride/noFallthroughCasesInSwitch/noUnusedLocals/noUnusedParameters/exactOptionalPropertyTypes/isolatedModules). eslint.config.mjs still runs typescript-eslint strictTypeChecked + stylisticTypeChecked (type-aware), complexity<=12, max-params<=8; lint script still '--max-warnings 0'. No rule disabled or downgraded. TS6 produced zero new strict-type errors.

=== TASK-440: ADOPTION VERIFIED ===
- Workarounds fully removed, no dead code / orphaned tests: buildTitleLookup, getListSnapshot/ListSnapshot, and the openIds-diff classifyListItems signature are gone (grep across src/+test/ finds no references). classifyListItems is retained but rewritten to a single-arg form reading item.is_open directly — not orphaned.
- Tree labels now come from sq tree --json's title (treeMapping.mapNode: label = id + node.title, no lookup); open/closed from is_open (listView.classifyListItems: item.is_open ? open : closed). Types updated (SqTreeNode +title/+is_open, SqListItem +is_open); adapter validators (isSqTreeNode/isSqListItem) now require both, so an un-enriched payload is rejected as a parse-error.
- Single-call collapse (closes REV-438 F1): hierarchy refresh is one 'sq tree --json' spawn (titles + known types via distinctTypesInTree walking the tree); flat/grouped view is one 'sq list --all --json' spawn (is_open read from that same payload, no default-vs-all diff). Error handling + spawn-error re-probe preserved.
- Fixtures are GENUINE full captures (not hand-edited): test/fixtures/list.json items carry the exact 22-key set of live 'sq list --json' — including extra/subentities/created_session/modified_session that the client's own SqListItem interface doesn't even model — plus the new is_open; tree.json nodes carry the exact 9-key live set incl. title/is_open. Both fixtures span both is_open states (open + closed). Tests meaningfully updated to assert title-from-tree and is_open classification.
- .vscodeignore added (closes REV-443 F3): excludes src/**, test/** (fixtures carry internal IDs — now kept out of the VSIX), tsconfig/eslint/prettier/vitest config, package-lock.json, node_modules/**, *.map, *.vsix, coverage — so the VSIX ships only out/ + manifest/README/resources. Hygiene guard (test/hygiene.test.ts) green.

Prior findings this batch resolves are already closed: REV-438 F1 (Fixed, single-call collapse) and REV-443 F3 (Fixed, .vscodeignore).

Overall: APPROVE both. No findings — clean adoption, and the TS6 bump keeps the strict gate fully intact with zero warnings.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 445 add-finding "…" --severity medium`; track with `sq review 445 finding <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
