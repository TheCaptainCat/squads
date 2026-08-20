---
summary: Backticks in a double-quoted sq -m argument silently delete text
created_at: '2026-07-31T16:15:53Z'
---
Backticks inside a double-quoted bash argument are command substitution, so writing
`sq … comment -m "… the `_specs/` package …"` silently deletes the backticked token from the
stored text (and may emit a stray shell error that is easy to read as unrelated noise). The
comment lands, `sq check` passes, and the markers are intact — the loss is invisible unless the
text is read back.

What happened: a comment describing a path correction stored as "names the bundled spec package
(, holding workflow.toml …)" — the path itself gone. Discussion is append-only, so the fix is a
follow-up correcting bullet, not an edit.

The habit: for any `-m` text, either single-quote the whole argument, or drop the backticks and
name identifiers plainly. Prefer `--file` for anything long. And read the stored text back
(`grep` the `.md`) after writing a comment that contained any shell metacharacter — the same
verify-after-write reflex the stray-`</content>` lesson already demands for `--file` bodies.