---
summary: Never put backticks in a double-quoted sq -m message
created_at: '2026-07-31T11:38:48Z'
---
A backtick-quoted command inside a double-quoted `-m` string is substituted by the shell: the
comment stores the command's *output*, and — worse — the command actually RUNS, in whatever
directory you are in. On REV-706 this executed `sq role qa status Archived` against the squads
repo itself, retiring a live role and regenerating four managed files, while I was under
instruction to mutate only throwaway squads.

Write every `-m` in single quotes, or write the body to a file with a heredoc and pass `--file`.
Heredocs quoted as `<<'BODY'` are safe; `<<BODY` is not. After any batch of comment/body commands,
run `git status --short` in the repo and confirm nothing outside the item you meant to touch moved.