---
id: FEAT-1108
sequence_id: 1108
type: feature
title: 'View transforms: structured data for views'
status: Draft
parent: EPIC-897
author: product-owner
priority: high
refs:
- MILE-1051:targets
- REV-1099:addresses
description: A view may declare a transform that feeds both its template and show
  --json.
subentities:
- local_id: US1
  title: Declare and run a transform for a view
  status: Todo
- local_id: US2
  title: Resolve override transforms safely from the client's squad
  status: Todo
- local_id: US3
  title: 'show --json: stored body plus a views key'
  status: Todo
- local_id: US4
  title: Milestone roll-up transform matches its text
  status: Todo
- local_id: US5
  title: Document transforms and their trust model
  status: Todo
created_at: '2026-10-24T13:01:42Z'
updated_at: '2026-10-24T13:04:06Z'
---
<!-- sq:body -->
## Problem

A view is a declared source plus a Jinja template. `show --json` returns the body with every placed view already rendered to text, so a JSON consumer gets prose where it should get data, and cannot tell stored text from computed text. Feeding that body back to a write verb freezes the rendered roll-up into the body next to the live tag, so a milestone shows its roll-up twice (REV-1099 F5). The only structured shape a view has today is the source's raw result (items, sub-entities), which the template shapes with Jinja. That shaping is invisible to JSON.

## Scope

- A view declared in the workflow spec may declare a transform. In a bundled spec it is `transform = { module, function }`, a normal import. In an override it is `transform = { path, function }`, with `path` relative to `.overrides/` and confined to it.
- The transform is called as `fn(source, *, item, spec)` and is read-only. It may omit keyword arguments it does not need; sq passes only the ones it declares.
- It returns a structured object or list. That value feeds both the Jinja template context and the JSON output, so the text and the data come from one computation.
- It is loaded at render time only: nothing is imported at spec load, and a view without a transform behaves exactly as today.
- `show --json`: `body` returns the stored text with its raw view tags. A new `views` key carries, for each placed view that declares a transform, that view's data. Text renderings (`show`, `--full`, `--raw`) keep rendering views.
- Path resolution starts from the squad directory found from the client's working directory (what `-C` sets), never the process cwd. This holds under the 0.17 daemon (ADR-1052), whose server cwd is not the client's.
- The bundled `milestone_rollup` view gets a transform producing its delivered / outstanding / settled partition, so its JSON matches its text.
- Consumers of `show --json` `body` (the VS Code client's adapter, the TUI reader) are checked and adjusted so a body that now carries raw tags still previews as rendered text.
- User transforms are trusted and documented, like a `conftest.py`. There is no approval gate. The documentation says so plainly.

## Out of scope

- Any approval, signing or sandbox mechanism for user transforms.
- Transforms that write, or that mutate the item, the spec or the index.
- Transforms for views placed by `sq workflow view` outside a body, beyond what that verb already does with a view's source.
- New bundled views, or transforms for bundled views other than `milestone_rollup`.
- The milestone body round-trip fix itself (REV-1099 F5): it is built on top of this feature.

## Acceptance criteria

1. A view with a bundled transform renders its template from the transform's return value, and `show --json` carries the same value under `views.<name>`.
2. A view declaring no transform renders as before and is absent from `views`.
3. `show --json` `body` contains the stored text with raw `sq:view:` tags and no rendered view output. `show`, `show --full` and `show --raw` still print the rendered view.
4. Feeding `show --json` `body` back through a body write leaves exactly one roll-up on a milestone (round trip is stable).
5. A milestone's `views.milestone_rollup` holds the delivered, outstanding and settled partition, and its counts and members equal the text sections.
6. An override transform declared with `path` and `function` runs when the view renders. A function that declares only some of `source`, `item`, `spec` is called with just those.
7. A `path` that escapes `.overrides/` (`..`, an absolute path, a symlink out) is refused with a clear error naming the view and the path; nothing outside `.overrides/` is imported.
8. Run from a subdirectory of the project, an override transform is found and runs.
9. With `-C <project>` from an unrelated working directory, the same transform is found and runs; a same-named file relative to the process cwd is never picked up.
10. Under the daemon, with the server started in a different directory from the client, criteria 6, 8 and 9 hold for each client.
11. A missing file, a missing function, an import error, a raised exception or a return value that is not JSON-serializable is reported as a `SquadsError` naming the view, never a traceback.
12. `sq check` reports a declared transform that cannot be resolved; spec load itself does not import it.
13. The VS Code client and the TUI still show rendered views in item previews.
14. The authoring documentation describes the `transform` key, the signature, the trust model and the path rule, and says that override code runs with the user's permissions.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1108 add-story "As a <role>, I want … so that …"`; track with `sq feature 1108 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Declare and run a transform for a view

<!-- sq:story:US1:body -->
As a spec author, I declare a transform on a view (module and function in a bundled spec, path and function in an override) and its return value feeds the template, so presentation logic lives in code I can test. Calls pass only the keyword arguments the function declares; load happens at render time only; failures are SquadsErrors naming the view.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Resolve override transforms safely from the client's squad

<!-- sq:story:US2:body -->
As an adopter, my override transform path is relative to .overrides/ of the squad found from the client's working directory (-C, a subdirectory, or a daemon client), never the process cwd. Paths that escape .overrides/ by .., absolute path or symlink are refused with an error naming the view.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — show --json: stored body plus a views key

<!-- sq:story:US3:body -->
As a tool author, show --json returns the stored body with raw view tags and a views key holding the data of each placed view that declares a transform. Text renderings keep rendering views. The VS Code adapter and the TUI reader keep previewing rendered views.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Milestone roll-up transform matches its text

<!-- sq:story:US4:body -->
As a milestone reader, the bundled milestone_rollup view has a transform producing the delivered, outstanding and settled partition; the template renders from it and views.milestone_rollup carries the same partition, so JSON and text agree.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Document transforms and their trust model

<!-- sq:story:US5:body -->
As an adopter, the authoring docs describe the transform key, the call signature, the path rule and that override code is trusted and runs with my permissions, like a conftest.py, with a worked example in the override scaffold.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
