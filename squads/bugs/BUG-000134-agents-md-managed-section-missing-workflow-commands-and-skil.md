---
id: BUG-134
sequence_id: 134
type: bug
title: AGENTS.md managed section missing workflow commands and skill content (agents_md
  backend)
status: Verified
parent: FEAT-16
author: qa
created_at: '2026-06-15T13:54:47Z'
updated_at: '2026-06-16T09:42:35Z'
---
<!-- sq:body -->
## Symptom

After `sq init --backend agents_md` + `sq sync`, the generated AGENTS.md does not carry actual workflow or skill content as stated in FEAT-16 US1 acceptance ('a valid AGENTS.md carrying roster, workflow and skill content').

## Actual AGENTS.md content

- Roster: present (role names, titles, slugs) -- PASS

- Workflow: only the sentence 'a status lifecycle, and a handoff protocol' — no sq commands, no status machine, no workflow.md.j2 content

- Skill content: absent from AGENTS.md. Staging files in .agents_md/roles/ have role missions but are never compiled into the file non-Claude tools read.

- Role definitions section shows only '**Role:** manager' — no mission text despite staging files having it.

## Expected

AGENTS.md managed section should include: (1) workflow.md.j2 content (team workflow, status aliases, ref kinds) so non-Claude tools understand how to use squads; (2) role missions from staging files compiled into AGENTS.md, not left in hidden .agents_md/ directory.

## Root cause

agents_section.md.j2 template does not include workflow.md.j2 and write_managed does not compile .agents_md/roles/ staging content into AGENTS.md. TASK-132 approach document said to reuse workflow.md.j2 but the implementation did not.

## Reproduction

```bash

cd $(mktemp -d) && uv run sq init --backend agents_md --roles minimal --default-names

grep -i 'workflow\|sq create\|Todo\|InProgress' AGENTS.md   # returns nothing actionable

```
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
