"""TASK-000256 — Characterization goldens: pin sq workflow / CLAUDE.md / sq-<type> skill output.

These goldens capture the EXACT rendered output of three artifacts the FEAT-000210 rewire will
touch (TASK-257 dynamic CLI, TASK-261 spec-derived renderer + CLAUDE.md, TASK-260 generated
skill).  They enforce AC#7 (non-custom squads byte-identical) and AC#8 (golden green).

ALL inputs are frozen so comparisons are deterministic:

  Roster  — a pinned fixed list that includes one python-dev, so the ``has_dev`` gate in
             ``_write_item_skills`` is always True.
             See [[pin-roster-when-diffing-generated-skills]].
  Version — pinned to ``PINNED_VERSION`` below; any version bump that changes rendered output
             shows up as a golden failure and must update both PINNED_VERSION and the fixture.
  squad_dir — the literal string ``"squads"`` (not a tmp-path) so the rendered path references
              are stable across runs.
  FORCE_COLOR / ANSI — stripped by the ``_neutralize_forced_color`` autouse conftest fixture;
             these tests call render() directly (no CLI) so no ANSI enters at all.
  Clock   — irrelevant here (templates contain no timestamps), but conftest frozen_time is
             available as a backstop.

Regenerating goldens
--------------------
Set ``UPDATE_GOLDENS=1`` in the environment and run the suite normally::

    UPDATE_GOLDENS=1 uv run pytest tests/test_golden_rendered_output.py -v

The suite will *write* (not read) the golden files, updating them to match the current output.
Commit the diff — any rendered-output change then appears in the PR as a deliberate golden update.

Coverage
--------
This module pins:

  1. ``sq workflow`` raw rendered markdown (the template output before Rich processes it) — the
     full text from ``render("workflow.md.j2", spec=bundled_spec())`` (TASK-261: spec-derived).
  2. The managed CLAUDE.md workflow section body — the text rendered by
     ``render("claude/claude_section.md.j2", ...)`` with the pinned roster.
  3. The managed AGENTS.md workflow section body — the text rendered by
     ``render("agents_md/agents_section.md.j2", ...)`` with the pinned roster.
  4. Every bundled ``sq-<type>`` skill body — the text rendered by
     ``render("agents/item_skill.md.j2", ...)`` for each type in ``managed_item_types()``,
     with the pinned roster (has_dev=True so developer sections are included).

What breaks these tests
-----------------------
Any of the following causes a golden failure (which is the INTENT):

  - A rewire task (257/260/261) changes the workflow template, CLAUDE/AGENTS template, or
    item_skill template.
  - A playbook.toml or TYPE_ALIASES change alters rendered content.
  - A version bump changes the squads:version comment in skill bodies (update PINNED_VERSION
    and run UPDATE_GOLDENS=1).
  - A roster change in the PINNED_ROSTER constant (changing the developer name, adding a new
    bundled role) alters skill section headers — update the roster constant and golden together.
"""

import os
from pathlib import Path
from typing import Any

from squads._backends._base import OperatorView, RoleView
from squads._interactions import DEV, PLAYBOOK, is_dev_slug, item_skill_name, managed_item_types
from squads._rendering._engine import render
from squads._workflow import bundled_spec as _bundled_spec

# Golden files live in the shared goldens directory alongside the JSON goldens.
GOLDENS_DIR = Path(__file__).parent / "goldens"

# Set UPDATE_GOLDENS=1 to write/update golden files instead of comparing.
_UPDATE = os.getenv("UPDATE_GOLDENS") == "1"

# ---------------------------------------------------------------------------
# Frozen inputs — ALL must be held constant or the golden comparison is flaky.
# ---------------------------------------------------------------------------

#: Pinned version string.  When the package version bumps, this constant must be updated
#: TOGETHER WITH a golden update (UPDATE_GOLDENS=1).  Never read __version__ at test time:
#: that would make the golden track the current version rather than asserting it is unchanged.
PINNED_VERSION: str = "0.5.0"

#: Fixed squad_dir string used in template context.  Using the literal "squads" (not a
#: tmp-path) makes the rendered path references stable across machines and runs.
PINNED_SQUAD_DIR: str = "squads"

#: Fixed roster — all 8 bundled named roles + one python-dev.
#:
#: The python-dev is deliberately included so ``has_dev`` is always True: omitting a dev
#: would hide the "## For developers" sections, making the golden miss a third of the task
#: skill body.  The exact developer name ("Elias Python") is the bundled catalog default for
#: the python stack (see DEV_NAME_POOL in _catalog.py).
#:
#: IMPORTANT: changing any name/slug here changes the golden.  Don't "fix" this list; if
#: the bundled catalog changes, update this constant AND re-run UPDATE_GOLDENS=1.
PINNED_ROSTER: list[RoleView] = [
    RoleView(slug="manager", full_name="Catherine Manager", title="Manager", is_default=True),
    RoleView(slug="architect", full_name="Robert Architect", title="Architect", is_default=False),
    RoleView(slug="tech-lead", full_name="Olivia Lead", title="Tech lead", is_default=False),
    RoleView(slug="reviewer", full_name="Paul Reviewer", title="Code reviewer", is_default=False),
    RoleView(slug="qa", full_name="Mara Tester", title="QA engineer", is_default=False),
    RoleView(slug="devops", full_name="Hugo Ops", title="DevOps engineer", is_default=False),
    RoleView(
        slug="product-owner",
        full_name="Nina Product",
        title="Product owner",
        is_default=False,
    ),
    RoleView(
        slug="tech-writer",
        full_name="Theo Writer",
        title="Technical writer",
        is_default=False,
    ),
    RoleView(
        slug="python-dev",
        full_name="Elias Python",
        title="Python developer",
        is_default=False,
    ),
]

#: Fixed operator roster — one human operator.  Affects the CLAUDE/AGENTS section "Operators"
#: list, so it must be stable.
PINNED_OPERATORS: list[OperatorView] = [
    OperatorView(slug="op-pierre", full_name="Pierre Chat"),
]

# Derived from PINNED_ROSTER — stable for the duration of the module.
_BY_SLUG: dict[str, RoleView] = {r.slug: r for r in PINNED_ROSTER}
_HAS_DEV: bool = any(is_dev_slug(r.slug) for r in PINNED_ROSTER)
_DEFAULT_ROLE: RoleView = next(r for r in PINNED_ROSTER if r.is_default)


# ---------------------------------------------------------------------------
# Golden-comparison helper
# ---------------------------------------------------------------------------


def _check_golden(name: str, actual: str) -> None:
    """Compare *actual* (a rendered string) to the stored golden, or write it.

    Files are stored as ``.txt`` under ``tests/goldens/`` to distinguish them
    from the JSON goldens produced by ``test_golden_json.py``.
    """
    path = GOLDENS_DIR / f"{name}.txt"
    if _UPDATE:
        GOLDENS_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        return
    assert path.exists(), (
        f"Golden file missing: {path}\n"
        f"Run UPDATE_GOLDENS=1 uv run pytest tests/test_golden_rendered_output.py to generate it."
    )
    expected = path.read_text(encoding="utf-8")
    first_diff = next(
        (i for i, (a, b) in enumerate(zip(actual, expected, strict=False)) if a != b),
        min(len(actual), len(expected)),
    )
    assert actual == expected, (
        f"Golden mismatch for {name!r}.\n"
        f"If this change is intentional, regenerate with:\n"
        f"  UPDATE_GOLDENS=1 uv run pytest tests/test_golden_rendered_output.py -v\n"
        f"and commit the updated golden file in the same PR.\n\n"
        f"First diff at char {first_diff}:\n"
        f"  actual  [{len(actual)} chars]: {actual[:120]!r}...\n"
        f"  expected[{len(expected)} chars]: {expected[:120]!r}..."
    )


# ---------------------------------------------------------------------------
# Render helpers (mirror the production render calls precisely)
# ---------------------------------------------------------------------------


def _render_workflow_cheatsheet() -> str:
    """Render the workflow cheatsheet template — the raw markdown before Rich processes it.

    TASK-261: now rendered from the live bundled spec instead of the static TYPE_ALIASES dict.
    The bundled spec produces byte-identical output for a non-custom squad (AC#7/#8).
    """
    return render("workflow.md.j2", spec=_bundled_spec())


def _render_claude_section() -> str:
    """Render the CLAUDE.md managed section body with the pinned roster.

    Mirrors ``ClaudeCodeBackend.write_managed`` → ``render("claude/claude_section.md.j2", ...)``.
    The returned text is passed to ``claude_md.inject()`` which wraps it in the
    ``<!-- squads:start --> … <!-- squads:end -->`` markers — we pin the body only, not the
    outer markers (those are part of the inject protocol and are independently tested).
    """
    return render(
        "claude/claude_section.md.j2",
        squad_dir=PINNED_SQUAD_DIR,
        roles=[{"full_name": r.full_name, "title": r.title, "slug": r.slug} for r in PINNED_ROSTER],
        operators=[{"full_name": o.full_name, "slug": o.slug} for o in PINNED_OPERATORS],
        default_role_full_name=_DEFAULT_ROLE.full_name,
        default_role_slug=_DEFAULT_ROLE.slug,
        spec=_bundled_spec(),
    )


def _render_agents_section() -> str:
    """Render the AGENTS.md managed section body with the pinned roster.

    Mirrors ``AgentsMdBackend.write_managed`` → ``render("agents_md/agents_section.md.j2", ...)``.
    The staging-file path for role missions is skipped (mission="", responsibilities=[]) because
    the staging files are generated dynamically from the index and are not part of the template
    rendering surface we are pinning here.  The template falls back to mission-absent rendering,
    which is the same path taken in unit-level backend tests.

    TASK-261: passes the bundled spec instead of the deprecated TYPE_ALIASES dict.
    """
    return render(
        "agents_md/agents_section.md.j2",
        squad_dir=PINNED_SQUAD_DIR,
        roles=[
            {
                "full_name": r.full_name,
                "title": r.title,
                "slug": r.slug,
                "mission": "",
                "responsibilities": [],
            }
            for r in PINNED_ROSTER
        ],
        operators=[{"full_name": o.full_name, "slug": o.slug} for o in PINNED_OPERATORS],
        spec=_bundled_spec(),
    )


def _render_item_skill(item_type: Any) -> str:  # item_type: ItemType
    """Render the sq-<type> skill body for *item_type* with the pinned roster.

    Mirrors ``ClaudeCodeBackend._write_item_skills`` exactly:
    - ``by_slug`` is built from PINNED_ROSTER.
    - ``has_dev`` is True (python-dev is in the roster).
    - The DEV sentinel expands to the literal title ``"developers"``.
    - Roles absent from the pinned roster are silently skipped (same as production).
    """
    pb = PLAYBOOK[item_type]
    sections: list[dict[str, Any]] = []
    for guide in pb.roles:
        if guide.slug == DEV:
            if not _HAS_DEV:
                continue
            title = "developers"
        elif guide.slug in _BY_SLUG:
            r = _BY_SLUG[guide.slug]
            title = f"{r.full_name} (`{r.slug}`)"
        else:
            continue
        sections.append(
            {
                "title": title,
                "enter": guide.enter,
                "do": guide.do,
                "handoff": guide.handoff,
                "watch": guide.watch,
            }
        )
    return render(
        "agents/item_skill.md.j2",
        title=item_type.value.capitalize(),
        type=item_type.value,
        version=PINNED_VERSION,
        overview=pb.overview,
        lifecycle=pb.lifecycle,
        commands=list(pb.commands),
        sections=sections,
    )


# ---------------------------------------------------------------------------
# Tests — one per golden artifact
# ---------------------------------------------------------------------------


class TestWorkflowCheatsheetGolden:
    """Pin the raw rendered markdown from workflow.md.j2.

    TASK-261 will replace this static template output with a spec-derived renderer.
    This test fails if that renderer produces different text for a non-custom squad.
    """

    def test_workflow_cheatsheet_raw_markdown(self) -> None:
        """workflow.md.j2 renders byte-identical output for a non-custom (bundled) squad."""
        actual = _render_workflow_cheatsheet()
        # Sanity: the output must contain the static sections that TASK-261 must preserve.
        assert "## Team workflow" in actual, "static section header missing"
        assert "## Type-command aliases" in actual, "alias table section missing"
        assert "## Retype" in actual, "Retype section missing (stability-contract prose)"
        assert "## Remove vs. Cancel" in actual, "Remove vs Cancel section missing"
        assert "## Ref kinds" in actual, "Ref kinds section missing"
        # No ANSI escape codes should be present (this is raw markdown, not Rich-rendered).
        assert "\x1b[" not in actual, "ANSI escape codes found in raw template output"
        _check_golden("workflow_cheatsheet", actual)


class TestClaudeMdSectionGolden:
    """Pin the rendered CLAUDE.md managed section body (ClaudeCodeBackend path).

    TASK-261 will regenerate this from the live spec.  This test fails if that
    regeneration produces different text for a non-custom squad.
    """

    def test_claude_md_section_body(self) -> None:
        """claude_section.md.j2 renders byte-identical CLAUDE.md section with the pinned roster."""
        actual = _render_claude_section()
        # Sanity: must contain key structural landmarks.
        assert "## Agent roster" in actual, "Agent roster section missing"
        assert "Catherine Manager" in actual, "default role name missing"
        assert "## Orchestration loop" in actual, "Orchestration loop section missing"
        assert "## Team workflow" in actual, "Team workflow section missing"
        assert "Pierre Chat" in actual, "operator name missing"
        assert "op-pierre" in actual, "operator slug missing"
        assert "Elias Python" in actual, "python-dev missing from roster"
        assert "\x1b[" not in actual, "ANSI escape codes found in section render"
        _check_golden("claude_md_section", actual)


class TestAgentsMdSectionGolden:
    """Pin the rendered AGENTS.md managed section body (AgentsMdBackend path).

    TASK-261 will regenerate this from the live spec.  This test fails if that
    regeneration produces different text for a non-custom squad.
    """

    def test_agents_md_section_body(self) -> None:
        """agents_section.md.j2 renders byte-identical AGENTS.md section with the pinned roster."""
        actual = _render_agents_section()
        # Sanity: must contain key structural landmarks.
        assert "## Agent roster" in actual, "Agent roster section missing"
        assert "Catherine Manager" in actual, "manager missing"
        assert "## Team workflow" in actual, "workflow section missing from AGENTS.md"
        assert "## Type-command aliases" in actual, "alias table missing from AGENTS.md"
        assert "Pierre Chat" in actual, "operator missing"
        assert "Elias Python" in actual, "python-dev missing from AGENTS.md section"
        assert "\x1b[" not in actual, "ANSI escape codes found in section render"
        _check_golden("agents_md_section", actual)


class TestItemSkillGoldens:
    """Pin every bundled sq-<type> skill body.

    TASK-260 will regenerate these from the live spec.  Each test fails if the
    rewire produces different output for the corresponding type.
    """

    def _check_skill(self, item_type: Any, *, expect_dev_section: bool = True) -> None:  # type: ignore[explicit-any]
        name = item_skill_name(item_type)
        actual = _render_item_skill(item_type)
        # Sanity checks.
        assert "<!-- squads:managed" in actual, f"{name}: managed comment missing"
        assert f"squads:version:{PINNED_VERSION}" in actual, (
            f"{name}: version stamp missing or wrong (expected {PINNED_VERSION})"
        )
        assert PLAYBOOK[item_type].lifecycle in actual, f"{name}: lifecycle string missing"
        if expect_dev_section:
            assert "## For developers" in actual, (
                f"{name}: developer section missing — is has_dev True? _HAS_DEV={_HAS_DEV}"
            )
        assert "\x1b[" not in actual, f"{name}: ANSI escape codes found"
        _check_golden(f"skill_body_{name}", actual)

    def test_skill_body_sq_epic(self) -> None:
        """sq-epic skill body is byte-identical to the golden (epic has no dev section)."""
        from squads._models._enums import ItemType

        # Epic playbook has no DEV guide — confirm that expectation.
        pb = PLAYBOOK[ItemType.EPIC]
        has_dev_guide = any(g.slug == DEV for g in pb.roles)
        self._check_skill(ItemType.EPIC, expect_dev_section=has_dev_guide)

    def test_skill_body_sq_feature(self) -> None:
        """sq-feature skill body is byte-identical to the golden."""
        from squads._models._enums import ItemType

        pb = PLAYBOOK[ItemType.FEATURE]
        has_dev_guide = any(g.slug == DEV for g in pb.roles)
        self._check_skill(ItemType.FEATURE, expect_dev_section=has_dev_guide)

    def test_skill_body_sq_task(self) -> None:
        """sq-task skill body is byte-identical to the golden (includes developer section)."""
        from squads._models._enums import ItemType

        self._check_skill(ItemType.TASK, expect_dev_section=True)

    def test_skill_body_sq_bug(self) -> None:
        """sq-bug skill body is byte-identical to the golden (includes developer section)."""
        from squads._models._enums import ItemType

        self._check_skill(ItemType.BUG, expect_dev_section=True)

    def test_skill_body_sq_decision(self) -> None:
        """sq-decision skill body is byte-identical to the golden."""
        from squads._models._enums import ItemType

        pb = PLAYBOOK[ItemType.DECISION]
        has_dev_guide = any(g.slug == DEV for g in pb.roles)
        self._check_skill(ItemType.DECISION, expect_dev_section=has_dev_guide)

    def test_skill_body_sq_review(self) -> None:
        """sq-review skill body is byte-identical to the golden."""
        from squads._models._enums import ItemType

        pb = PLAYBOOK[ItemType.REVIEW]
        has_dev_guide = any(g.slug == DEV for g in pb.roles)
        self._check_skill(ItemType.REVIEW, expect_dev_section=has_dev_guide)

    def test_skill_body_sq_guide(self) -> None:
        """sq-guide skill body is byte-identical to the golden."""
        from squads._models._enums import ItemType

        pb = PLAYBOOK[ItemType.GUIDE]
        has_dev_guide = any(g.slug == DEV for g in pb.roles)
        self._check_skill(ItemType.GUIDE, expect_dev_section=has_dev_guide)

    def test_all_managed_item_types_covered(self) -> None:
        """Every type from managed_item_types() has a golden covering its skill body.

        This test fails if a new item type is added to the playbook without a
        corresponding golden test being added here.  Add a new test_skill_body_sq_<type>
        method and run UPDATE_GOLDENS=1 to capture the new type's output.
        """
        from squads._models._enums import ItemType

        # The types this module explicitly tests.
        covered = {
            ItemType.EPIC,
            ItemType.FEATURE,
            ItemType.TASK,
            ItemType.BUG,
            ItemType.DECISION,
            ItemType.REVIEW,
            ItemType.GUIDE,
        }
        managed = set(managed_item_types())
        assert managed == covered, (
            f"managed_item_types() has changed.\n"
            f"Extra in managed (need new golden test): {managed - covered}\n"
            f"Missing from managed (remove stale test): {covered - managed}"
        )


# ---------------------------------------------------------------------------
# Mechanism smoke test
# ---------------------------------------------------------------------------


def test_update_goldens_flag_is_documented() -> None:
    """Confirm the UPDATE_GOLDENS mechanism is in place (non-functional smoke)."""
    assert isinstance(_UPDATE, bool)
