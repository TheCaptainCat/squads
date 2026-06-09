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
    slug: str  # a role slug, or the DEV sentinel
    text: str


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
            "sq tree EPIC-…",
        ),
        roles=(
            RoleGuide("product-owner", "Define the epic's goal and the outcomes it groups."),
            RoleGuide("architect", "Shape it technically; spin off ADRs for cross-cutting calls."),
            RoleGuide("tech-lead", "Group features under the epic and keep its scope coherent."),
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
                "Author the feature and its user stories; define acceptance criteria.",
            ),
            RoleGuide(
                "tech-lead",
                "Break it into tasks (parent = this feature); map each subtask to a user story.",
            ),
            RoleGuide("qa", "Derive test cases from the user stories; verify acceptance criteria."),
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
                "Author tasks, set the feature parent, and map each subtask to a user story.",
            ),
            RoleGuide(
                DEV,
                "Implement the task; write tests; comment progress and hand off via `… comment`.",
            ),
            RoleGuide("reviewer", "Review the changes; open a review or request changes."),
            RoleGuide("qa", "Verify the task once implemented."),
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
            RoleGuide("qa", "Report bugs with clear repro steps; verify fixes."),
            RoleGuide(DEV, "Fix the bug in a task and link it with `--kind fixes`."),
            RoleGuide("tech-lead", "Triage and prioritise bugs."),
            RoleGuide("reviewer", "Review the fix before it lands."),
        ),
    ),
    ItemType.DECISION: ItemPlaybook(
        overview="An architecture decision record: context, decision, consequences.",
        lifecycle="Proposed → Accepted → Superseded (+ Rejected, Deprecated)",
        commands=('sq create decision "…" --author architect', "sq decision <n> status Accepted"),
        roles=(
            RoleGuide("architect", "Author ADRs; capture context, the decision, and consequences."),
            RoleGuide("tech-lead", "Co-author and review decisions; supersede when they change."),
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
                "Perform reviews; log findings (`review <n> add-finding`); drive to a verdict.",
            ),
            RoleGuide(
                DEV,
                "Address findings (`finding <k> update --status Fixed`); link the fix task.",
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
            RoleGuide("architect", "Author guides capturing good practice and anti-patterns."),
            RoleGuide("tech-lead", "Co-author guides drawn from real tasks."),
            RoleGuide("tech-writer", "Edit and maintain guides for clarity and currency."),
        ),
    ),
}

SQUADS_SKILL = "squads"


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
    """Skill names a role's Claude pointer should preload: the squads skill + its item skills."""
    return [SQUADS_SKILL, *(item_skill_name(t) for t in item_types_for_role(slug))]
