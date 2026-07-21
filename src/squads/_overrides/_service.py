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
import re
from dataclasses import dataclass
from pathlib import Path

from squads import __version__
from squads._errors import SquadsError
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
from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME

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

_SQ_OPEN_RE = re.compile(r"<!--\s*(sq:[a-z0-9][a-z0-9:_-]*)\s*-->")


def _required_markers_from_bundled(template_name: str) -> set[str]:
    """Return the set of ``sq:*`` open-marker tags that the bundled template requires.

    Only matches opening markers (not ``:end`` closers).  Empty set for templates we
    cannot read or that carry no markers.
    """
    content = bundled_template_content(template_name)
    if content is None:
        return set()
    tags: set[str] = set()
    for m in _SQ_OPEN_RE.finditer(content):
        tag = m.group(1)
        if not tag.endswith(":end"):
            tags.add(tag)
    return tags


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

    The workflow override is additive-only (no bundled counterpart to diff against),
    so drift is detected by version stamp alone: stamp < running version → drifted.
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
# Workflow spec override — additive-only extensions to the squads built-in vocabulary.
#
# Rules:
#   - You may ADD new item types, statuses, and lifecycle state machines.
#   - You may NOT redefine (shadow) a built-in type, status, or lifecycle.
#   - A new type may reference a built-in lifecycle (e.g. lifecycle = "work").
#   - Unknown TOML keys are rejected at load time (fail-closed).
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
# terminal = false
#
# [statuses.Mitigating]
# terminal = false
#
# [statuses.Resolved]
# terminal = true
#
# [items.incident]
# prefix = "INC"
# folder = "incidents"
# lifecycle = "incident"
# -----------------------------------------------------------------------------
"""


def scaffold_workflow(squad_dir: Path, *, force: bool = False) -> Path:
    """Create ``.overrides/workflow.toml`` with the stamp comment + a worked example.

    The file is additive-only: it starts from scratch (not a copy of the bundled default)
    and contains only a commented example that the admin can uncomment and extend.
    Raises :class:`SquadsError` if the file already exists and ``--force`` is not set.
    """
    dest = _workflow_override_path(squad_dir)
    if dest.exists() and not force:
        raise SquadsError(f"{WORKFLOW_OVERRIDE_FILENAME} already exists; use --force to overwrite")

    dest.parent.mkdir(parents=True, exist_ok=True)
    stamp_line = f"# squads:override-base:{__version__}\n"
    dest.write_text(stamp_line + _WORKFLOW_SCAFFOLD_BODY, encoding="utf-8")
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

    *kind* is ``"template"``, ``"role"``, or ``"workflow"``.
    Raises :class:`SquadsError` when the override file is not found.
    """
    if kind == "template":
        return _diff_template(squad_dir, name)
    if kind == "role":
        return _diff_role(squad_dir, name)
    if kind == "workflow":
        return _diff_workflow(squad_dir)
    raise SquadsError(f"unknown override kind {kind!r}; expected 'template', 'role', or 'workflow'")


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

    # Δ-mine: override vs empty reference (workflow overrides are additive-only, starting
    # from scratch, so the meaningful diff is "what the team added").
    delta_mine = _unified_diff(
        "",
        override_text,
        fromfile="(empty — workflow overrides are additive-only, starting from scratch)",
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

    return stamped


# ─── check helpers (used by _services/_maintenance.py) ────────────────────────


def check_override_issues(squad_dir: Path) -> list[tuple[str, str, str]]:
    """Return a list of (level, item_path, message) for sq check integration.

    Levels are ``"warn"`` or ``"error"`` (matching CheckIssue).
    *item_path* is the relative path string for display in the sq check output.
    """
    issues: list[tuple[str, str, str]] = []

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

    issues.extend(_check_workflow_override_issues(squad_dir))
    return issues


def _check_workflow_override_issues(squad_dir: Path) -> list[tuple[str, str, str]]:
    """Return check issues for the workflow TOML override (if present)."""
    wf_path = _workflow_override_path(squad_dir)
    if not wf_path.is_file():
        return []

    issues: list[tuple[str, str, str]] = []
    display = WORKFLOW_OVERRIDE_FILENAME
    text = wf_path.read_text(encoding="utf-8")
    stamp = read_toml_stamp(text)
    if stamp is None:
        issues.append(
            (
                "warn",
                display,
                "workflow override has no squads:override-base stamp; "
                "run `sq override update workflow` to re-stamp",
            )
        )
    elif stamp != __version__:
        msg = (
            f"workflow override may be stale: stamp v{stamp} "
            f"predates running v{__version__}; "
            "run `sq override diff workflow` to review, then "
            "`sq override update workflow` to re-stamp"
        )
        issues.append(("warn", display, msg))
    return issues
