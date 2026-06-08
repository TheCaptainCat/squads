# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-06-08

### Fixed

- **Windows: every write command crashed** (`sq init`, `create`, `status`, `repair`, …). The atomic
  index write called `os.fsync()` on a read-only file handle, which Windows rejects with
  `OSError [Errno 9]`; it now fsyncs the write handle that produced the bytes.
- **Windows: non-ASCII output crashed** under the legacy cp1252 console (`UnicodeEncodeError` on
  `→`/`•`/`—`, e.g. from `sq workflow`). The CLI now forces UTF-8 stdio on Windows.
- **Windows: reading squad files crashed or silently corrupted non-ASCII content.** `sq check`
  (and any read path) used `Path.read_text()` with no encoding, so on a non-UTF-8 locale (e.g.
  cp1252) a heading such as `### ST1 — … (→ US1)` either raised `UnicodeDecodeError` or decoded the
  `→` to mojibake — breaking subtask/story validation. All file I/O is now pinned to
  `encoding="utf-8"`. The CI test matrix now runs the suite on Windows and macOS as well as Linux,
  so this class of bug is caught before release.

## [0.1.0] - 2026-06-08

Initial release.

### Added

- **CLI** (`squads` / `sq`) for managing a team of AI agents as identified markdown with a
  JIRA-like, globally-unique ID system. Item types: epic, feature, task, bug, decision (ADR),
  review, guide, role, skill.
- **Index** — a single `<squad>/.squads.json` with one global monotonic counter and all item
  metadata; filelock'd, atomic writes. The `.md` frontmatter is the durable source of truth; the
  index is rebuildable (`sq repair`, `sq repair --renumber`).
- **Commands** — `init`, `adopt`, `create`, `list`, `show`, `tree`, `link`/`unlink`, `update`,
  `status`, `comment`, `story`, `subtask`, `ref`/`refs`, `inbox`, `role`, `dev`, `skill`, `guide`,
  `check`, `repair`, `sync`, `workflow`. Global `--dir` (target a squad) and `--at` (forge
  timestamps for history-preserving migration).
- **Workflow** — per-type status machines with validated transitions; parent rules
  (task → feature, feature → epic); typed forward refs with computed backrefs; user stories &
  subtasks with their own discussion; `@mention` inbox.
- **Claude Code backend** — thin `.claude/` pointers to real definitions under the squad folder,
  bundled `squads` skill + per-item-type skills, a managed `CLAUDE.md` section with
  greeting-based impersonation, and a non-clobbering `settings.json` merge.
- **8 bundled roles** + on-demand stack developers (`sq dev add`); the role↔item-type playbook.
- **Docs** — README, plus `docs/` (workflow, internals, adoption, agents, tutorial, roles,
  backends, recipes, faq); `py.typed`; MIT licensed.

[Unreleased]: https://github.com/TheCaptainCat/squads/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/TheCaptainCat/squads/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/TheCaptainCat/squads/releases/tag/v0.1.0
