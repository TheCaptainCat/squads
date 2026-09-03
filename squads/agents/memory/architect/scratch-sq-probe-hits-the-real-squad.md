---
summary: A scratch sq probe can resolve to the real squad — read the code instead
  of driving a temp squad
created_at: '2026-09-02T13:20:06Z'
---
A scratch `sq init` in a temp dir failed (exit 1) and the very next `sq role activate qa` reported
success against the **repo's** squad, not the scratch one — nothing existed in the scratch dir
afterwards. It happened to be idempotent (an already-active role), so `git status squads/` was
clean and no harm was done, but a write-verb would have landed on the real board.

So: to answer "can an operator set this field", read the code and the CLI verb list rather than
driving a scratch squad. If a probe squad is genuinely necessary, check `sq init`'s exit code
before the next command, and check `git status squads/` immediately after.

Static evidence was sufficient in the case that prompted this — the field table, the pinned unit
test, an exhaustive grep of the key's sites, and `sq <group> --help`'s verb list together answered
it with no squad to create.