"""The team playbook: which roles interact with each item type, and how.

Drives two things:
  - the per-item-type managed skills (one role-directed section per interacting role), and
  - the reverse mapping (which skills each role's Claude pointer preloads).

A role that does not interact with an item type does not get that item's skill.
"""

from dataclasses import dataclass

from squads._models._enums import ItemType

#: Sentinel interacting "role" that expands to every developer role (slug ``<tech>-dev``).
DEV = "*dev"


@dataclass(frozen=True)
class RoleGuide:
    """Precise, structured guidance for one actor on one item type.

    Rendered under fixed labels in the per-item skill, so every actor reads the same shape:
    what to check first, what to do, what moves the work on, and what to stay out of.
    """

    slug: str  # a role slug, or the DEV sentinel
    enter: tuple[str, ...] = ()  # read/confirm before acting
    do: tuple[str, ...] = ()  # the core actions (with concrete `sq …` commands)
    handoff: tuple[str, ...] = ()  # the trigger + target that moves work on
    watch: tuple[str, ...] = ()  # scope discipline / pitfalls ("don't … — that's <role>")


@dataclass(frozen=True)
class ItemPlaybook:
    overview: str
    lifecycle: str
    commands: tuple[str, ...]
    roles: tuple[RoleGuide, ...]


PLAYBOOK: dict[ItemType, ItemPlaybook] = {
    ItemType.EPIC: ItemPlaybook(
        overview="A large body of work that groups related features toward one outcome.",
        lifecycle="Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)",
        commands=(
            'sq create epic "…" --author <slug>',
            "sq feature <n> update --parent EPIC-…   # group a feature under this epic",
            "sq tree EPIC-… [--json]",
        ),
        roles=(
            RoleGuide(
                "product-owner",
                enter=("confirm the outcome the epic targets and who it's for",),
                do=(
                    'author it (`sq create epic "…" --author product-owner`)',
                    "set the body to the goal + the outcomes it groups (`sq epic <n> body -m …`)",
                ),
                handoff=(
                    "when the epic is ready, create the features under it and `@tech-lead` to "
                    "break them down",
                ),
                watch=("an epic is an outcome, not a task list — keep it about the why",),
            ),
            RoleGuide(
                "architect",
                enter=("read the epic's goal and any related epics/ADRs",),
                do=(
                    "shape it technically; spin off ADRs (`sq create decision`) for cross-cutting "
                    "calls and link them (`sq epic <n> ref add ADR-… --kind related`)",
                ),
                handoff=(
                    "when the technical shape is settled, `@tech-lead` to break it into features "
                    "and tasks",
                ),
            ),
            RoleGuide(
                "tech-lead",
                enter=("review the epic's features and their state (`sq tree EPIC-… --json`)",),
                do=(
                    "group features under the epic (`sq feature <n> update --parent EPIC-…`)",
                    "keep its scope coherent; track status as features progress",
                ),
                watch=("authoring features is the product-owner's job, not yours",),
            ),
        ),
    ),
    ItemType.FEATURE: ItemPlaybook(
        overview="A user-facing capability, described through persona-worded user stories.",
        lifecycle="Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)",
        commands=(
            'sq create feature "…" --author product-owner [--parent EPIC-…]',
            'sq feature <n> add-story "As a <role>, I want … so that …"',
            "sq feature <n> story <k> update --status InProgress   # Todo → InProgress → Done",
            "sq feature <n> stories",
        ),
        roles=(
            RoleGuide(
                "product-owner",
                enter=("confirm the user need and which epic (if any) it belongs under",),
                do=(
                    'author the feature (`sq create feature "…" --author product-owner`)',
                    "add persona-worded user stories "
                    '(`sq feature <n> add-story "As a … I want …"`)',
                    "write each story's acceptance criteria in its body "
                    "(`sq feature <n> story <k> body -m …`)",
                ),
                handoff=(
                    "when stories and acceptance criteria are complete and the feature is "
                    "greenlit, `@tech-lead` to break it into tasks",
                ),
                watch=(
                    "stories describe user value + acceptance criteria — not implementation steps",
                ),
            ),
            RoleGuide(
                "tech-lead",
                enter=("read every user story + its acceptance criteria (`sq feature <n> show`)",),
                do=(
                    "create tasks with this feature as parent "
                    "(`sq create task … --parent FEAT-<n>`)",
                    "map each subtask to one user story (`sq task <n> add-subtask … --story USk`)",
                ),
                handoff=(
                    "when tasks are created, assigned, and sequenced, `@<tech>-dev` (or spawn "
                    "the developer) to begin implementation",
                ),
                watch=("if a story is ambiguous, ask the product-owner (`@product-owner`) first",),
            ),
            RoleGuide(
                "qa",
                enter=("read the user stories + acceptance criteria",),
                do=(
                    "derive test cases from each story",
                    "verify the feature against its acceptance criteria once tasks land",
                ),
                handoff=(
                    "when acceptance criteria all pass, confirm in a comment so the feature can "
                    "close; when one fails, file a bug and `@tech-lead`",
                ),
            ),
        ),
    ),
    ItemType.TASK: ItemPlaybook(
        overview="A unit of implementation work. Its parent is the feature it implements; "
        "subtasks each map to one user story.",
        lifecycle="Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)",
        commands=(
            'sq create task "…" --author tech-lead --parent FEAT-…',
            'sq task <n> add-subtask "…" --story US1',
            "sq task <n> subtask <k> update --status InProgress   # Todo → InProgress → Done",
            "sq task <n> ref add BUG-… --kind fixes   # or REV-… --kind addresses",
            "sq task <n> status InProgress",
        ),
        roles=(
            RoleGuide(
                "tech-lead",
                enter=("confirm the parent feature exists and its stories are clear",),
                do=(
                    'author the task (`sq create task "…" --author tech-lead --parent FEAT-…`)',
                    "add subtasks, each mapped to a story (`add-subtask … --story USn`)",
                    "set `--priority`/`--assignee`; sequence with `ref add … --kind blocks`",
                ),
                handoff=(
                    "once the task is fully defined, assign the developer "
                    "(`sq task <n> update --assignee <tech>-dev`) — spawn or `@<tech>-dev` to "
                    "start implementation",
                ),
                watch=(
                    "a task's parent must be a feature; "
                    "link bugs/reviews via refs, never as parent",
                ),
            ),
            RoleGuide(
                DEV,
                enter=(
                    "read the parent feature's stories + acceptance criteria "
                    "(`sq feature <n> show`)",
                    "confirm your subtask→story mapping",
                ),
                do=(
                    "`sq task <n> status InProgress`",
                    "implement with tests; tick subtasks (`subtask <k> update --status …`)",
                    "log progress with `sq task <n> comment --as <your-slug> -m …`",
                ),
                handoff=(
                    "when implementation is complete, `sq task <n> status InReview`",
                    "comment a summary of what changed + `@reviewer`/`@qa`",
                    "for a review follow-up, link it (`ref add REV-… --kind addresses`)",
                ),
                watch=(
                    "don't author features/tasks — that's the product-owner/tech-lead",
                    "file a newly-found defect as a bug; don't silently expand scope",
                ),
            ),
            RoleGuide(
                "reviewer",
                enter=("read the task's changes + the linked feature stories",),
                do=(
                    "open a review (`sq create review … --author reviewer`) and link it "
                    "(`sq task <n> ref add REV-… --kind addresses`)",
                    "log findings with `--severity`; drive Requested → InReview → verdict",
                ),
                handoff=(
                    "on ChangesRequested, `@<tech>-dev` with the findings",
                    "on Approved, comment the verdict so the task can close",
                ),
                watch=("request changes — don't fix the code yourself",),
            ),
            RoleGuide(
                "qa",
                enter=(
                    "derive test cases from the parent feature's stories + acceptance criteria",
                ),
                do=("verify the implementation against each story; reproduce on failure",),
                handoff=(
                    "on pass, comment confirmation so the task can reach Done",
                    "on fail, file a bug (`sq create bug …`) and `@<tech>-dev`",
                ),
                watch=("verify against acceptance criteria, not just that it runs",),
            ),
        ),
    ),
    ItemType.BUG: ItemPlaybook(
        overview="A defect: what's wrong, how to reproduce, expected vs actual.",
        lifecycle="Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)",
        commands=(
            'sq create bug "…" --author <slug>',
            "sq task <n> ref add BUG-… --kind fixes",
            "sq bug <n> status InProgress",
        ),
        roles=(
            RoleGuide(
                "qa",
                enter=("reproduce the defect and capture the exact steps",),
                do=(
                    'file it (`sq create bug "…" --author qa`)',
                    "in the body give repro steps + expected vs actual (`sq bug <n> body -m …`)",
                    "set `--severity`/`--priority`",
                ),
                handoff=(
                    "once filed, `@tech-lead` to triage; once a fix task lands, verify it and "
                    "confirm in a comment so the bug can close",
                ),
            ),
            RoleGuide(
                DEV,
                enter=("read the repro steps; confirm you can reproduce it",),
                do=(
                    "fix it inside a task and link it (`sq task <n> ref add BUG-… --kind fixes`)",
                    "add a regression test",
                ),
                handoff=(
                    "when the fix is ready, move the task to InReview and `@reviewer`/`@qa`; "
                    "the bug closes when the fix is verified",
                ),
                watch=("track the fix on a task — don't implement straight off the bug",),
            ),
            RoleGuide(
                "tech-lead",
                enter=("assess impact + severity against current work",),
                do=("triage and prioritise; create the fix task and assign a developer",),
                handoff=(
                    "once the fix task is created and assigned, `@<tech>-dev` to start the fix",
                ),
            ),
            RoleGuide(
                "reviewer",
                enter=("read the bug + the fix task's changes",),
                do=("review the fix for correctness and a regression test before it lands",),
                watch=("make sure the root cause is fixed, not just the symptom",),
            ),
        ),
    ),
    ItemType.DECISION: ItemPlaybook(
        overview="An architecture decision record: context, decision, consequences.",
        lifecycle="Proposed → Accepted → Superseded (+ Rejected, Deprecated)",
        commands=('sq create decision "…" --author architect', "sq decision <n> status Accepted"),
        roles=(
            RoleGuide(
                "architect",
                enter=("gather the context + the options you're weighing",),
                do=(
                    'author the ADR (`sq create decision "…" --author architect`)',
                    "in the body capture context, the decision, and consequences",
                    "link what it affects (`sq decision <n> ref add … --kind related`)",
                ),
                handoff=(
                    "once the decision is agreed, `sq decision <n> status Accepted` and "
                    "`@tech-lead` to apply it in the affected tasks",
                ),
                watch=("supersede an old ADR rather than editing its decision after acceptance",),
            ),
            RoleGuide(
                "tech-lead",
                enter=("read the proposed decision + its context",),
                do=("co-author/review it; ensure tasks follow it once Accepted",),
                handoff=("supersede it (new ADR) when reality changes",),
            ),
        ),
    ),
    ItemType.REVIEW: ItemPlaybook(
        overview="A code review: scope, findings (each with severity + status), and a verdict.",
        lifecycle="Requested → InReview → ChangesRequested → Approved (+ Rejected)",
        commands=(
            'sq create review "…" --author reviewer',
            'sq review <n> add-finding "…" --severity high',
            "sq review <n> finding <k> update --status Fixed   # transition a finding",
            "sq review <n> status InReview",
            "sq task <n> ref add REV-… --kind addresses",
        ),
        roles=(
            RoleGuide(
                "reviewer",
                enter=("read the task/changes under review + the feature's acceptance criteria",),
                do=(
                    "`sq review <n> status InReview`",
                    'log each issue as a finding (`add-finding "…" --severity …`)',
                    "drive to a verdict: Approved or ChangesRequested",
                ),
                handoff=(
                    "on ChangesRequested, `@<tech>-dev` with the findings",
                    "on Approved, comment the verdict",
                ),
                watch=("severity-tag findings honestly; don't approve with open high findings",),
            ),
            RoleGuide(
                DEV,
                enter=("read every finding and its severity (`sq review <n> findings`)",),
                do=(
                    "fix each one, then `sq review <n> finding <k> update --status Fixed`",
                    "link the fix task (`sq task <n> ref add REV-… --kind addresses`)",
                ),
                handoff=("`@reviewer` once all findings are Fixed, for re-review",),
                watch=("don't close findings you didn't actually address",),
            ),
        ),
    ),
    ItemType.GUIDE: ItemPlaybook(
        overview="Project-agnostic best-practice notes on a technology or framework.",
        lifecycle="Draft → Published → Deprecated",
        commands=(
            'sq create guide "…" --author architect [--tech …] [--tag …]',
            "sq guide <n> status Published",
        ),
        roles=(
            RoleGuide(
                "architect",
                enter=("identify the recurring practice or anti-pattern worth capturing",),
                do=(
                    'author it (`sq create guide "…" --author architect --tech …`)',
                    "write good practice + anti-patterns in the body",
                ),
                handoff=(
                    "when the first draft is complete, `@tech-writer` to polish; set "
                    "`sq guide <n> status Published` once it's clean",
                ),
            ),
            RoleGuide(
                "tech-lead",
                enter=("spot a lesson from a real task worth generalising",),
                do=("co-author the guide drawn from concrete work",),
            ),
            RoleGuide(
                "tech-writer",
                enter=("read the draft guide",),
                do=("edit for clarity, structure, and currency",),
                handoff=("`sq guide <n> status Published` when it's clean",),
                watch=("keep it project-agnostic; deprecate guides that go stale",),
            ),
        ),
    ),
}

SQUADS_SKILL = "squads"
#: Always-loaded skill for the start-of-conversation ritual (detect the human, register, greet).
GREETING_SKILL = "greeting"


def is_dev_slug(slug: str) -> bool:
    return slug.endswith("-dev")


def item_skill_name(item_type: ItemType) -> str:
    return f"sq-{item_type.value}"


def managed_item_types() -> list[ItemType]:
    return list(PLAYBOOK)


def item_types_for_role(slug: str) -> list[ItemType]:
    """Item types this role interacts with (DEV sentinel matches any ``*-dev`` slug)."""
    dev = is_dev_slug(slug)
    out: list[ItemType] = []
    for item_type, pb in PLAYBOOK.items():
        slugs = {g.slug for g in pb.roles}
        if slug in slugs or (dev and DEV in slugs):
            out.append(item_type)
    return out


def skills_for_role(slug: str) -> list[str]:
    """Skill names a role's pointer preloads: the always-on skills + the role's item skills."""
    return [SQUADS_SKILL, GREETING_SKILL, *(item_skill_name(t) for t in item_types_for_role(slug))]
