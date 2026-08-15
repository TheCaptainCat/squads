"""Repo gate: every agent-facing surface squads generates must be built from the ACTIVE spec,
the ACTIVE playbook and the LIVE roster — never from a bundled literal.

Two halves, because neither alone is enough:

* a **behavioural probe** that renders each surface against a squad sharing no vocabulary with
  the bundled documents at all — different squad dir, different roster slugs, a renamed retired
  status, a renamed superseded status, a renamed sub-entity local prefix — and asserts that not
  one bundled literal survives into the output. This is the half that catches the real defect
  shape: a literal sitting inside a runnable command, right beside spec-derived text on the same
  line, which hands an agent a command that exits 1;
* a **text scan** for the bundled anchor type name, which no probe can catch when the literal
  and the derived value happen to agree on the bundled spec.

The literals scanned for are the ones a squad can legitimately not have: ``sq init --roles
minimal`` gives a roster with no ``qa``; a lifecycle override renames ``Cancelled``; a sub-entity
kind declares its own ``local_prefix``; ``sq init --squad-dir team`` moves the squad folder.
"""

import re
from pathlib import Path

import pytest

from squads._backends._agents_md._backend import _also_creatable_types
from squads._interactions import cheatsheet_anchor_context
from squads._rendering._engine import render
from squads._workflow import bundled_spec
from squads._workflow._models import Lifecycle, WorkflowSpec

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATES_DIR = _REPO_ROOT / "src" / "squads" / "_rendering" / "templates"

#: The templates whose worked examples are built from `cheatsheet_anchor_type`/
#: `authoring_owner`/the live roster rather than a hardcoded literal. Not every template in the
#: tree belongs here: a per-type item body template (`items/task.md.j2`) legitimately names its
#: own type.
_GUARDED_TEMPLATES: tuple[str, ...] = (
    "agents/squads_skill.md.j2",
    "agents_md/agents_section.md.j2",
    "claude/claude_section.md.j2",
    "workflow.md.j2",
    "workflow_static.md.j2",
)

#: ``"task"`` never appears as ordinary English prose in this codebase's generated text —
#: unlike ``"review"``/``"feature"``, which are common nouns too — so a plain word-boundary
#: match is a clean, zero-false-positive signal, the same shape as the other ``tests/meta``
#: text scans.
_TASK_WORD = re.compile(r"\btask\b")

#: Two probe rosters, because they falsify different things and one alone passes for the wrong
#: reason. ``_MINIMAL`` carries no bundled slug at all — the `sq init --roles minimal` shape,
#: which is what makes an ``--assignee qa`` literal exit 1 — but a roster with no in-lane author
#: also renders no authoring bullet, so the story-prefix line the same scan must see is simply
#: absent. ``_FULL`` keeps the bundled authoring slugs (so those bullets render) and adds a
#: developer whose slug the bundled catalog does not carry.
_MINIMAL_ROSTER: list[dict[str, str]] = [
    {"full_name": "Robin Crew", "title": "crew lead", "slug": "crew-lead"},
    {"full_name": "Sam Crew", "title": "Rust developer", "slug": "rust-dev"},
]
_FULL_ROSTER: list[dict[str, str]] = [
    {"full_name": "Robin Crew", "title": "crew lead", "slug": "tech-lead"},
    {"full_name": "Nadia Crew", "title": "product owner", "slug": "product-owner"},
    {"full_name": "Kit Crew", "title": "architect", "slug": "architect"},
    {"full_name": "Ola Crew", "title": "code reviewer", "slug": "reviewer"},
    {"full_name": "Zaid Crew", "title": "QA engineer", "slug": "qa"},
    {"full_name": "Sam Crew", "title": "Rust developer", "slug": "rust-dev"},
]
_PROBE_ROSTERS: tuple[tuple[str, list[dict[str, str]]], ...] = (
    ("minimal", _MINIMAL_ROSTER),
    ("full", _FULL_ROSTER),
)

#: Bundled vocabulary that must not survive into a render driven by the probe squad below.
#: Each is paired with what an adopter does to make it wrong.
_FORBIDDEN_LITERALS: tuple[tuple[str, str], ...] = (
    ("--assignee qa", "a roster with no `qa` role (`sq init --roles minimal`)"),
    ("status Cancelled", "a lifecycle whose retired state is named otherwise"),
    ("Superseded", "a lifecycle whose superseded state is named otherwise"),
    ("US<n>", "a sub-entity kind declaring its own local_prefix"),
    ("USn", "a sub-entity kind declaring its own local_prefix"),
    ("squads/agents", "`sq init --squad-dir team`"),
)


def _probe_spec() -> WorkflowSpec:
    """The bundled spec with every vocabulary word this guard scans for renamed away.

    Renamed, not dropped: dropping a type would degrade the templates down their "no anchor"
    branch and the probe would pass for the wrong reason — the literal would be absent because
    nothing rendered, not because the derivation ran.
    """
    base = bundled_spec()

    def _rename_status(machine: Lifecycle, old: str, new: str) -> Lifecycle:
        return Lifecycle(
            initial=new if machine.initial == old else machine.initial,
            transitions={
                (new if src == old else src): [(new if d == old else d) for d in dsts]
                for src, dsts in machine.transitions.items()
            },
        )

    renames = {"Cancelled": "Abandoned", "Superseded": "Retired"}
    lifecycles = dict(base.lifecycles)
    for name, machine in base.lifecycles.items():
        for old, new in renames.items():
            machine = _rename_status(machine, old, new)
        lifecycles[name] = machine
    statuses = {renames.get(s, s): spec for s, spec in base.statuses.items()}

    kinds = dict(base.subentity_kinds)
    kinds["story"] = kinds["story"].model_copy(update={"local_prefix": "SR"})

    return WorkflowSpec.model_validate(
        {
            "items": base.items,
            "statuses": statuses,
            "lifecycles": lifecycles,
            "prefix_to_type": base.prefix_to_type,
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": kinds,
            "roles": base.roles,
        }
    )


def _probe_renders(roles: list[dict[str, str]]) -> dict[str, str]:
    spec = _probe_spec()
    anchor_ctx = cheatsheet_anchor_context(spec)
    return {
        "agents/squads_skill.md.j2": render(
            "agents/squads_skill.md.j2", squad_dir="team", spec=spec, roles=roles
        ),
        "agents/memory_skill.md.j2": render("agents/memory_skill.md.j2", squad_dir="team"),
        "claude/claude_section.md.j2": render(
            "claude/claude_section.md.j2",
            squad_dir="team",
            roles=roles,
            operators=[],
            default_role_full_name=roles[0]["full_name"],
            default_role_slug=roles[0]["slug"],
            spec=spec,
        ),
        "agents_md/agents_section.md.j2": render(
            "agents_md/agents_section.md.j2",
            squad_dir="team",
            roles=[{**r, "mission": "", "responsibilities": []} for r in roles],
            operators=[],
            spec=spec,
            also_creatable_types=_also_creatable_types(spec, anchor_ctx["anchor"]),
            **anchor_ctx,
        ),
        "workflow.md.j2": render("workflow.md.j2", spec=spec, roles=roles),
    }


@pytest.mark.parametrize(("roster_name", "roles"), _PROBE_ROSTERS)
@pytest.mark.parametrize(("literal", "why"), _FORBIDDEN_LITERALS)
def test_no_bundled_vocabulary_literal_survives_a_renamed_squad(
    literal: str, why: str, roster_name: str, roles: list[dict[str, str]]
) -> None:
    for name, rendered in _probe_renders(roles).items():
        assert literal not in rendered, (
            f"{name}: generated agent text still contains the bundled literal {literal!r} "
            f"after rendering against {why} on the {roster_name} roster — derive it from the "
            "active spec / live roster"
        )


def test_the_probe_squad_actually_renders_its_own_vocabulary() -> None:
    """Falsification floor: without this, every assertion above passes on an empty render —
    a roster with no in-lane author renders no authoring bullet at all, so the very lines the
    scan is meant to read would simply be missing."""
    renders = _probe_renders(_FULL_ROSTER)
    assert "status Abandoned" in renders["workflow.md.j2"]
    assert "--story SRn" in renders["claude/claude_section.md.j2"]
    assert "--story SRn" in renders["workflow.md.j2"]
    assert "--assignee rust-dev" in renders["agents/squads_skill.md.j2"]
    assert "team/agents/memory" in renders["agents/memory_skill.md.j2"]
    assert "Retired" in renders["workflow.md.j2"]


def test_no_bare_task_literal_in_the_guarded_generated_templates() -> None:
    for rel in _GUARDED_TEMPLATES:
        text = (_TEMPLATES_DIR / rel).read_text(encoding="utf-8")
        hit_lines = [
            lineno
            for lineno, line in enumerate(text.splitlines(), start=1)
            if _TASK_WORD.search(line)
        ]
        assert not hit_lines, (
            f"{rel}: hardcoded 'task' literal at line(s) {hit_lines} — derive it from "
            "interactions.cheatsheet_anchor_type(spec) (or the resolved spec's own "
            "item/authoring data) instead of naming the bundled type directly"
        )
