---
summary: Windows-only CI failures come from POSIX and UTF-8 assumptions in tests,
  not from the product
created_at: '2026-08-20T14:18:59Z'
---
Three concrete traps, all found in one Windows-only CI failure of 24 tests:

**Rich width.** `Console.__init__` latches its width as `COLUMNS - legacy_windows`,
and `legacy_windows` is true whenever Rich cannot read console features off the
handle it writes to — precisely a captured pipe on Windows, so every CliRunner and
subprocess capture there. `COLUMNS=80` therefore renders at 79, a message long
enough to reflow wraps one word earlier, and a literal the test looks for straddles
the inserted newline. Emulate it locally: `Console(legacy_windows=True)` — passing
the flag to the *constructor*, because the subtraction happens once at construction
and flipping the attribute on a live console changes nothing (a falsification that
does that is silently vacuous).

**chmod cannot express "unreadable" on Windows.** `os.chmod` there only toggles the
read-only attribute; `chmod(0o000)` leaves the file perfectly readable, so a
degradation fixture built on it stages nothing and the assertions read a healthy
corpus. The read-only bit it *does* set makes the file an illegal `os.replace`
target, so a whole-corpus rewrite fails with a write error instead. Portable
instrument: replace the file with a directory of the same name — opening a directory
raises `IsADirectoryError` on POSIX and `PermissionError` on Windows, both `OSError`,
both landing in the same read guard, and `Path.glob` still matches the name.

**`subprocess.run(text=True)` decodes with the locale codepage.** On Windows that is
cp1252, so capturing UTF-8 output (which `sq` always emits — `_cli/__init__` forces
it) raises `UnicodeDecodeError` inside the reader thread. Always pass
`encoding="utf-8"` explicitly.

Corollary for reading the CI log itself: a mangled non-ASCII character in a GitHub
Actions log is usually the log pipeline, not the product. pytest's own stdout is not
UTF-8-forced, so it writes cp1252 bytes that GitHub's UTF-8 ingest replaces with
U+FFFD. Check the raw log bytes before believing the product emitted a `?`.