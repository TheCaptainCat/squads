---
summary: Never rewrite a file in one Python expression — it truncates first
created_at: '2026-09-01T13:12:02Z'
---
`open(p,"w").write(open(p).read().replace(a,b))` silently produces an EMPTY file. Python evaluates arguments left to right, so `open(p,"w")` truncates before `open(p).read()` runs.

It cost a whole probe setup and looked like a squads bug (the override "stopped loading"). Always two statements: read into a variable, then open for write.