---
id: BUG-000151
sequence_id: 151
type: bug
title: 'Windows CI: override path separators, template-hash CRLF, and init prompt
  abort'
status: Verified
author: manager
priority: high
refs:
- FEAT-000015
created_at: '2026-06-17T12:37:46Z'
updated_at: '2026-06-17T13:00:48Z'
---
<!-- sq:body -->
## Symptom

The PR #1 (0.3.0) `test (windows-latest)` job fails: **15 failed, 825 passed**. All failures are Windows-only and cluster in the project-overrides / template-manifest / init-naming features shipped during the road to 1.0. The Linux and macOS jobs pass. This is exactly the class of cross-platform defect the Windows matrix exists to catch, and it blocks the release merge.

## Root causes (three independent)

**1. Path separators — `\` vs `/` (~8 failures).** The override "name" is built with `str(path.relative_to(tmpl_dir))`, which uses `os.sep` → on Windows yields `items\task.md.j2` instead of the canonical `items/task.md.j2`. The manifest keys and golden JSON use `/`, so the name both renders wrong AND fails to match the manifest (a `\`-name looks "unknown", so drift/marker detection silently no-ops).
- Sites: `src/squads/_overrides/_service.py:184, 435, 466` and `scripts/gen_template_manifest.py:62`.
- Fails: test_golden_override_list, test_golden_override_diff, test_scan_overrides_stamped_current, test_scan_overrides_broken_template, test_cli_list_shows_overrides, test_cli_list_json, test_update_stamp_bulk_skips_broken, test_check_errors_on_missing_required_marker, test_check_exit3_on_missing_marker, test_cli_check_json_override_error.

**2. Template-hash CRLF (~4 failures).** Hashing reads raw bytes (`sha256(read_bytes())`), and there is no `.gitattributes`, so Windows checks out `.j2` files as CRLF → every one of the 23 template hashes mismatches the LF-generated manifest.
- Sites: `src/squads/_overrides/_manifest.py:55` (`current_template_hash`) and `scripts/gen_template_manifest.py:56` (`_hash_file`).
- Fails: test_manifest_freshness_all_bundled_templates, test_current_template_hash_matches_bundled, test_template_changed_since_false_for_same_version, test_diff_template_delta_upgrade_same_version.

**3. `sq init` prompts and aborts non-interactively on Windows (1 failure).** In the Windows subprocess, `sys.stdin.isatty()` reports a console, so the agent-naming feature prompts (`Name for 'manager'…`) and then aborts on EOF (closed/empty stdin), failing the whole `init`. On Linux the same subprocess reads as non-TTY and skips.
- Site: `src/squads/_cli/_main.py:50` (isatty) + the prompt at `:191`.
- Fails: test_at_after_subcommand_works.

## Fix direction (decided)

1. Use `Path.relative_to(...).as_posix()` for the canonical name at all four sites (it yields the `/`-joined string the manifest/JSON contract already uses; `.parts` would only force a manual re-join). Reconstruct real paths with `Path(name)` (accepts `/` on Windows).
2. Normalize newlines (`\r\n`→`\n`) before sha256 in both the runtime hasher and the generator — makes the hash EOL-agnostic on every platform. Manifest values are unchanged (generated from LF content), so NO manifest regeneration is needed. Add a `.gitattributes` (`* text=auto eol=lf`) as hygiene + to keep golden diff content LF.
3. Product fix (operator's call): make the init prompt degrade to defaults when stdin can't be read — wrap `typer.prompt` and on `typer.Abort`/`EOFError` fall back to the bundled default name instead of aborting `init`.

## Verification

Linux suite + pyright + ruff stay green locally; the objective gate is a green `test (windows-latest)` re-run on PR #1 after the fix is pushed.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-17T12:48:46Z] Elias Python:
  - Fixed: .as_posix() at all four path-to-name sites, CRLF-normalized hashing in manifest runtime and generator, .gitattributes for LF enforcement, and typer.Abort/EOFError fallback in init prompt — all 839 tests green, pyright+ruff clean, manifest unchanged.
- [2026-06-17T13:00:48Z] Catherine Manager:
  - Verified: the Windows fix landed in 8d7b3c5 and PR #1 is fully green — test (windows-latest) passed in 5m20s (run 27690459775), alongside ubuntu, macos, and lint. All three root causes (os.sep override keys, CRLF template hashing, init non-TTY-EOF prompt abort) confirmed resolved on the actual Windows runner.
<!-- sq:discussion:end -->
