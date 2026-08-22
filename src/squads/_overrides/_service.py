"""Service-level logic for the ``sq override`` command group.

Provides:
- :func:`scan_overrides` — enumerate every present override with kind, stamp, and state.
- :func:`scaffold_template` — copy a bundled template into ``.overrides/templates/`` with stamp.
- :func:`scaffold_role` — copy a bundled role (empty TOML) into ``.overrides/roles/`` with stamp.
- :func:`scaffold_new_role` — start a brand-new, non-bundled role TOML with essentials stubbed.
- :func:`scaffold_workflow` — create ``.overrides/workflow.toml`` with stamp + commented example.
- :func:`diff_override` — produce the two-delta comparison (Δ-mine + Δ-upgrade) for one override.
- :func:`update_stamp` — re-stamp one or all structurally-valid overrides to the current version.

All functions raise :class:`~squads._errors.SquadsError` on user-facing problems.

Required-marker contract:
An overridden item template (``items/*.md.j2``) must keep all of the ``<!-- sq:* -->`` marker
regions that the bundled template requires.  The required set per template is derived from the
bundled template itself, not hardcoded, so it automatically tracks future marker additions.
Role templates (``agents/role.md.j2``) must keep ``<!-- sq:body -->`` and
``<!-- sq:discussion -->``.

Only item and role body templates are checked for required markers.  Backend templates (claude/*)
and subentity partials (subentities/*) are not item files and carry no sq-body sections.
"""

import difflib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from squads import __version__
from squads._errors import SquadsError
from squads._interactions._loader import (
    PLAYBOOK_OVERRIDE_FILENAME,
    bundled_playbook_toml_text,
    playbook_stamp_finding,
)
from squads._models._item import Item
from squads._overrides._manifest import (
    base_version_template_content,
    bundled_template_content,
    template_changed_since,
)
from squads._overrides._stamp import (
    read_template_stamp,
    read_toml_stamp,
    stamp_template_file,
    stamp_toml_file,
    write_template_stamp,
)
from squads._rendering._engine import invalidate_squad_dir
from squads._roles._catalog import PREDEFINED
from squads._sections import find_markers
from squads._workflow._loader import (
    WORKFLOW_OVERRIDE_FILENAME,
    bundled_workflow_toml_text,
    workflow_stamp_finding,
)

_BUNDLED_ROLE_SLUGS: frozenset[str] = frozenset(r.slug for r in PREDEFINED)

# ─── Override state ────────────────────────────────────────────────────────────

# Values for OverrideEntry.state (part of the durable contract).
STATE_CURRENT = "current"  # stamp == running version OR bundled counterpart unchanged
STATE_DRIFTED = "drifted"  # stamp < running version AND bundled counterpart changed
STATE_BROKEN = "broken"  # missing a required sq:* marker region


@dataclass
class OverrideEntry:
    """One project override's metadata for ``sq override list``."""

    name: str  # template-relative path (e.g. "items/task.md.j2") or role slug
    kind: str  # "template" or "role"
    base_version: str | None  # from the stamp, or None if unstamped
    state: str  # STATE_CURRENT | STATE_DRIFTED | STATE_BROKEN


@dataclass
class DiffResult:
    """Both deltas for ``sq override diff``."""

    name: str
    kind: str
    delta_mine: str  # unified diff: override vs current bundled (what the team customised)
    delta_upgrade: str  # unified diff: base-version bundled vs current bundled (what upgraded)
    base_version: str | None
    base_available: bool  # False when we couldn't recover the base-version bundled content


# ─── Template overridability: which templates are user-overridable ─────────────

# Only the templates under items/ and agents/role.md.j2 are item/role templates with
# required marker regions.  Backend and subentity partials are scaffoldable but not
# subject to the missing-marker ERROR (they don't carry sq:body sections).
_ITEM_TEMPLATE_PREFIXES = ("items/", "agents/role.md.j2")


def _is_item_or_role_template(name: str) -> bool:
    return any(name == p or name.startswith(p) for p in _ITEM_TEMPLATE_PREFIXES)


# ─── Required marker detection ─────────────────────────────────────────────────


def _required_markers_from_bundled(template_name: str) -> set[str]:
    """Return the set of ``sq:*`` open-marker tags that the bundled template requires.

    Only matches opening markers (not ``:end`` closers).  Empty set for templates we
    cannot read or that carry no markers.

    Goes through :func:`~squads._sections.find_markers` — the one marker-recognition
    primitive — rather than a second regex of its own: the copy that used to live here was a
    verbatim duplicate, so it inherited the lowercase-only tag class that made every
    mixed-case sub-entity marker invisible, and would have had to be found and fixed a second
    time. One definition, one place to widen.
    """
    content = bundled_template_content(template_name)
    if content is None:
        return set()
    return {tag for tag in find_markers(content) if not tag.endswith(":end")}


def _missing_required_markers(template_name: str, override_text: str) -> list[str]:
    """Return marker tags required by the bundled template but absent from *override_text*.

    Only meaningful for item/role templates.
    """
    required = _required_markers_from_bundled(template_name)
    present_raw = find_markers(override_text)  # returns "sq:body", "sq:body:end", …
    present: set[str] = {r for r in present_raw if not r.endswith(":end")}
    missing = sorted(required - present)
    return missing


# ─── Path helpers ──────────────────────────────────────────────────────────────


def _template_overrides_dir(squad_dir: Path) -> Path:
    return squad_dir / ".overrides" / "templates"


def _role_overrides_dir(squad_dir: Path) -> Path:
    return squad_dir / ".overrides" / "roles"


def _workflow_override_path(squad_dir: Path) -> Path:
    return squad_dir / WORKFLOW_OVERRIDE_FILENAME


def _playbook_override_path(squad_dir: Path) -> Path:
    return squad_dir / PLAYBOOK_OVERRIDE_FILENAME


# ─── Determine override state ──────────────────────────────────────────────────


def _template_state(template_name: str, path: Path, text: str) -> str:
    """Classify a template override as current / drifted / broken."""
    # Broken check (independent of version): missing a required marker.
    if _is_item_or_role_template(template_name) and _missing_required_markers(template_name, text):
        return STATE_BROKEN

    stamp = read_template_stamp(text)
    if stamp is None:
        # Unstamped — treat as drifted (no provenance → warn).
        return STATE_DRIFTED

    if stamp == __version__:
        return STATE_CURRENT

    # Check whether the bundled counterpart actually changed since the stamp.
    if template_changed_since(template_name, stamp):
        return STATE_DRIFTED
    return STATE_CURRENT


def _role_state(slug: str, path: Path, text: str) -> str:
    """Classify a role TOML override as current / drifted.

    Role TOML overrides are never 'broken' in the marker sense (TOML has no sq markers).
    """
    stamp = read_toml_stamp(text)
    if stamp is None:
        return STATE_DRIFTED

    if stamp == __version__:
        return STATE_CURRENT

    # Check role-template drift (the role body shape, agents/role.md.j2).
    if template_changed_since("agents/role.md.j2", stamp):
        return STATE_DRIFTED
    return STATE_CURRENT


def _workflow_state(text: str) -> str:
    """Classify the workflow TOML override as current / drifted.

    An unstamped file has by definition not been reconciled against any bundled version, so
    it is classified not-current (drifted) regardless of whether it shadows or only adds —
    that distinction drives the separate stamp-obligation *finding* in
    :func:`_check_workflow_override_issues`, not this state. Drift is detected by
    version stamp alone: there is no per-release content-hash for the workflow TOML in the
    manifest, so this never compares content the way a template override's drift check does.
    TOML has no sq markers, so a workflow override is never 'broken' in the marker sense.
    """
    stamp = read_toml_stamp(text)
    if stamp is None:
        return STATE_DRIFTED
    if stamp == __version__:
        return STATE_CURRENT
    # For v1 simplicity: any stamp older than the running version is drifted.
    # (No per-release content-hash for the workflow TOML in the manifest yet.)
    return STATE_DRIFTED


def _playbook_state(text: str) -> str:
    """Classify the playbook TOML override as current / drifted — mirrors
    :func:`_workflow_state` exactly (same three-state, stamp-only contract; no per-release
    content-hash for the playbook TOML either). TOML has no sq markers, so a playbook override
    is never 'broken' in the marker sense."""
    stamp = read_toml_stamp(text)
    if stamp is None:
        return STATE_DRIFTED
    if stamp == __version__:
        return STATE_CURRENT
    return STATE_DRIFTED


# ─── scan_overrides ────────────────────────────────────────────────────────────


def scan_overrides(squad_dir: Path) -> list[OverrideEntry]:
    """Enumerate every override under ``.overrides/``, returning one entry per file."""
    entries: list[OverrideEntry] = []

    # Template overrides
    tmpl_dir = _template_overrides_dir(squad_dir)
    if tmpl_dir.is_dir():
        for path in sorted(tmpl_dir.rglob("*.md.j2")):
            rel = path.relative_to(tmpl_dir).as_posix()
            text = path.read_text(encoding="utf-8")
            stamp = read_template_stamp(text)
            state = _template_state(rel, path, text)
            entries.append(
                OverrideEntry(name=rel, kind="template", base_version=stamp, state=state)
            )

    # Role TOML overrides
    role_dir = _role_overrides_dir(squad_dir)
    if role_dir.is_dir():
        for path in sorted(role_dir.glob("*.toml")):
            slug = path.stem
            text = path.read_text(encoding="utf-8")
            stamp = read_toml_stamp(text)
            state = _role_state(slug, path, text)
            entries.append(OverrideEntry(name=slug, kind="role", base_version=stamp, state=state))

    # Workflow TOML override (single file, not a directory)
    wf_path = _workflow_override_path(squad_dir)
    if wf_path.is_file():
        text = wf_path.read_text(encoding="utf-8")
        stamp = read_toml_stamp(text)
        state = _workflow_state(text)
        entries.append(
            OverrideEntry(name="workflow", kind="workflow", base_version=stamp, state=state)
        )

    # Playbook TOML override (single file, not a directory)
    pb_path = _playbook_override_path(squad_dir)
    if pb_path.is_file():
        text = pb_path.read_text(encoding="utf-8")
        stamp = read_toml_stamp(text)
        state = _playbook_state(text)
        entries.append(
            OverrideEntry(name="playbook", kind="playbook", base_version=stamp, state=state)
        )

    return entries


# ─── scaffold_template ─────────────────────────────────────────────────────────


def scaffold_template(squad_dir: Path, template_name: str, *, force: bool = False) -> Path:
    """Copy *template_name* from the bundle into ``.overrides/templates/``, stamped.

    Returns the path of the created override file.
    Raises :class:`SquadsError` if the template is unknown or exists and ``--force`` is not set.
    """
    bundled = bundled_template_content(template_name)
    if bundled is None:
        raise SquadsError(
            f"no bundled template {template_name!r} — "
            "use a path like 'items/task.md.j2' or 'agents/role.md.j2'"
        )

    dest = _template_overrides_dir(squad_dir) / template_name
    if dest.exists() and not force:
        raise SquadsError(
            f".overrides/templates/{template_name} already exists; use --force to overwrite"
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    # Write bundled content first, then add the stamp as the first line.
    stamped = write_template_stamp(bundled, __version__)
    dest.write_text(stamped, encoding="utf-8")

    # The engine caches the environment per squad dir — invalidate so the new file is picked up.
    invalidate_squad_dir(squad_dir)

    return dest


# ─── role slug safety ──────────────────────────────────────────────────────────


def _validate_role_slug(squad_dir: Path, slug: str) -> Path:
    """Validate *slug* is safe as a ``.overrides/roles/<slug>.toml`` filename component.

    Rejects an empty/whitespace slug, or one containing a path separator, a leading dot, or a
    ``..`` traversal segment. As a backstop (mirroring ``_paths.SquadPaths.abspath``'s traversal
    guard), also rejects a slug whose resolved destination would land outside
    ``.overrides/roles/`` — catching anything the syntax checks above didn't anticipate.

    Returns the (unresolved) destination path on success; raises :class:`SquadsError` otherwise.
    """
    if not slug.strip():
        raise SquadsError("role slug must not be empty or whitespace")
    if "/" in slug or "\\" in slug or ".." in slug or slug.startswith("."):
        raise SquadsError(
            f"invalid role slug {slug!r}: must not contain a path separator, '..', "
            "or start with '.'"
        )

    role_dir = _role_overrides_dir(squad_dir)
    dest = role_dir / f"{slug}.toml"
    if not dest.resolve().is_relative_to(role_dir.resolve()):
        raise SquadsError(f"invalid role slug {slug!r}: escapes .overrides/roles/")
    return dest


# ─── scaffold_role ─────────────────────────────────────────────────────────────


def scaffold_role(squad_dir: Path, slug: str, *, force: bool = False) -> Path:
    """Create ``.overrides/roles/<slug>.toml`` with the stamp comment.

    The TOML starts empty (only the stamp) — teams add fields they want to override.
    Raises :class:`SquadsError` if *slug* is unsafe, or the file exists and ``--force`` is not set.
    """
    dest = _validate_role_slug(squad_dir, slug)
    if dest.exists() and not force:
        raise SquadsError(f".overrides/roles/{slug}.toml already exists; use --force to overwrite")

    dest.parent.mkdir(parents=True, exist_ok=True)
    stamp_line = f"# squads:override-base:{__version__}\n"
    desc = f"# Role override for '{slug}'. Add fields to override (e.g. full_name, model).\n"
    dest.write_text(stamp_line + desc, encoding="utf-8")
    return dest


# ─── scaffold_new_role ─────────────────────────────────────────────────────────

#: Starter body for a brand-new (non-bundled) custom role — essentials active, advanced commented.
_NEW_ROLE_SCAFFOLD_TPL = """\
# Role override for '{slug}' — defines a brand-new custom role (not in the bundled catalog).
#
# Fill in the essentials below, then activate it with: sq role activate {slug}
# See docs/roles.md and docs/overrides.md for the full field reference.

full_name = "TODO: full name (e.g. \\"Sam Security\\")"
title = "TODO: one-line title (e.g. \\"security analyst\\")"
description = "TODO: one-line description for the Claude pointer frontmatter"
mission = "TODO: what this role is responsible for accomplishing"

# Advanced fields (optional) — uncomment and edit to set:
# responsibilities = ["First responsibility", "Second responsibility"]
# agreements = ["A team agreement this role follows"]
# model = "sonnet"  # sonnet | opus | haiku | inherit (omit to inherit the project default)
# color = "teal"
{can_spawn_line}
"""

_CAN_SPAWN_COMMENTED = (
    "# can_spawn = false  # true grants this role the ability to spawn/orchestrate subagents"
)
_CAN_SPAWN_ACTIVE = (
    "can_spawn = true  # grants this role the ability to spawn/orchestrate subagents"
)


def scaffold_new_role(
    squad_dir: Path, slug: str, *, force: bool = False, can_spawn: bool = False
) -> Path:
    """Create ``.overrides/roles/<slug>.toml`` defining a wholly new, non-bundled role.

    *slug* must not collide with a bundled role (use :func:`scaffold_role` / ``--role`` for that).
    The essential fields the resolver requires for a new-slug role (``full_name``, ``title``,
    ``description``, ``mission``) are pre-stubbed as active keys with fill-in placeholders;
    the advanced fields (``responsibilities``, ``agreements``, ``model``, ``color``, ``can_spawn``)
    are included commented out. Pass ``can_spawn=True`` to emit ``can_spawn = true`` active instead.

    Raises :class:`SquadsError` if *slug* is unsafe or a bundled role, or the file exists without
    ``--force``.
    """
    dest = _validate_role_slug(squad_dir, slug)
    if slug in _BUNDLED_ROLE_SLUGS:
        raise SquadsError(
            f"{slug!r} is a bundled role; use `sq override scaffold --role {slug}` to override it "
            "(--new is for a brand-new, non-bundled role slug)"
        )

    if dest.exists() and not force:
        raise SquadsError(f".overrides/roles/{slug}.toml already exists; use --force to overwrite")

    dest.parent.mkdir(parents=True, exist_ok=True)
    stamp_line = f"# squads:override-base:{__version__}\n"
    can_spawn_line = _CAN_SPAWN_ACTIVE if can_spawn else _CAN_SPAWN_COMMENTED
    body = _NEW_ROLE_SCAFFOLD_TPL.format(slug=slug, can_spawn_line=can_spawn_line)
    dest.write_text(stamp_line + body, encoding="utf-8")
    return dest


# ─── scaffold_workflow ─────────────────────────────────────────────────────────

#: Starter content for a scaffolded workflow override — stamp + commented example.
_WORKFLOW_SCAFFOLD_BODY = """\
# Workflow spec override — shadow or extend the squads built-in vocabulary.
#
# Rules:
#   - Add new item types, statuses, and lifecycle state machines.
#   - Shadow (redefine one field of, or wholesale replace) a built-in type, status, or
#     lifecycle — the field you write replaces its bundled counterpart; every other field
#     is inherited unchanged.
#   - Drop a built-in via a top-level [selected] table (e.g. selected.items = [...] to keep
#     only the listed item types).
#   - The three roster type keys (role, skill, operator) are locked: they can't be added,
#     dropped, or claimed by another type's category.
#   - A new type may reference a built-in lifecycle (e.g. lifecycle = "work").
#   - Unknown top-level/[selected] keys are rejected at load time (fail-closed).
#
# Every status names a `role` — the single source of its settled/hidden/colour behaviour.
# The built-in roles are: pending, active, attention, blocked, in_force, done, retired,
# superseded (`sq workflow roles` lists them with their flags). A status with no `role`
# falls back to `pending`, so it stays visible until you assign one.
#
# Validate with: sq workflow lint
# See state after editing: sq override diff workflow
# Re-stamp after merging: sq override update workflow
#
# --- Worked example (uncomment and edit to activate) -------------------------
#
# [lifecycles.incident]
# # Custom lifecycle: Triage → Mitigating → Resolved (+ Cancelled)
# initial = "Triage"
#
# [lifecycles.incident.transitions]
# Triage = ["Mitigating", "Cancelled"]
# Mitigating = ["Resolved", "Triage", "Cancelled"]
# Resolved = ["Triage"]
# Cancelled = ["Triage"]
#
# [statuses.Triage]
# role = "pending"    # not settled, not hidden — an open incident awaiting triage
#
# [statuses.Mitigating]
# role = "active"     # not settled — work in flight
#
# [statuses.Resolved]
# role = "done"       # settled and hidden from the default list view
#
# [items.incident]
# prefix = "INC"
# folder = "incidents"
# lifecycle = "incident"
# -----------------------------------------------------------------------------
"""


def scaffold_workflow(squad_dir: Path, *, force: bool = False) -> Path:
    """Create ``.overrides/workflow.toml`` with the stamp comment + a worked example.

    The scaffolded file starts from scratch (not a copy of the bundled default) and contains
    only a commented example the admin can uncomment and extend — but the override it primes
    can shadow, not just add: a hand-written key replaces its bundled counterpart, and
    ``[selected]`` drops one by name. Raises :class:`SquadsError` if the file
    already exists and ``--force`` is not set.
    """
    dest = _workflow_override_path(squad_dir)
    if dest.exists() and not force:
        raise SquadsError(f"{WORKFLOW_OVERRIDE_FILENAME} already exists; use --force to overwrite")

    dest.parent.mkdir(parents=True, exist_ok=True)
    stamp_line = f"# squads:override-base:{__version__}\n"
    dest.write_text(stamp_line + _WORKFLOW_SCAFFOLD_BODY, encoding="utf-8")
    return dest


# ─── scaffold_playbook ──────────────────────────────────────────────────────────

#: Starter content for a scaffolded playbook override — stamp + the one worked example the
#: playbook override exists for: the one-line append idiom.
_PLAYBOOK_SCAFFOLD_BODY = """\
# Playbook spec override — add role guidance to a type's entry, or shadow a bundled one.
#
# Rules:
#   - One entry per non-roster type declared in the (possibly workflow-overridden) active spec
#     — coverage is DERIVED, never independently declared: dropping a type via
#     .overrides/workflow.toml's [selected] drops its playbook coverage requirement too, with
#     no [selected] key here (none exists for this document).
#   - A type entry's SCALAR fields (overview, lifecycle, commands) merge field-by-field: write
#     only the one you want to change, every other field of that entry is inherited unchanged.
#   - `roles` is a LIST, not a per-guide merge — writing it replaces the type's whole roles
#     array. The one-line append idiom, `roles = ["$(*self)", { slug = "my-role", ... }]`,
#     spreads the bundled array first so you keep every existing guide and ADD one — it does
#     not edit an existing guide's fields, and must be TOML's inline-array form (the
#     [[types.<t>.roles]] header form has no slot for the "$(*self)" token). Changing one field
#     of one bundled guide, or replacing it outright, is not expressible without restating the
#     whole array by hand (omit "$(*self)" and list every guide you want to keep).
#   - A slug must not appear twice in one type's roles array — roles is keyed by slug (the
#     generated skill renders one section per slug), so a repeat is rejected at load time, not
#     merged or rendered twice.
#   - Every role slug must be one of: a bundled catalog role, the "*dev" sentinel (matching any
#     <tech>-dev role), or a project role you have defined under .overrides/roles/<slug>.toml.
#     A project role must also be ACTIVATED (`sq role activate <slug>`) for its guidance to
#     reach the generated skill — a guide whose slug names no live role loads fine but is
#     dropped from the skill, and `sq check` warns about it until you activate the role or
#     remove the guide.
#   - `authors = true` on a guide declares that role an in-lane AUTHOR of the type the guide
#     hangs under. It is the sole source of the advisory create-lane: `sq create <type>` warns
#     when the declared author has no `authors = true` guide on that type. Omit it (the default)
#     for a role that only reads, triages, or verifies the type.
#   - Unknown top-level keys are rejected at load time (fail-closed); there is no [selected]
#     table for this document — see the coverage rule above.
#
# See the state of this file with: sq override diff playbook
# Re-stamp after merging:          sq override update playbook
#
# In the example below, the first entry appends a guide; the second appends one that also
# claims the type's create-lane, so `sq create bug --author devops` stops warning.
#
# --- Worked example (uncomment and edit to activate) -------------------------
#
# [types.task]
# roles = [
#     "$(*self)",
#     { slug = "architect", enter = ["Confirm the design holds"], do = ["Flag any deviation"] },
# ]
#
# [types.bug]
# roles = [
#     "$(*self)",
#     { slug = "devops", authors = true, do = ["File the incident as a bug"] },
# ]
# -----------------------------------------------------------------------------
"""


def scaffold_playbook(squad_dir: Path, *, force: bool = False) -> Path:
    """Create ``.overrides/playbook.toml`` with the stamp comment + a worked example.

    Mirrors :func:`scaffold_workflow`: starts from scratch (not a copy of the bundled default)
    and contains only a commented example — the one-line append idiom, since that is the
    mechanism this override kind exists for. Raises :class:`SquadsError` if the file already
    exists and ``--force`` is not set.
    """
    dest = _playbook_override_path(squad_dir)
    if dest.exists() and not force:
        raise SquadsError(f"{PLAYBOOK_OVERRIDE_FILENAME} already exists; use --force to overwrite")

    dest.parent.mkdir(parents=True, exist_ok=True)
    stamp_line = f"# squads:override-base:{__version__}\n"
    dest.write_text(stamp_line + _PLAYBOOK_SCAFFOLD_BODY, encoding="utf-8")
    return dest


# ─── diff_override ─────────────────────────────────────────────────────────────


def _unified_diff(a: str, b: str, fromfile: str, tofile: str) -> str:
    """Return a unified diff string (empty if no difference)."""
    a_lines = a.splitlines(keepends=True)
    b_lines = b.splitlines(keepends=True)
    lines = list(difflib.unified_diff(a_lines, b_lines, fromfile=fromfile, tofile=tofile))
    return "".join(lines)


def diff_override(squad_dir: Path, name: str, kind: str) -> DiffResult:
    """Compute both diffs for one override.

    *kind* is ``"template"``, ``"role"``, ``"workflow"``, or ``"playbook"``.
    Raises :class:`SquadsError` when the override file is not found.
    """
    if kind == "template":
        return _diff_template(squad_dir, name)
    if kind == "role":
        return _diff_role(squad_dir, name)
    if kind == "workflow":
        return _diff_workflow(squad_dir)
    if kind == "playbook":
        return _diff_playbook(squad_dir)
    raise SquadsError(
        f"unknown override kind {kind!r}; expected 'template', 'role', 'workflow', or 'playbook'"
    )


def _diff_template(squad_dir: Path, template_name: str) -> DiffResult:
    path = _template_overrides_dir(squad_dir) / template_name
    if not path.exists():
        raise SquadsError(
            f"no template override for {template_name!r} "
            f"(run `sq override scaffold {template_name}` first)"
        )

    override_text = path.read_text(encoding="utf-8")
    base_version = read_template_stamp(override_text)

    current_bundled = bundled_template_content(template_name) or ""

    # Δ-mine: override vs current bundled (what the team customised from today's default).
    delta_mine = _unified_diff(
        current_bundled,
        override_text,
        fromfile=f"bundled/{template_name}",
        tofile=f".overrides/templates/{template_name}",
    )

    # Δ-upgrade: base-version bundled vs current bundled (what the upgrade changed).
    base_available = False
    delta_upgrade = ""
    if base_version is not None:
        base_content = base_version_template_content(template_name, base_version)
        if base_content is not None:
            base_available = True
            delta_upgrade = _unified_diff(
                base_content,
                current_bundled,
                fromfile=f"bundled/{template_name}@v{base_version}",
                tofile=f"bundled/{template_name} (current)",
            )
        else:
            delta_upgrade = (
                f"(cannot recover bundled {template_name} at v{base_version} — "
                "content changed but base snapshot is not available; "
                "refer to the squads changelog or git history)"
            )

    return DiffResult(
        name=template_name,
        kind="template",
        delta_mine=delta_mine,
        delta_upgrade=delta_upgrade,
        base_version=base_version,
        base_available=base_available,
    )


def _diff_role(squad_dir: Path, slug: str) -> DiffResult:
    path = _role_overrides_dir(squad_dir) / f"{slug}.toml"
    if not path.exists():
        raise SquadsError(
            f"no role override for {slug!r} (run `sq override scaffold --role {slug}` first)"
        )

    override_text = path.read_text(encoding="utf-8")
    base_version = read_toml_stamp(override_text)

    # For roles, Δ-mine is the TOML content vs an empty reference (roles start from empty).
    delta_mine = _unified_diff(
        "",
        override_text,
        fromfile="(empty — role overrides start from scratch)",
        tofile=f".overrides/roles/{slug}.toml",
    )

    # Δ-upgrade for roles: whether the role body template (agents/role.md.j2) changed.
    delta_upgrade = ""
    base_available = False
    if base_version is not None:
        changed = template_changed_since("agents/role.md.j2", base_version)
        if changed:
            base_content = base_version_template_content("agents/role.md.j2", base_version)
            current_bundled = bundled_template_content("agents/role.md.j2") or ""
            if base_content is not None:
                base_available = True
                delta_upgrade = _unified_diff(
                    base_content,
                    current_bundled,
                    fromfile=f"bundled/agents/role.md.j2@v{base_version}",
                    tofile="bundled/agents/role.md.j2 (current)",
                )
            else:
                delta_upgrade = (
                    f"(role body template changed since v{base_version} "
                    "but base snapshot is not available; "
                    "review the squads changelog for role template changes)"
                )
        else:
            delta_upgrade = "(role body template unchanged since base version)"
            base_available = True

    return DiffResult(
        name=slug,
        kind="role",
        delta_mine=delta_mine,
        delta_upgrade=delta_upgrade,
        base_version=base_version,
        base_available=base_available,
    )


def _diff_workflow(squad_dir: Path) -> DiffResult:
    path = _workflow_override_path(squad_dir)
    if not path.exists():
        raise SquadsError("no workflow override found (run `sq override scaffold workflow` first)")

    override_text = path.read_text(encoding="utf-8")
    base_version = read_toml_stamp(override_text)

    # Δ-mine: override vs the bundled workflow.toml — now that the override can shadow, an
    # empty reference would describe only "what the team added" and say nothing about a
    # shadowed field, which is exactly the kind of change this diff exists to show.
    delta_mine = _unified_diff(
        bundled_workflow_toml_text(),
        override_text,
        fromfile="bundled/workflow.toml",
        tofile=WORKFLOW_OVERRIDE_FILENAME,
    )

    # Δ-upgrade: for v1 simplicity, compare stamp version to running version.
    # (No per-release content-hash for the workflow TOML in the manifest yet.)
    delta_upgrade = ""
    base_available = True
    if base_version is None:
        delta_upgrade = (
            "(no stamp — run `sq override update workflow` to stamp the current version)"
        )
        base_available = False
    elif base_version != __version__:
        delta_upgrade = (
            f"(stamp v{base_version} → running v{__version__}; "
            "review the squads changelog for workflow spec changes, "
            "then run `sq override update workflow` to re-stamp)"
        )
    else:
        delta_upgrade = "(stamp matches running version — no upgrade delta)"

    return DiffResult(
        name="workflow",
        kind="workflow",
        delta_mine=delta_mine,
        delta_upgrade=delta_upgrade,
        base_version=base_version,
        base_available=base_available,
    )


def _diff_playbook(squad_dir: Path) -> DiffResult:
    """Mirrors :func:`_diff_workflow` exactly — same Δ-mine-against-bundled,
    Δ-upgrade-by-stamp-comparison shape, no per-release content-hash for this document either."""
    path = _playbook_override_path(squad_dir)
    if not path.exists():
        raise SquadsError("no playbook override found (run `sq override scaffold playbook` first)")

    override_text = path.read_text(encoding="utf-8")
    base_version = read_toml_stamp(override_text)

    delta_mine = _unified_diff(
        bundled_playbook_toml_text(),
        override_text,
        fromfile="bundled/playbook.toml",
        tofile=PLAYBOOK_OVERRIDE_FILENAME,
    )

    delta_upgrade = ""
    base_available = True
    if base_version is None:
        delta_upgrade = (
            "(no stamp — run `sq override update playbook` to stamp the current version)"
        )
        base_available = False
    elif base_version != __version__:
        delta_upgrade = (
            f"(stamp v{base_version} → running v{__version__}; "
            "review the squads changelog for playbook changes, "
            "then run `sq override update playbook` to re-stamp)"
        )
    else:
        delta_upgrade = "(stamp matches running version — no upgrade delta)"

    return DiffResult(
        name="playbook",
        kind="playbook",
        delta_mine=delta_mine,
        delta_upgrade=delta_upgrade,
        base_version=base_version,
        base_available=base_available,
    )


# ─── update_stamp ─────────────────────────────────────────────────────────────


def update_stamp(squad_dir: Path, name: str | None, kind: str | None) -> list[str]:
    """Re-stamp one or all structurally-valid overrides to the current version.

    Returns the list of names that were re-stamped.
    Never rewrites the override body — only the stamp line changes.

    When *name* is ``None`` (bulk mode), all structurally-valid overrides are re-stamped.
    *kind* is required when *name* is provided (``"template"`` or ``"role"``).
    """
    if name is not None:
        return _update_one(squad_dir, name, kind)
    return _update_all(squad_dir)


def _update_one(squad_dir: Path, name: str, kind: str | None) -> list[str]:
    """Re-stamp a single named override; raise SquadsError if it's broken or absent."""
    if kind == "workflow":
        path = _workflow_override_path(squad_dir)
        if path.exists():
            stamp_toml_file(path, __version__)
            return ["workflow"]
        raise SquadsError("no workflow override found. Run `sq override scaffold workflow` first.")
    if kind == "playbook":
        path = _playbook_override_path(squad_dir)
        if path.exists():
            stamp_toml_file(path, __version__)
            return ["playbook"]
        raise SquadsError("no playbook override found. Run `sq override scaffold playbook` first.")
    if kind == "template" or kind is None:
        path = _template_overrides_dir(squad_dir) / name
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if _is_item_or_role_template(name) and _missing_required_markers(name, text):
                raise SquadsError(
                    f"cannot re-stamp {name!r}: override is missing required sq markers. "
                    "Fix the marker structure first, then run `sq override update`."
                )
            stamp_template_file(path, __version__)
            return [name]
    if kind == "role":
        path = _role_overrides_dir(squad_dir) / f"{name}.toml"
        if path.exists():
            stamp_toml_file(path, __version__)
            return [name]
    raise SquadsError(
        f"no override found for {name!r} (kind={kind!r}). "
        "Run `sq override list` to see existing overrides."
    )


def _update_all(squad_dir: Path) -> list[str]:
    """Re-stamp every structurally-valid override; skip broken ones."""
    stamped: list[str] = []

    tmpl_dir = _template_overrides_dir(squad_dir)
    if tmpl_dir.is_dir():
        for path in sorted(tmpl_dir.rglob("*.md.j2")):
            rel = path.relative_to(tmpl_dir).as_posix()
            text = path.read_text(encoding="utf-8")
            if _is_item_or_role_template(rel) and _missing_required_markers(rel, text):
                continue  # Skip broken overrides silently in bulk mode
            stamp_template_file(path, __version__)
            stamped.append(rel)

    role_dir = _role_overrides_dir(squad_dir)
    if role_dir.is_dir():
        for path in sorted(role_dir.glob("*.toml")):
            stamp_toml_file(path, __version__)
            stamped.append(path.stem)

    # Workflow TOML override (single file)
    wf_path = _workflow_override_path(squad_dir)
    if wf_path.is_file():
        stamp_toml_file(wf_path, __version__)
        stamped.append("workflow")

    # Playbook TOML override (single file)
    pb_path = _playbook_override_path(squad_dir)
    if pb_path.is_file():
        stamp_toml_file(pb_path, __version__)
        stamped.append("playbook")

    return stamped


# ─── check helpers (used by _services/_maintenance.py) ────────────────────────


def check_override_issues(
    squad_dir: Path, role_items_by_slug: Mapping[str, Item] | None = None
) -> list[tuple[str, str, str]]:
    """Return a list of (level, item_path, message) for sq check integration.

    Levels are ``"warn"`` or ``"error"`` (matching CheckIssue).
    *item_path* is the relative path string for display in the sq check output.

    *role_items_by_slug* — the live roster's ``ROLE`` items, keyed by ``extra.slug`` — lets a
    role override resolve against its own live identity, bundled or developer alike (see
    :func:`~squads._roles._resolver.role_base_from_item`), instead of the developer case alone
    regenerating a pool name. Omitted (or a slug with no entry) falls back to
    :func:`~squads._roles._resolver.dev_base_for_slug`, which is exactly right for a
    ``<tech>-dev.toml`` with no matching roster entry — this function has no roster of its own
    to load, so the caller (``Service.check``, which already has the index in hand) supplies it.
    """
    issues: list[tuple[str, str, str]] = []
    role_items_by_slug = role_items_by_slug or {}

    # Template overrides
    tmpl_dir = _template_overrides_dir(squad_dir)
    if tmpl_dir.is_dir():
        for path in sorted(tmpl_dir.rglob("*.md.j2")):
            rel = path.relative_to(tmpl_dir).as_posix()
            display = f".overrides/templates/{rel}"
            text = path.read_text(encoding="utf-8")

            # Error: missing required markers (structural breakage).
            if _is_item_or_role_template(rel):
                missing = _missing_required_markers(rel, text)
                if missing:
                    tags = ", ".join(f"<!-- sq:{t} -->" for t in missing)
                    issues.append(
                        (
                            "error",
                            display,
                            f"override is missing required sq marker(s): {tags} "
                            "(breaks marker-safe editing; add the missing regions)",
                        )
                    )
                    continue  # Broken → don't also warn about drift

            # Warn: version drift (stamp present, bundled counterpart changed).
            stamp = read_template_stamp(text)
            if stamp is None:
                # Unstamped → warn (scaffold adds a stamp; manually-placed files may lack one).
                issues.append(
                    (
                        "warn",
                        display,
                        "override has no squads:override-base stamp; "
                        "run `sq override scaffold --force` to re-scaffold with a stamp, "
                        "or `sq override update` after verifying the content",
                    )
                )
            elif stamp != __version__ and template_changed_since(rel, stamp):
                issues.append(
                    (
                        "warn",
                        display,
                        f"override may be stale: bundled {rel} changed since v{stamp}; "
                        f"run `sq override diff {rel}`, merge, then `sq override update {rel}`",
                    )
                )

    # Role TOML overrides
    role_dir = _role_overrides_dir(squad_dir)
    if role_dir.is_dir():
        for path in sorted(role_dir.glob("*.toml")):
            slug = path.stem
            display = f".overrides/roles/{slug}.toml"
            text = path.read_text(encoding="utf-8")
            stamp = read_toml_stamp(text)
            if stamp is None:
                issues.append(
                    (
                        "warn",
                        display,
                        "role override has no squads:override-base stamp; "
                        "run `sq override update` to re-stamp",
                    )
                )
            elif stamp != __version__ and template_changed_since("agents/role.md.j2", stamp):
                issues.append(
                    (
                        "warn",
                        display,
                        f"role override may be stale: role body template changed since v{stamp}; "
                        f"run `sq override diff --role {slug}`, merge, then "
                        f"`sq override update --role {slug}`",
                    )
                )
            issues.extend(
                _check_role_override_resolves(squad_dir, slug, display, role_items_by_slug)
            )

    issues.extend(_check_workflow_override_issues(squad_dir))
    issues.extend(_check_playbook_override_issues(squad_dir))
    return issues


def _check_role_override_resolves(
    squad_dir: Path, slug: str, display: str, role_items_by_slug: Mapping[str, Item]
) -> list[tuple[str, str, str]]:
    """Report a role override that the surfaces which consume it refuse to load.

    A role override is refusable — an unknown key, a wrong type, a model outside the closed
    vocabulary, a ``slug`` disagreeing with the filename. That refusal reaches ``sq sync`` and
    ``sq role <slug> show``, both at exit 1, and reached nothing else: role overrides resolve
    lazily at the point of use, so no reporter's path ever loaded one. A squad could sit at
    ``sq check`` "no issues" while ``sq sync`` was impossible — and ``sq check`` is the gate an
    adopter's CI runs, the surface whose whole job is finding that state before the command
    that needs it does.

    The workflow and playbook overrides are each reported this way already (their loaders run
    on ``open_service``'s path, so ``sq check`` rewraps the failure into its own issue). This
    is the same statement for the one document class that had no reporter at all.

    Deliberately resolved through ``resolve_role_with_base`` — the exact seam ``sq sync``'s
    catalog refresh and ``sq role <slug> show`` both go through — rather than a re-implemented
    validation, so the report can never claim a refusal the consumers do not make, or miss one
    they do. A slug with a roster item gets the same base those two consumers would build
    (:func:`~squads._roles._resolver.role_base_from_item` — a stored fact, whether the item is a
    developer or a bundled role, for exactly the fields an operator can set on it), the
    generated pool name (:func:`~squads._roles._resolver.dev_base_for_slug`) only for a
    ``<tech>-dev`` slug with no roster item. ``RoleNotFoundError`` is unreachable here (the file
    exists, so resolution always takes the override branch) and needs no separate arm.

    Every override file is resolved, not only the slugs the roster carries: ``sq role <slug>
    show`` reads one for a bundled role that was never activated, so scoping to live roles
    would leave a refusable file unreported on the one surface that can still reach it. Hence
    the message names when each consumer refuses rather than asserting both do.
    """
    from squads._interactions import is_dev_slug
    from squads._roles._resolver import (
        dev_base_for_slug,
        resolve_role_with_base,
        role_base_from_item,
    )

    item = role_items_by_slug.get(slug)
    if item is not None:
        base_role = role_base_from_item(item)
    else:
        base_role = dev_base_for_slug(slug) if is_dev_slug(slug) else None

    try:
        resolve_role_with_base(slug, squad_dir, base=base_role)
    except SquadsError as exc:
        return [
            (
                "error",
                display,
                f"role override does not load: {exc} — `sq role {slug} show` refuses now, "
                f"and `sq sync` does too once {slug} is on the roster",
            )
        ]
    return []


def _check_workflow_override_issues(squad_dir: Path) -> list[tuple[str, str, str]]:
    """Return check issues for the workflow TOML override (if present).

    The stamp obligation itself is decided by :func:`workflow_stamp_finding` — shared with
    ``sq workflow lint`` so the two never disagree about the same file: an
    error-level finding when the override shadows a bundled key and carries no stamp, the
    existing warn-level drift finding when a stamp predates the running version, and nothing
    for an add-only override with no stamp.
    """
    wf_path = _workflow_override_path(squad_dir)
    if not wf_path.is_file():
        return []

    display = WORKFLOW_OVERRIDE_FILENAME
    text = wf_path.read_text(encoding="utf-8")
    stamp = read_toml_stamp(text)
    finding = workflow_stamp_finding(squad_dir, stamp)
    if finding is None:
        return []
    level, message = finding
    return [(level, display, message)]


def _check_playbook_override_issues(squad_dir: Path) -> list[tuple[str, str, str]]:
    """Return check issues for the playbook TOML override (if present) — mirrors
    :func:`_check_workflow_override_issues` exactly, sharing the same stamp-obligation
    decision shape via :func:`playbook_stamp_finding`."""
    pb_path = _playbook_override_path(squad_dir)
    if not pb_path.is_file():
        return []

    display = PLAYBOOK_OVERRIDE_FILENAME
    text = pb_path.read_text(encoding="utf-8")
    stamp = read_toml_stamp(text)
    finding = playbook_stamp_finding(squad_dir, stamp)
    if finding is None:
        return []
    level, message = finding
    return [(level, display, message)]
