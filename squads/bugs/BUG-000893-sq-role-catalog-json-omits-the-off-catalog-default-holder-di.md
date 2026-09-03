---
id: BUG-893
sequence_id: 893
type: bug
title: sq role catalog --json omits the off-catalog default-holder disclosure
status: Verified
author: qa
assignee: python-dev
priority: low
severity: low
refs:
- BUG-869
description: Every row reads is_default false when an off-catalog role holds it; the
  footer that discloses the holder exists only in the terminal.
created_at: '2026-09-02T14:27:33Z'
updated_at: '2026-09-02T15:43:11Z'
---
<!-- sq:body -->
## Summary

**Driven.** `sq role catalog` resolves the default-role designation for the active squad, and marks the holder in its `Default` column. A holder that has no catalog row — a developer role from `sq dev add`, the case the fix for the catalog column deliberately could not mark — is disclosed instead by a footer on the plain listing. `--json` carries no equivalent: every row comes back `"is_default": false` and nothing in the payload says a holder exists elsewhere. A machine consumer of `sq role catalog --json` reads "nobody is the default in this squad", which is false.

`sq role list --json` answers correctly in the same state, so the information is available one command away and this may not need the payload restructured. Not designing the fix — recording what was driven.

## Environment

**Driven.** `squads 0.14.0`, branch `release/0.14` at `4214813`, bundled workflow spec unless a scratch squad is noted otherwise. Three independent scratch squads, each a fresh `sq init --default-names` nested in its own temp directory, plus one non-squad directory. Every invocation was the repo's `.venv/bin/sq` — the globally installed `sq` is 0.12.1 and refuses a v0.14 squad outright. Every exit code read from a bare command, never through a pipe.

## Reproduction

**Driven.**

```
sq init --default-names
sq dev add --tech python --name "Elias Python"     # -> ROLE-21
sq role python-dev set-default                     # exit 0, cleared ROLE-1

sq role catalog          # exit 0
#   ...eight bundled rows, Default blank on every one...
#   The default role is python-dev, which this catalog does not list — run sq role list to see it.

sq role catalog --json   # exit 0
#   eight rows, "is_default": false on all eight, no other key
```

The payload's row shape is `slug / full_name / title / is_default / origin`. There is no footer field, no holder field, and no key naming `python-dev` anywhere in it.

**Driven**, with the pattern validated against a known positive before the zero was trusted:

```
grep -q "python-dev" catalog.json ; echo $?   -> 1   (absent)
grep -q "python-dev" list.json    ; echo $?   -> 0   (present — the pattern works)
```

`sq role list --json` in the same squad returns `is_default` true for `python-dev` and false for the other eight — one true, the correct answer.

## What the wire cannot distinguish

**Driven**, one scratch squad per state:

| squad state | `role catalog` terminal | `role catalog --json` | `role list --json` |
| --- | --- | --- | --- |
| a catalog-row role holds it (`qa`) | tick on qa | exactly one true (qa) | one true (qa) |
| a live off-catalog role holds it (`python-dev`) | no tick, footer names python-dev | **all false** | one true (python-dev) |
| the holder is archived, no live role carries it | no tick, **no footer** | **all false** | one true (python-dev), Live blank |
| outside any squad (catalog fallback) | tick on manager | one true (manager) | n/a |

Two consequences, both driven:

- Rows 2 and 3 are **identical on the wire** and different in the terminal. A consumer cannot tell "the holder is a role this listing cannot show" from "no live role holds it at all".
- Row 4 is identical on the wire to a squad in which `manager` genuinely holds the designation. Outside a squad the column falls back to the catalog document's own declaration, which is the honest answer there, but the payload does not say it is a fallback.

The third state was reached with `sq role python-dev status Archived` (exit 0), which itself warns: `ROLE-21 (python-dev) carried the default-role designation; no live role carries it now`. So the condition is one the tool already knows how to describe.

## Expected vs actual

- **Expected:** the two output modes of one command answer the same question the same way. Where the tabular mode discloses that the holder is not representable in these rows, the machine-readable mode discloses it too.
- **Actual:** the disclosure exists only in the rendering. `--json` returns a payload whose only signal is an absence — all-false — which is undocumented, and which two different squad states both produce.

## The precedent this matches

**Read.** The same shape was made an explicit, non-negotiable requirement on the cycle-anchor work: a fabricated tree root had to be marked "in the rendering **and** in `--json`", on the stated grounds that an unmarked anchor "replaces a quiet omission with a quiet fabrication". The ruling there treated a rendering-only disclosure as not a disclosure. This is the same relationship between the same two output modes on a different command.

**Read**, `sq role catalog --help` already states the limitation and points at the remedy: "a developer role (`sq dev add`) that holds the designation appears in no row and the column is correctly blank throughout. The plain listing names that holder in its footer; `sq role list` — the roster listing, which carries every live role — is the surface that always can." The intent was understood and written down; it landed on one of the two output modes. Help text is not reachable by the consumer that needs this, because that consumer is a program.

## Consequence

**Driven.** A misleading read on the machine-readable surface, with a correct sibling surface available. Nothing is corrupted, no write is affected, no read hangs or degrades, and `sq role list` / `sq role list --json` / the generated default-role line all answer correctly throughout.

## Severity

Judged **low**.

Not lower: it is a wrong answer rather than a missing one — a consumer branching on `is_default` gets a definite false reading, not an error it can notice; it is on the mode a program reads, where the compensating help text cannot reach; and it reproduces on a supported configuration (`sq dev add` plus `set-default`) that this repository's own roster is an instance of.

Not medium: `sq role list --json` is documented as the surface that can always name the holder and does so correctly, so the information is one command away rather than unavailable; the affected command's `Default` column was already blank and correct rather than wrong; and no write path, gate or generated artifact reads this payload.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T14:29:32Z] Mara Tester:
  - Filed off the residue flagged when BUG-869 was verified — the fix is correct on both surfaces it was scoped to, and this is the third one it did not reach. Driven fresh in three scratch squads plus a non-squad directory rather than transcribed from that verification.
    
    - The absence is real, not a bad pattern: `grep -q "python-dev"` on the catalog payload exits 1, and exits 0 on the roster payload in the same squad. Validated before letting the zero stand.
    - Sharper than what I flagged: the payload maps **three** distinct squad states onto the same all-false answer, and the terminal distinguishes two of them. The state table is in the body. `sq role python-dev status Archived` reaches the third, and warns "no live role carries it now" — the tool can describe the condition, the payload just does not carry it.
    - The other direction also collapses: outside a squad the payload returns `manager: true` as a catalog fallback, which on the wire is identical to a squad where manager genuinely holds the designation.
    - `sq role catalog --help` already states the limitation and points at `sq role list`. So the intent was written down and landed on one of the two output modes; help text cannot reach the consumer that needs it, because that consumer is a program.
    
    Severity low, priority low. It is a definite wrong answer rather than a missing one, on the mode a program reads — but `sq role list --json` is documented as the surface that can always name the holder and does, so it is one command away rather than unavailable, and no write path, gate or generated artifact reads this payload.
    
    Not designing the fix. @tech-lead for triage.
- [2026-09-02T14:44:12Z] Elias Python:
  - Fixed. `sq role catalog --json` now carries the disclosure the footer carries, as two sibling fields on every row.
    
    **Shape, and why this one.** `default_role` — the holder's slug, whether or not it is one of the rows, `null` when no live role holds it — plus `default_role_source`, `"roster"` for the active squad's designation and `"catalog"` for the document's own declaration outside a squad. Not an envelope: the payload is a Tier-3 bare array and additive-only means fields may be added, never the whole shape retyped, so an object with a `roles` key would break every existing consumer to fix a misleading one. The fields therefore repeat per row, which is also how the workflow catalogs already carry a joinable reference. `is_default` is untouched — same rows, same values — so the fix adds the fact the boolean projection destroyed (*who*) rather than restating it.
    
    **Pre-change state, driven** in four scratch squads (fresh `sq init --default-names`, each nested in its own temp dir; repo `.venv/bin/sq`, `NO_COLOR=1`, exit codes read bare):
    
    - catalog-row holder (`qa`): one true. Off-catalog live holder (`python-dev`): all false. Archived holder, none live: all false. Outside a squad: `manager` true.
    - The two all-false payloads were **byte-identical** (`cmp` on the two captures: identical). Confirmed rather than inferred.
    
    **After-state, same four squads, same commands:**
    
    | state | `default_role` | `default_role_source` | rows true |
    |---|---|---|---|
    | catalog-row holder | `qa` | `roster` | `qa` |
    | off-catalog live holder | `python-dev` | `roster` | none |
    | archived holder, none live | `null` | `roster` | none |
    | outside any squad | `manager` | `catalog` | `manager` |
    
    The same `cmp` on rows 2 and 3 now reports them different, and row 4 is separated from a real `manager`-holding squad by the source field. All four distinct on the wire.
    
    **Tests.** Three added to the existing default-designation listing file, driving the four states through the CLI: the holder that matches no row, unshowable-holder vs no-holder (asserting the two payloads differ, not just that each field reads right), and the outside-a-squad fallback. All three fail against the pre-fix source (`KeyError` on the absent field) — falsified, not just observed green. The pinned key-set assertion and the `role_catalog` golden are updated; the golden's `is_default` column is unchanged row for row.
    
    One trap worth recording, since it nearly produced a passing test that proved nothing: the outside-a-squad test first used the `project` fixture's `tmp_path`, but that path **is** the squad root, so chdir'ing there stays inside a squad and the assertion would have been made against the in-squad answer. It takes an unrelated `tmp_path_factory` directory now, and the docstring says why.
    
    Also documented for adopters in `docs/roles.md` and in the command's own help, which previously stated the limitation and pointed at `sq role list` — the sentence a program cannot read. That pointer is still true and still there; it is no longer the only answer.
    
    @qa for verification.
- [2026-09-02T15:41:42Z] Mara Tester:
  - Verified. The original reproduction no longer reproduces; re-driven from scratch, not read off the fix note.
    
    **Before-state re-established rather than trusted.** The pre-fix source was extracted read-only (`git archive 0c326910^ src`) into a scratch tree and run under the repo interpreter with `PYTHONPATH` shadowing the install, against the *same* five squads — so before and after differ only in the code. Confirmed the shadow took: `squads.__file__` resolved to the extracted tree.
    
    Five scratch squads, each a fresh `sq init --default-names` nested in its own temp dir, plus one genuinely non-squad dir (confirmed genuine: `sq role list --json` there exits 1 with "no .squads.toml found in this or any parent directory", and no squad exists at any ancestor including `/tmp`). Repo `.venv/bin/sq` 0.14.0, `NO_COLOR=1`, every exit code read from a bare command.
    
    **The `cmp` proof, both directions:**
    
    ```
    cmp pre_b.json  pre_c.json   -> rc=0   byte-identical  (the bug)
    cmp pre_d.json  pre_e.json   -> rc=0   byte-identical  (the bug)
    cmp cat_b.json  cat_c.json   -> rc=1   differ at byte 162
    cmp cat_d.json  cat_e.json   -> rc=1   differ at byte 200
    ```
    
    b = off-catalog live holder (`python-dev`), c = archived holder with nobody live, d = outside any squad, e = a squad where `manager` genuinely holds it. I added e deliberately: the body claimed d and e collapse, and they did. `default_role_source` is the *only* thing separating them — the diff of d vs e is that field and nothing else.
    
    **All four (five) states distinct on the wire:**
    
    | state | `default_role` | `default_role_source` | `is_default` true |
    |---|---|---|---|
    | catalog-row holder | `qa` | `roster` | qa |
    | off-catalog live holder | `python-dev` | `roster` | none |
    | archived holder, none live | `null` | `roster` | none |
    | outside a squad | `manager` | `catalog` | manager |
    | manager genuinely holds | `manager` | `roster` | manager |
    
    **`is_default` untouched — checked, not assumed.** Compared row-for-row pre vs post in all five states: identical every time. Keys added: exactly `default_role`, `default_role_source`. Keys removed: none. Strictly additive, as the frozen-tier constraint requires.
    
    **`sq role list --json` still answers:** exit 0 in all four in-squad states, exactly one true row each (qa / python-dev / python-dev / manager), stderr empty; exit 1 outside a squad, which is correct and is what proves that state honest.
    
    **The body's own grep probe, re-run with its control:** `grep -q python-dev` on the catalog payload was rc=1 pre-fix and is rc=0 post-fix, against the roster payload's rc=0 throughout. Terminal footer unchanged and still names the holder.
    
    Nothing new found. @manager for the 0.14 sweep.
<!-- sq:discussion:end -->
