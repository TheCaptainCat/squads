---
summary: Two more ways an exit code lies
created_at: '2026-09-02T14:29:48Z'
---
Two ways an exit code lies, beyond the pipe trap we already brief.

**1. A command substitution in the same `echo` overwrites `$?`.**

```bash
grep -q PAT "$f"; echo "$(basename "$f") exit=$?"   # reports basename's status (0), not grep's
```

Bash expands the `echo` word left to right, so `$(basename …)` runs before `$?` is expanded. This
inverted a real result: six clean files read as six matches. Inverted is worse than lost — it
manufactures findings. Capture the status on the very next line, before any substitution:

```bash
grep -q PAT "$f"; rc=$?
name=$(basename "$f")
echo "$name exit=$rc"
```

Rule: `$?` is valid only until the next command runs, and a substitution inside the argument you
are printing counts as the next command.

**2. A validated matcher over an under-sized corpus still yields false zeros.**

Validating the pattern against a known positive is necessary and not sufficient. Building a corpus
from the on-disk `squads/agents/skills/*.md` files gave 0 for six commands while `create` still
hit — the bodies are empty stubs because a skill definition renders at read time. The
known-positive check passed and the zeros were false anyway. Assert the corpus's size too (each
render non-trivial, the extracted region non-empty) before letting any absence stand.