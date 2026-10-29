"""Service-level logic for the ``sq override`` command group: :func:`scan_overrides` (every present
override with kind, stamp and state), :func:`scaffold_template`, :func:`scaffold_role` and
:func:`scaffold_workflow` (stamped scaffolds under ``.overrides/``), :func:`diff_override` (the
Δ-mine and Δ-upgrade comparison) and :func:`update_stamp` (re-stamp structurally valid overrides).
User-facing problems raise :class:`~squads._errors.SquadsError`.

Required-marker contract: an overridden item template (``items/*.md.j2``) must keep every ``<!--
sq:* -->`` region the bundled template requires, derived from the bundled template so it tracks
marker additions, and a role template (``agents/role.md.j2``) must keep ``sq:body`` and
``sq:discussion``. Backend templates (``claude/*``) and sub-entity partials (``subentities/*``) are
not item files and are not checked.
"""

import difflib
import json
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from squads import __version__
from squads._errors import RoleNotFoundError, SquadsError
from squads._interactions._loader import (
    PLAYBOOK_OVERRIDE_FILENAME,
    PLAYBOOK_OVERRIDE_MESSAGES,
    bundled_playbook_toml_text,
    playbook_stamp_finding,
)
from squads._models import _attributes as attrs
from squads._models import _markers as markers
from squads._models._item import Item
from squads._overrides._manifest import (
    PLAYBOOK_KEY,
    ROLES_KEY,
    WORKFLOW_KEY,
    artifact_changed_since,
    artifact_floor,
    base_version_artifact_content,
    bundled_artifact_content,
    bundled_template_content,
    template_changed_since,
    template_key,
)
from squads._overrides._stamp import (
    read_template_stamp,
    read_toml_stamp,
    stamp_template_file,
    stamp_toml_file,
    write_template_stamp,
)
from squads._paths import path_from_process_dir
from squads._rendering._engine import invalidate_squad_dir, template_compile_error
from squads._roles._catalog import PREDEFINED, RoleDef, get_catalog, role_by_slug
from squads._roles._loader import (
    ROLES_OVERRIDE_FILENAME,
    ROLES_OVERRIDE_MESSAGES,
    bundled_roles_raw,
    bundled_roles_toml_text,
)
from squads._roles._models import CatalogSource, RoleSpec
from squads._roles._resolver import role_base_from_item
from squads._sections import find_markers
from squads._specload import (
    ROLE_OVERRIDE_MESSAGES,
    TEMPLATE_OVERRIDE_MESSAGES,
    OverrideFiles,
    OverrideMessages,
    OverrideReadError,
    override_mapping,
    override_present,
    read_override_text,
)
from squads._util import version_tuple
from squads._workflow._loader import (
    WORKFLOW_OVERRIDE_FILENAME,
    WORKFLOW_OVERRIDE_MESSAGES,
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

    name: str  # template-relative path, role slug, "workflow", "playbook", or "roles"
    #: "template" | "role" (a per-slug .overrides/roles/<slug>.toml) | "workflow" | "playbook"
    #: | "roles" (the whole-document .overrides/roles.toml catalog override) — five kinds, not
    #: the two this field was once documented as.
    kind: str
    base_version: str | None  # from the stamp, or None if unstamped
    state: str  # STATE_CURRENT | STATE_DRIFTED | STATE_BROKEN
    cause: str | None = None  # why the file is broken, when it cannot be read


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
    """Return the ``sq:*`` open-marker tags the bundled template requires (never ``:end`` closers,
    and empty for an unreadable or marker-free template). A view-tag family member
    (:func:`~squads._models._markers.view_tag_parts`) is excluded: a seeded view's tag binds a
    document, not the template that scaffolds it, so an override dropping it is a sanctioned escape,
    and being unpaired its absence cannot break marker-safe editing. It uses
    :func:`~squads._sections.find_markers`, the one marker-recognition primitive, so the tag class
    is widened in one place.
    """
    content = bundled_template_content(template_name)
    if content is None:
        return set()
    return {
        tag
        for tag in find_markers(content)
        if not tag.endswith(":end") and markers.view_tag_parts(tag) is None
    }


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


def _roles_catalog_override_path(squad_dir: Path) -> Path:
    return squad_dir / ROLES_OVERRIDE_FILENAME


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
    """Classify a role TOML override as current or drifted. Drift is measured against
    ``roles.toml``, the document a role override actually overrides, not the role body template
    (``agents/role.md.j2``), which is a separate override with its own stamp: a change to a bundled
    role's mission or a new ``RoleSpec`` field drifts a shadowing override, a cosmetic body-template
    edit does not. TOML has no sq markers, so it is never 'broken'.
    """
    stamp = read_toml_stamp(text)
    if stamp is None:
        return STATE_DRIFTED

    if stamp == __version__:
        return STATE_CURRENT

    if artifact_changed_since(ROLES_KEY, stamp):
        return STATE_DRIFTED
    return STATE_CURRENT


def _workflow_state(text: str) -> str:
    """Classify the workflow TOML override as current or drifted. An unstamped file has not been
    reconciled against any bundled version, so it is drifted whether it shadows or only adds (that
    distinction drives the stamp-obligation finding in :func:`_check_workflow_override_issues`). A
    stamp older than the running version is drifted only when the bundled ``workflow.toml`` changed
    since it, so an add-only override with no bundled change is silent. TOML has no sq markers, so
    it is never 'broken'.
    """
    stamp = read_toml_stamp(text)
    if stamp is None:
        return STATE_DRIFTED
    if stamp == __version__:
        return STATE_CURRENT
    if artifact_changed_since(WORKFLOW_KEY, stamp):
        return STATE_DRIFTED
    return STATE_CURRENT


def _playbook_state(text: str) -> str:
    """Classify the playbook TOML override as current / drifted — mirrors
    :func:`_workflow_state` exactly (same three-state, content-gated contract). TOML
    has no sq markers, so a playbook override is never 'broken' in the marker
    sense."""
    stamp = read_toml_stamp(text)
    if stamp is None:
        return STATE_DRIFTED
    if stamp == __version__:
        return STATE_CURRENT
    if artifact_changed_since(PLAYBOOK_KEY, stamp):
        return STATE_DRIFTED
    return STATE_CURRENT


def _roles_catalog_state(text: str) -> str:
    """Classify the role catalog document override (``.overrides/roles.toml``) as
    current / drifted — mirrors :func:`_workflow_state`/:func:`_playbook_state` exactly, gated
    against ``ROLES_KEY`` (the same manifest key :func:`_role_state` gates a per-slug override
    against, since both documents shadow the same bundled ``roles.toml``). TOML has no sq
    markers, so this override is never 'broken' in the marker sense."""
    stamp = read_toml_stamp(text)
    if stamp is None:
        return STATE_DRIFTED
    if stamp == __version__:
        return STATE_CURRENT
    if artifact_changed_since(ROLES_KEY, stamp):
        return STATE_DRIFTED
    return STATE_CURRENT


# ─── scan_overrides ────────────────────────────────────────────────────────────


def _messages_for(kind: str) -> OverrideMessages:
    """The read-error wording of one kind of override file."""
    match kind:
        case "workflow":
            return WORKFLOW_OVERRIDE_MESSAGES
        case "playbook":
            return PLAYBOOK_OVERRIDE_MESSAGES
        case "roles":
            return ROLES_OVERRIDE_MESSAGES
        case "role":
            return ROLE_OVERRIDE_MESSAGES
        case _:
            return TEMPLATE_OVERRIDE_MESSAGES


def _read(path: Path, kind: str) -> str:
    """The text of an override file of *kind*; the one read the scan, diff, update and check
    paths share. Raises :class:`OverrideReadError`."""
    return read_override_text(path, _messages_for(kind))


def _scan_text(path: Path, kind: str) -> tuple[str | None, str | None]:
    """The override's text and no cause, or no text and the reason it cannot be read (the file is
    listed as broken)."""
    try:
        return _read(path, kind), None
    except OverrideReadError as exc:
        return None, str(exc)


def scan_overrides(squad_dir: Path) -> list[OverrideEntry]:
    """Enumerate every override under ``.overrides/``, returning one entry per file."""
    entries: list[OverrideEntry] = []

    # Template overrides
    tmpl_dir = _template_overrides_dir(squad_dir)
    if tmpl_dir.is_dir():
        for path in sorted(tmpl_dir.rglob("*.md.j2")):
            rel = path.relative_to(tmpl_dir).as_posix()
            text, cause = _scan_text(path, "template")
            stamp = read_template_stamp(text) if text is not None else None
            state = _template_state(rel, path, text) if text is not None else STATE_BROKEN
            entries.append(
                OverrideEntry(
                    name=rel, kind="template", base_version=stamp, state=state, cause=cause
                )
            )

    # Role TOML overrides
    role_dir = _role_overrides_dir(squad_dir)
    if role_dir.is_dir():
        for path in sorted(role_dir.glob("*.toml")):
            slug = path.stem
            text, cause = _scan_text(path, "role")
            stamp = read_toml_stamp(text) if text is not None else None
            state = _role_state(slug, path, text) if text is not None else STATE_BROKEN
            entries.append(
                OverrideEntry(name=slug, kind="role", base_version=stamp, state=state, cause=cause)
            )

    # Workflow TOML override (single file, not a directory)
    wf_path = _workflow_override_path(squad_dir)
    if override_present(wf_path):
        text, cause = _scan_text(wf_path, "workflow")
        stamp = read_toml_stamp(text) if text is not None else None
        state = _workflow_state(text) if text is not None else STATE_BROKEN
        entries.append(
            OverrideEntry(
                name="workflow", kind="workflow", base_version=stamp, state=state, cause=cause
            )
        )

    # Playbook TOML override (single file, not a directory)
    pb_path = _playbook_override_path(squad_dir)
    if override_present(pb_path):
        text, cause = _scan_text(pb_path, "playbook")
        stamp = read_toml_stamp(text) if text is not None else None
        state = _playbook_state(text) if text is not None else STATE_BROKEN
        entries.append(
            OverrideEntry(
                name="playbook", kind="playbook", base_version=stamp, state=state, cause=cause
            )
        )

    # Role catalog document override (single file, not a directory)
    rc_path = _roles_catalog_override_path(squad_dir)
    if override_present(rc_path):
        text, cause = _scan_text(rc_path, "roles")
        stamp = read_toml_stamp(text) if text is not None else None
        state = _roles_catalog_state(text) if text is not None else STATE_BROKEN
        entries.append(
            OverrideEntry(name="roles", kind="roles", base_version=stamp, state=state, cause=cause)
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
    dest.write_text(stamped, encoding="utf-8", newline="")

    # The engine caches the environment per squad dir — invalidate so the new file is picked up.
    invalidate_squad_dir(squad_dir)

    return dest


# ─── role slug safety ──────────────────────────────────────────────────────────


def _validate_role_slug(squad_dir: Path, slug: str) -> Path:
    """Validate *slug* as a safe ``.overrides/roles/<slug>.toml`` filename component: it rejects an
    empty slug or one with a path separator, a leading dot or a ``..`` segment, and, mirroring
    ``_paths.SquadPaths.abspath``, one whose resolved destination lands outside
    ``.overrides/roles/``. Returns the unresolved destination path or raises :class:`SquadsError`.
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


#: Fields a role override file cannot meaningfully set: the filename is the slug, and the default
#: role is designated with ``sq role set-default``.
_ROLE_SCAFFOLD_SKIPPED_FIELDS = frozenset({"slug", "is_default"})

_ROLE_APPEND_IDIOM = (
    "# Append to the bundled list instead of replacing it:\n"
    '# responsibilities = ["$(*self)", "…"]\n'
)


def _role_scaffold_lines(role: RoleDef) -> str:
    """Every overridable field *role* sets, commented out with its value; a field it leaves
    unset has no line."""
    lines: list[str] = []
    for field in RoleSpec.model_fields:
        value = getattr(role, field)
        if field in _ROLE_SCAFFOLD_SKIPPED_FIELDS or value is None:
            continue
        lines.append(f"# {field} = {json.dumps(value, ensure_ascii=False)}\n")
        if field == "responsibilities":
            lines.append(_ROLE_APPEND_IDIOM)
    return "".join(lines)


def scaffold_role(
    squad_dir: Path, slug: str, *, force: bool = False, base: RoleDef | None = None
) -> Path:
    """Create ``.overrides/roles/<slug>.toml`` with the stamp comment.

    For a bundled role, or a role whose resolved *base* the caller supplies (a templated
    developer), every overridable field follows, commented out with its value; uncomment and
    edit the ones to change. Raises :class:`SquadsError` if *slug* is unsafe, or the file exists
    and ``--force`` is not set.
    """
    dest = _validate_role_slug(squad_dir, slug)
    if dest.exists() and not force:
        raise SquadsError(f".overrides/roles/{slug}.toml already exists; use --force to overwrite")

    if base is None and slug in _BUNDLED_ROLE_SLUGS:
        base = role_by_slug(slug)
    dest.parent.mkdir(parents=True, exist_ok=True)
    stamp_line = f"# squads:override-base:{__version__}\n"
    if base is None:
        desc = f"# Role override for '{slug}'. Add fields to override (e.g. full_name, model).\n"
        fields = ""
    else:
        desc = f"# Role override for '{slug}'. Uncomment a field to override it.\n"
        fields = _role_scaffold_lines(base)
    dest.write_text(stamp_line + desc + fields, encoding="utf-8", newline="")
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
#
# [views.related_incidents]
# # A derived view: a source (a declared ref kind, a sub-entity kind, or a subtree) and an
# # optional transform. Computed fresh on every request — nothing is ever written into a body. The
# # presentation template receives the source's own resolved records directly (real items, not
# # a flattened row) and does its own grouping/ordering with Jinja's groupby/sort/selectattr.
# # Needs a presentation template of its own before it can render: create one at
# # templates/views/related_incidents.md.j2 (or .overrides/templates/views/related_incidents.md.j2
# # to shadow the bundled default) — until you do, resolve it with `--json`, which does not render.
# source = { kind = "ref", name = "related" }
# # Optional: a transform turns the source into plain data (dict or list of JSON values) that
# # the template reads as `data` and `show --json` returns under `views.related_incidents`.
# # The file lives under .overrides/ and defines `def related_incidents(source, *, item, spec)`;
# # sq passes only the keywords it declares. It is trusted code, run with your permissions.
# transform = { path = "transforms/related_incidents.py", function = "related_incidents" }
# -----------------------------------------------------------------------------
"""


def scaffold_workflow(squad_dir: Path, *, force: bool = False) -> Path:
    """Create ``.overrides/workflow.toml`` with the stamp comment and a commented worked example,
    starting from scratch rather than copying the bundled default. The override it primes can
    shadow, not only add: a hand-written key replaces its bundled counterpart and ``[selected]``
    drops one by name. Raises :class:`SquadsError` if the file exists and ``--force`` is not set.
    """
    dest = _workflow_override_path(squad_dir)
    if dest.exists() and not force:
        raise SquadsError(f"{WORKFLOW_OVERRIDE_FILENAME} already exists; use --force to overwrite")

    dest.parent.mkdir(parents=True, exist_ok=True)
    stamp_line = f"# squads:override-base:{__version__}\n"
    dest.write_text(stamp_line + _WORKFLOW_SCAFFOLD_BODY, encoding="utf-8", newline="")
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
#   - Every guide subject must be one of: a bundled catalog role, a project role you have
#     defined under .overrides/roles/<slug>.toml, or `*<capability>`, which addresses every live
#     role whose `capabilities` list holds that name.
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
# claims the type's create-lane, so `sq create <type> --author devops` stops warning.
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
    dest.write_text(stamp_line + _PLAYBOOK_SCAFFOLD_BODY, encoding="utf-8", newline="")
    return dest


# ─── scaffold_roles_catalog ──────────────────────────────────────────────────────

#: Starter content for a scaffolded role-catalog override — stamp + a commented example
#: covering all three sections this document closes over.
_ROLES_CATALOG_SCAFFOLD_BODY = """\
# Role catalog override — bundles, role templates, and (optionally) roles, all in one
# document. Precedence: bundled roles.toml -> this document -> a per-slug
# .overrides/roles/<slug>.toml file, which still wins over this document for the same field.
#
# A role's name: a new role takes its name from these layers when it is created, the most
# specific one winning, unless `--name` is given (`sq role activate --name`, `sq dev add --name`,
# `sq init --name`). The name is then stored on the role and no change here renames it.
#
# Rules:
#   - Top-level keys are limited to: roles, bundles, templates, defaults (plus [selected] below).
#   - [bundles.<name>] fields merge field-by-field over the bundled default; a new bundle
#     name is simply added.
#   - [templates.<name>] fields merge field-by-field over a bundled template of that name —
#     override just one without restating the others; a new name defines a new template,
#     instantiated by `sq role activate --from <name>` (placeholders: {tech}, {Tech}, and
#     {first} in `name`).
#   - [defaults] holds roster-wide values a role takes when it has none of its own: pronouns
#     (one line, 1 to 40 characters). Never written onto a role; operators never take it.
#   - [[roles]] entries are keyed by their own 'slug': an entry naming a bundled slug
#     field-merges onto it (write only the field you want to change); an entry naming a new
#     slug adds a catalog role (full_name, title, description, mission all required).
#   - Drop a bundled role, bundle or template via [selected] (selected.roles / bundles /
#     templates) — a
#     deselect that would empty a bundle or remove the default agent fails validation.
#
# See state after editing: sq override diff roles
# Re-stamp after merging:  sq override update roles
#
# --- Worked example (uncomment and edit to activate) -------------------------
#
# [templates.dev]
# model = "opus"
#
# [defaults]
# pronouns = "they/them"
#
# [[roles]]
# slug = "architect"
# title = "Chief Architect"
#
# [selected]
# bundles = ["all", "core"]
# -----------------------------------------------------------------------------
"""


def scaffold_roles_catalog(squad_dir: Path, *, force: bool = False) -> Path:
    """Create ``.overrides/roles.toml`` with the stamp comment + a worked example.

    Mirrors :func:`scaffold_workflow`/:func:`scaffold_playbook`: starts from scratch (not a
    copy of the bundled default) and contains only a commented example. Raises
    :class:`SquadsError` if the file already exists and ``--force`` is not set.
    """
    dest = _roles_catalog_override_path(squad_dir)
    if dest.exists() and not force:
        raise SquadsError(f"{ROLES_OVERRIDE_FILENAME} already exists; use --force to overwrite")

    dest.parent.mkdir(parents=True, exist_ok=True)
    stamp_line = f"# squads:override-base:{__version__}\n"
    dest.write_text(stamp_line + _ROLES_CATALOG_SCAFFOLD_BODY, encoding="utf-8", newline="")
    return dest


# ─── diff_override ─────────────────────────────────────────────────────────────


def _unified_diff(a: str, b: str, fromfile: str, tofile: str) -> str:
    """Return a unified diff string (empty if no difference)."""
    a_lines = a.splitlines(keepends=True)
    b_lines = b.splitlines(keepends=True)
    lines = list(difflib.unified_diff(a_lines, b_lines, fromfile=fromfile, tofile=tofile))
    return "".join(lines)


# ─── Δ-upgrade: shared across every override kind ─────────────────────────────


def _upgrade_delta(
    key: str, base_version: str | None, *, label: str, fromfile_prefix: str
) -> tuple[str, bool]:
    """Compute the Δ-upgrade pane and ``base_available`` for one artifact key, shared by every
    override kind: a real unified diff whenever the content store carries the stamped base revision
    (``base_version_artifact_content``), which is what makes it expressible for a spec document too;
    otherwise :func:`_uncarried_base_pane` explains why.
    """
    if base_version is None:
        return ("(no stamp — run `sq override update` to stamp the current version)", False)

    current_content = bundled_artifact_content(key) or ""
    base_content = base_version_artifact_content(key, base_version)
    if base_content is not None:
        return (
            _unified_diff(
                base_content,
                current_content,
                fromfile=f"{fromfile_prefix}@v{base_version}",
                tofile=f"{fromfile_prefix} (current)",
            ),
            True,
        )

    return (_uncarried_base_pane(key, base_version, label), False)


def _uncarried_base_pane(key: str, base_version: str, label: str) -> str:
    """The pane for a stamped base revision the content store does not carry, in three shapes: newer
    than the running version (a downgrade, refused, as no anchor exists in that direction); below
    this artifact's coverage floor (a partial Δ-upgrade from the earliest carried revision when its
    content is available); and any other (a malformed stamp, or a release predating this artifact's
    tracking), reported by name. Each names the artifact, the stamped version, why it is not carried
    and what is available. It is never an `sq check` finding, since the drift classifiers stay
    silent for all three (``artifact_changed_since`` is ``False`` for an unrecorded base).
    """
    running_v = version_tuple(__version__)
    base_v = version_tuple(base_version)

    if base_v > running_v:
        return (
            f"(cannot show an upgrade delta for {label}: the stamp names v{base_version}, "
            f"newer than the running v{__version__} — a downgrade has no earlier bundled "
            "revision to diff against)"
        )

    floor = artifact_floor(key)
    if floor is not None and base_v < version_tuple(floor):
        anchor_content = base_version_artifact_content(key, floor)
        if anchor_content is not None:
            current_content = bundled_artifact_content(key) or ""
            diff = _unified_diff(
                anchor_content,
                current_content,
                fromfile=f"{label}@v{floor} (earliest carried revision)",
                tofile=f"{label} (current)",
            )
            return (
                f"(stamp v{base_version} predates squads' own provenance for {label}, which "
                f"starts at v{floor} — partial Δ-upgrade below, starting from v{floor} "
                f"rather than v{base_version}; changes to {label} before v{floor} are not "
                f"represented)\n\n{diff}"
            )

    if floor is None:
        return (
            f"(stamp v{base_version} — squads carries no provenance history for {label} yet; "
            "run `sq override update` to re-stamp at the current, tracked revision)"
        )

    return (
        f"(stamp v{base_version} names no recorded {label} revision — either it names a "
        f"version squads never released, or {label} was not yet an overridable artifact at "
        f"that release; squads' own provenance for it starts at v{floor} — run "
        "`sq override update` to re-stamp at the current, tracked revision)"
    )


def diff_override(squad_dir: Path, name: str, kind: str) -> DiffResult:
    """Compute both diffs for one override.

    *kind* is ``"template"``, ``"role"``, ``"workflow"``, ``"playbook"``, or ``"roles"`` (the
    whole-document role catalog override). Raises :class:`SquadsError` when the override file
    is not found.
    """
    if kind == "template":
        return _diff_template(squad_dir, name)
    if kind == "role":
        return _diff_role(squad_dir, name)
    if kind == "workflow":
        return _diff_workflow(squad_dir)
    if kind == "playbook":
        return _diff_playbook(squad_dir)
    if kind == "roles":
        return _diff_roles_catalog(squad_dir)
    raise SquadsError(
        f"unknown override kind {kind!r}; expected 'template', 'role', 'workflow', "
        "'playbook', or 'roles'"
    )


def _diff_template(squad_dir: Path, template_name: str) -> DiffResult:
    path = _template_overrides_dir(squad_dir) / template_name
    if not override_present(path):
        raise SquadsError(
            f"no template override for {template_name!r} "
            f"(run `sq override scaffold {template_name}` first)"
        )

    override_text = _read(path, "template")
    base_version = read_template_stamp(override_text)

    current_bundled = bundled_template_content(template_name) or ""

    # Δ-mine: override vs current bundled (what the team customised from today's default).
    delta_mine = _unified_diff(
        current_bundled,
        override_text,
        fromfile=f"bundled/{template_name}",
        tofile=f".overrides/templates/{template_name}",
    )

    delta_upgrade, base_available = _upgrade_delta(
        template_key(template_name),
        base_version,
        label=template_name,
        fromfile_prefix=f"bundled/{template_name}",
    )

    return DiffResult(
        name=template_name,
        kind="template",
        delta_mine=delta_mine,
        delta_upgrade=delta_upgrade,
        base_version=base_version,
        base_available=base_available,
    )


#: RoleDef fields rendered by :func:`_role_def_as_toml`, in a stable display order.
_ROLE_DEF_SCALAR_FIELDS = ("full_name", "title", "description", "mission")
_ROLE_DEF_LIST_FIELDS = ("responsibilities", "agreements", "capabilities")
_ROLE_DEF_OPTIONAL_SCALAR_FIELDS = ("model", "color")


def _role_def_as_toml(base: RoleDef) -> str:
    """Render *base*'s fields in the same flat-key shape a role override file uses.

    Only for Δ-mine display (a diff baseline), not a real TOML writer: string values are
    escaped via ``json.dumps``, which produces a valid TOML basic string for every value a
    ``RoleDef`` actually carries. Fields absent from the bundled role (``None``, or an empty
    list) are omitted, exactly as they would be from a hand-written override.
    """
    lines: list[str] = [
        f"{field} = {json.dumps(getattr(base, field))}" for field in _ROLE_DEF_SCALAR_FIELDS
    ]
    for field in _ROLE_DEF_LIST_FIELDS:
        values = getattr(base, field)
        if values:
            lines.append(f"{field} = {json.dumps(list(values))}")
    for field in _ROLE_DEF_OPTIONAL_SCALAR_FIELDS:
        value = getattr(base, field)
        if value is not None:
            lines.append(f"{field} = {json.dumps(value)}")
    lines.append(f"can_spawn = {'true' if base.can_spawn else 'false'}")
    return "\n".join(lines) + "\n"


def _shadowed_bundled_role_toml(slug: str, squad_dir: Path | None = None) -> str | None:
    """The bundled role *slug* shadows, rendered as TOML — or ``None`` for a brand-new
    (non-bundled) role slug, which genuinely starts from scratch.

    A bundled role is read as the bundled catalog ships it, not after the project catalog
    merge: that is what the Δ-mine baseline means."""
    if slug in _BUNDLED_ROLE_SLUGS:
        return _role_def_as_toml(role_by_slug(slug))
    return None


def _diff_role(squad_dir: Path, slug: str) -> DiffResult:
    path = _role_overrides_dir(squad_dir) / f"{slug}.toml"
    if not override_present(path):
        raise SquadsError(
            f"no role override for {slug!r} (run `sq override scaffold --role {slug}` first)"
        )

    override_text = _read(path, "role")
    base_version = read_toml_stamp(override_text)

    # Δ-mine: a role override merges field-wise over the bundled role and so shadows it, so diff
    # against the shadowed bundled role's fields, as for the workflow document; an empty reference
    # would describe only what the team added. A file over a role with no bundled counterpart keeps
    # the empty baseline.
    shadowed = _shadowed_bundled_role_toml(slug, squad_dir)
    if shadowed is not None:
        delta_mine = _unified_diff(
            shadowed,
            override_text,
            fromfile=f"bundled/roles.toml#{slug}",
            tofile=f".overrides/roles/{slug}.toml",
        )
    else:
        delta_mine = _unified_diff(
            "",
            override_text,
            fromfile="(empty — role overrides start from scratch)",
            tofile=f".overrides/roles/{slug}.toml",
        )

    # Δ-upgrade: a role override's real bundled counterpart is roles.toml,
    # not the role body template (agents/role.md.j2, a separate override with its own drift) —
    # so the upgrade delta is the whole document's, at the granularity the manifest tracks it.
    delta_upgrade, base_available = _upgrade_delta(
        ROLES_KEY, base_version, label="roles.toml", fromfile_prefix="bundled/roles.toml"
    )

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
    if not override_present(path):
        raise SquadsError("no workflow override found (run `sq override scaffold workflow` first)")

    override_text = _read(path, "workflow")
    base_version = read_toml_stamp(override_text)

    # Δ-mine: override vs the bundled workflow.toml — since the override can shadow, an
    # empty reference would describe only "what the team added" and say nothing about a
    # shadowed field, which is exactly the kind of change this diff exists to show.
    delta_mine = _unified_diff(
        bundled_workflow_toml_text(),
        override_text,
        fromfile="bundled/workflow.toml",
        tofile=WORKFLOW_OVERRIDE_FILENAME,
    )

    # Δ-upgrade: for a spec document, a real diff between the
    # stamped base revision and the current bundled workflow.toml, resolved from the content
    # store, exactly like every other kind.
    delta_upgrade, base_available = _upgrade_delta(
        WORKFLOW_KEY, base_version, label="workflow.toml", fromfile_prefix="bundled/workflow.toml"
    )

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
    if not override_present(path):
        raise SquadsError("no playbook override found (run `sq override scaffold playbook` first)")

    override_text = _read(path, "playbook")
    base_version = read_toml_stamp(override_text)

    delta_mine = _unified_diff(
        bundled_playbook_toml_text(),
        override_text,
        fromfile="bundled/playbook.toml",
        tofile=PLAYBOOK_OVERRIDE_FILENAME,
    )

    delta_upgrade, base_available = _upgrade_delta(
        PLAYBOOK_KEY, base_version, label="playbook.toml", fromfile_prefix="bundled/playbook.toml"
    )

    return DiffResult(
        name="playbook",
        kind="playbook",
        delta_mine=delta_mine,
        delta_upgrade=delta_upgrade,
        base_version=base_version,
        base_available=base_available,
    )


def _diff_roles_catalog(squad_dir: Path) -> DiffResult:
    """Mirrors :func:`_diff_workflow`/:func:`_diff_playbook` exactly — same
    Δ-mine-against-bundled, Δ-upgrade-by-stamp-comparison shape, gated against ``ROLES_KEY``
    (the document a role catalog override actually overrides — the same key
    :func:`_diff_role`'s Δ-upgrade already uses for a per-slug override)."""
    path = _roles_catalog_override_path(squad_dir)
    if not override_present(path):
        raise SquadsError("no role catalog override found (run `sq override scaffold roles` first)")

    override_text = _read(path, "roles")
    base_version = read_toml_stamp(override_text)

    delta_mine = _unified_diff(
        bundled_roles_toml_text(),
        override_text,
        fromfile="bundled/roles.toml",
        tofile=ROLES_OVERRIDE_FILENAME,
    )

    delta_upgrade, base_available = _upgrade_delta(
        ROLES_KEY, base_version, label="roles.toml", fromfile_prefix="bundled/roles.toml"
    )

    return DiffResult(
        name="roles",
        kind="roles",
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
        if override_present(path):
            stamp_toml_file(path, __version__, _messages_for("workflow"))
            return ["workflow"]
        raise SquadsError("no workflow override found. Run `sq override scaffold workflow` first.")
    if kind == "playbook":
        path = _playbook_override_path(squad_dir)
        if override_present(path):
            stamp_toml_file(path, __version__, _messages_for("playbook"))
            return ["playbook"]
        raise SquadsError("no playbook override found. Run `sq override scaffold playbook` first.")
    if kind == "roles":
        path = _roles_catalog_override_path(squad_dir)
        if override_present(path):
            stamp_toml_file(path, __version__, _messages_for("roles"))
            return ["roles"]
        raise SquadsError("no role catalog override found. Run `sq override scaffold roles` first.")
    if kind == "template" or kind is None:
        path = _template_overrides_dir(squad_dir) / name
        if override_present(path):
            text = _read(path, "template")
            if _is_item_or_role_template(name) and _missing_required_markers(name, text):
                raise SquadsError(
                    f"cannot re-stamp {name!r}: override is missing required sq markers. "
                    "Fix the marker structure first, then run `sq override update`."
                )
            stamp_template_file(path, __version__)
            return [name]
    if kind == "role":
        path = _role_overrides_dir(squad_dir) / f"{name}.toml"
        if override_present(path):
            stamp_toml_file(path, __version__)
            return [name]
    raise SquadsError(
        f"no override found for {name!r} (kind={kind!r}). "
        "Run `sq override list` to see existing overrides."
    )


def _update_all(squad_dir: Path) -> list[str]:
    """Re-stamp every structurally-valid override; skip broken ones, including a file that
    cannot be read."""
    stamped: list[str] = []

    tmpl_dir = _template_overrides_dir(squad_dir)
    if tmpl_dir.is_dir():
        for path in sorted(tmpl_dir.rglob("*.md.j2")):
            rel = path.relative_to(tmpl_dir).as_posix()
            try:
                text = _read(path, "template")
            except OverrideReadError:
                continue
            if _is_item_or_role_template(rel) and _missing_required_markers(rel, text):
                continue  # Skip broken overrides silently in bulk mode
            stamp_template_file(path, __version__)
            stamped.append(rel)

    role_dir = _role_overrides_dir(squad_dir)
    if role_dir.is_dir():
        candidates = [(path, path.stem, "role") for path in sorted(role_dir.glob("*.toml"))]
    else:
        candidates = []
    candidates += [
        (_workflow_override_path(squad_dir), "workflow", "workflow"),
        (_playbook_override_path(squad_dir), "playbook", "playbook"),
        (_roles_catalog_override_path(squad_dir), "roles", "roles"),
    ]
    for path, name, kind in candidates:
        if not override_present(path):
            continue
        try:
            stamp_toml_file(path, __version__, _messages_for(kind))
        except OverrideReadError:
            continue
        stamped.append(name)

    return stamped


# Shadowing detection (stamp-obligation gating). An unstamped shadowing override is an error for
# every kind, having stopped tracking a bundled counterpart with no provenance; an unstamped add-
# only override reports nothing. ``workflow``/``playbook`` test this via their loaders'
# ``*_override_shadows_bundled``; these two give ``template``/``role`` the same test over the
# baseline each kind's Δ-mine already computes.


def _template_override_shadows_bundled(template_name: str) -> bool:
    """Whether *template_name* names an actual bundled template — the same baseline
    :func:`_diff_template`'s Δ-mine falls back to ``""`` for when this is ``False``."""
    return bundled_template_content(template_name) is not None


def _role_override_shadows_bundled(
    slug: str, role_items_by_slug: Mapping[str, Item], squad_dir: Path | None = None
) -> bool:
    """Whether *slug* shadows a bundled catalog or template role, resolved as
    :func:`_check_role_override_resolves` resolves a base: when a roster item exists its stored fact
    (its ``tech`` or bundled slug, via :func:`~squads._roles._resolver.role_base_from_item`, read
    against the bundled catalog alone) wins, and only a slug with no roster item falls back to the
    naming convention (:func:`_shadowed_bundled_role_toml`, the baseline :func:`_diff_role` uses).
    Otherwise a custom role whose slug merely ends in ``-dev`` would be misread as shadowing the
    dev-pool base.
    """
    item = role_items_by_slug.get(slug)
    if item is not None:
        return attrs.mission(item) is None and role_base_from_item(item, get_catalog) is not None
    return _shadowed_bundled_role_toml(slug, squad_dir) is not None


def _raw_role_slugs(raw: Mapping[str, Any]) -> set[str]:
    """Every slug a raw (unmerged) role-catalog mapping's ``[[roles]]`` array declares."""
    roles = raw.get("roles")
    if not isinstance(roles, list):
        return set()
    return {
        cast("dict[str, Any]", entry)["slug"]
        for entry in cast("list[Any]", roles)
        if isinstance(entry, dict) and isinstance(cast("dict[str, Any]", entry).get("slug"), str)
    }


def _keys_overlap(bundled: Any, override: Any) -> bool:
    """Whether two raw keyed tables (bundles, templates) name a key in common."""
    return (
        isinstance(bundled, dict)
        and isinstance(override, dict)
        and bool(set(cast("dict[str, Any]", bundled)) & set(cast("dict[str, Any]", override)))
    )


def _roles_catalog_override_shadows_bundled(
    squad_dir: Path, files: OverrideFiles | None = None
) -> bool:
    """Whether ``<squad_dir>/.overrides/roles.toml`` redeclares (shadows) at least one bundled
    role slug, bundle name or template name — a raw key-set intersection, no merge
    required, mirroring ``workflow_override_shadows_bundled``/``playbook_override_shadows_bundled``.

    Returns ``False`` when the override is absent, unreadable, undecodable or malformed TOML:
    the drift-stamp obligation is moot for a file that cannot even be parsed.
    """
    path = _roles_catalog_override_path(squad_dir)
    if not override_present(path):
        return False
    try:
        override_raw: dict[str, Any] = override_mapping(path, files)
    except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError):  # fmt: skip
        return False

    # Unguarded, like `workflow_override_shadows_bundled`/`playbook_override_shadows_bundled`'s
    # own bundled reads: a broken bundled roles.toml is a packaging defect, not a state this
    # predicate tolerates silently.
    bundled_raw = bundled_roles_raw()

    bundle_overlap = _keys_overlap(bundled_raw.get("bundles"), override_raw.get("bundles"))
    return (
        bool(_raw_role_slugs(bundled_raw) & _raw_role_slugs(override_raw))
        or bundle_overlap
        or _keys_overlap(bundled_raw.get("templates"), override_raw.get("templates"))
    )


def _roles_catalog_stamp_finding_gated(
    squad_dir: Path, stamp: str | None, files: OverrideFiles | None = None
) -> tuple[str, str] | None:
    """The stamp obligation for the role catalog document override, content-gated like
    ``workflow_stamp_finding`` and ``playbook_stamp_finding`` in ``squads._workflow._loader``, the
    three-outcome contract every shadowing override kind shares. Its remediation names its own
    object (``sq override update roles`` / ``diff roles``), as ``_cli/_override.py`` resolves a
    ``roles`` positional to the ``roles`` kind.
    """
    if stamp is None:
        if _roles_catalog_override_shadows_bundled(squad_dir, files):
            return (
                "error",
                "shadowing role catalog override has no squads:override-base stamp; run "
                "`sq override update roles` to re-stamp",
            )
        return None
    if stamp != __version__ and artifact_changed_since(ROLES_KEY, stamp):
        return (
            "warn",
            f"role catalog override may be stale: bundled roles.toml changed since v{stamp}; "
            "run `sq override diff roles` to review, then `sq override update roles` to re-stamp",
        )
    return None


def _roles_catalog_invalid_issue(squad_dir: Path, catalog: CatalogSource) -> OverrideIssue | None:
    """The error finding when the merged role catalog refuses to load, else ``None``. The
    catalog loads lazily, so ``compose_service`` never surfaces an invalid merge."""
    if not override_present(_roles_catalog_override_path(squad_dir)):
        return None
    try:
        catalog()
    except SquadsError as exc:
        return _issue(
            "error",
            ROLES_OVERRIDE_FILENAME,
            f"role catalog override is invalid: {exc}",
            "override_loads",
        )
    return None


def _check_roles_catalog_override_issues(
    squad_dir: Path, invalid: OverrideIssue | None, files: OverrideFiles
) -> list[OverrideIssue]:
    """Return check issues for the role catalog document override (if present): the stamp
    findings its workflow and playbook siblings report, plus *invalid* — the refusal from
    :func:`_roles_catalog_invalid_issue`, which those siblings leave to ``compose_service``."""
    rc_path = _roles_catalog_override_path(squad_dir)
    if not override_present(rc_path):
        return []

    display = ROLES_OVERRIDE_FILENAME
    text = _text_or_none(rc_path, files)
    stamp = read_toml_stamp(text) if text is not None else None
    issues: list[OverrideIssue] = []
    if invalid is not None:
        issues.append(invalid)
    finding = _roles_catalog_stamp_finding_gated(squad_dir, stamp, files)
    if finding is not None:
        issues.append(_stamp_issue(finding[0], display, finding[1]))
    return issues


# ─── check helpers (used by _services/_check.py) ────────────────────────

#: One override finding for ``sq check``: ``(level, display path, message, rule)``.
type OverrideIssue = tuple[str, str, str, str]


def _issue(level: str, display: str, message: str, rule: str) -> OverrideIssue:
    return (level, display, message, rule)


def _stamp_issue(level: str, display: str, message: str) -> OverrideIssue:
    """A stamp finding: an error is a missing stamp, a warn is drift from the bundled base."""
    return _issue(
        level, display, message, "override_stamped" if level == "error" else "override_current"
    )


def check_override_issues(
    squad_dir: Path,
    role_items_by_slug: Mapping[str, Item] | None = None,
    *,
    catalog: CatalogSource,
    files: OverrideFiles | None = None,
) -> list[OverrideIssue]:
    """Return ``(level, item_path, message, rule)`` tuples for ``sq check``, *level* being
    ``"warn"`` or ``"error"`` and *item_path* the display path. *role_items_by_slug* (the live
    roster's ``ROLE`` items, supplied by ``Service.check`` as this function has no roster) lets a
    role override resolve against its live identity via
    :func:`~squads._roles._resolver.role_base_from_item`; without an entry a file is reported as the
    new role it would be.
    """
    role_items_by_slug = role_items_by_slug or {}
    files = files if files is not None else OverrideFiles()
    # Per-slug role overrides resolve against the merged catalog, so with it invalid their
    # resolve step can only repeat its refusal; their stamp checks still run.
    catalog_invalid = _roles_catalog_invalid_issue(squad_dir, catalog)
    return [
        *_check_template_override_issues(squad_dir),
        *_check_role_toml_override_issues(
            squad_dir, role_items_by_slug, catalog, resolve=catalog_invalid is None
        ),
        *_check_workflow_override_issues(squad_dir, files),
        *_check_playbook_override_issues(squad_dir, files),
        *_check_roles_catalog_override_issues(squad_dir, catalog_invalid, files),
    ]


def _check_template_override_issues(squad_dir: Path) -> list[OverrideIssue]:
    """Return check issues for every ``.overrides/templates/*.md.j2`` override: an error for a
    structurally broken item/role template or one that does not compile, an error for a
    shadowing override with no stamp
    (shadowing-vs-add-only: an add-only override with no bundled counterpart reports nothing), and a
    content-gated drift warning."""
    # Function-local: `_view_tags` sits on the cycle through `_views`, which this package is on.
    from squads import _view_tags as view_tags

    issues: list[OverrideIssue] = []
    tmpl_dir = _template_overrides_dir(squad_dir)
    if not tmpl_dir.is_dir():
        return issues

    for path in sorted(tmpl_dir.rglob("*.md.j2")):
        rel = path.relative_to(tmpl_dir).as_posix()
        display = f".overrides/templates/{rel}"
        try:
            text = _read(path, "template")
        except OverrideReadError as exc:
            issues.append(_issue("error", display, str(exc), "override_loads"))
            continue

        if _is_item_or_role_template(rel):
            issues += [
                _issue(
                    "warn", display, view_tags.out_of_region_view_warning(tag), "view_tag_in_region"
                )
                for tag in view_tags.out_of_region_view_tags(text)
            ]

        # Error: missing required markers (structural breakage).
        if _is_item_or_role_template(rel):
            missing = _missing_required_markers(rel, text)
            if missing:
                # *missing* entries already carry the `sq:` prefix (`find_markers`'s own
                # return shape), so the marker delimiters wrap them as-is.
                tags = ", ".join(f"<!-- {t} -->" for t in missing)
                issues.append(
                    _issue(
                        "error",
                        display,
                        f"override is missing required sq marker(s): {tags} "
                        "(breaks marker-safe editing; add the missing regions)",
                        "override_loads",
                    )
                )
                continue  # Broken → don't also warn about drift

        compile_error = template_compile_error(rel, from_squad=squad_dir)
        if compile_error is not None:
            issues.append(
                _issue(
                    "error",
                    display,
                    f"override template does not compile: {compile_error}",
                    "override_loads",
                )
            )
            continue

        # Stamp obligation: unstamped is an error only when the override shadows a bundled template
        # (the uniform severity contract), and an add-only override reports nothing. Warn: version
        # drift (stamp present, bundled counterpart changed).
        stamp = read_template_stamp(text)
        if stamp is None:
            if _template_override_shadows_bundled(rel):
                issues.append(
                    _issue(
                        "error",
                        display,
                        "override has no squads:override-base stamp; "
                        "run `sq override scaffold --force` to re-scaffold with a stamp, "
                        "or `sq override update` after verifying the content",
                        "override_stamped",
                    )
                )
        elif stamp != __version__ and template_changed_since(rel, stamp):
            issues.append(
                _issue(
                    "warn",
                    display,
                    f"override may be stale: bundled {rel} changed since v{stamp}; "
                    f"run `sq override diff {rel}`, merge, then `sq override update {rel}`",
                    "override_current",
                )
            )
    return issues


def _check_role_toml_override_issues(
    squad_dir: Path,
    role_items_by_slug: Mapping[str, Item],
    catalog: CatalogSource,
    *,
    resolve: bool = True,
) -> list[OverrideIssue]:
    """Return check issues for every ``.overrides/roles/<slug>.toml`` override: an error for a
    shadowing override with no stamp (the uniform severity contract), a content-gated
    drift warning (both only over a base the bundled document declares), and — when *resolve* —
    whatever :func:`_check_role_override_resolves` finds for load-ability."""
    issues: list[OverrideIssue] = []
    role_dir = _role_overrides_dir(squad_dir)
    if not role_dir.is_dir():
        return issues

    for path in sorted(role_dir.glob("*.toml")):
        slug = path.stem
        display = f".overrides/roles/{slug}.toml"
        try:
            text = _read(path, "role")
        except OverrideReadError as exc:
            issues.append(_issue("error", display, str(exc), "override_loads"))
            continue
        stamp = read_toml_stamp(text)
        if stamp is None:
            if _role_override_shadows_bundled(slug, role_items_by_slug, squad_dir):
                issues.append(
                    _issue(
                        "error",
                        display,
                        "role override has no squads:override-base stamp; "
                        "run `sq override update` to re-stamp",
                        "override_stamped",
                    )
                )
        elif (
            stamp != __version__
            and artifact_changed_since(ROLES_KEY, stamp)
            and _role_override_shadows_bundled(slug, role_items_by_slug, squad_dir)
        ):
            issues.append(
                _issue(
                    "warn",
                    display,
                    f"role override may be stale: bundled roles.toml changed since v{stamp}; "
                    f"run `sq override diff --role {slug}`, merge, then "
                    f"`sq override update --role {slug}`",
                    "override_current",
                )
            )
        if resolve:
            issues.extend(
                _check_role_override_resolves(squad_dir, slug, display, role_items_by_slug, catalog)
            )
    return issues


def _check_role_override_resolves(
    squad_dir: Path,
    slug: str,
    display: str,
    role_items_by_slug: Mapping[str, Item],
    catalog: CatalogSource,
) -> list[OverrideIssue]:
    """Report a role override that the surfaces consuming it refuse to load (an unknown key, wrong
    type, model outside the closed vocabulary, or ``slug`` disagreeing with the filename). The
    refusal reaches ``sq sync`` and ``sq role <slug> show`` at exit 1, and role overrides resolve
    lazily, so ``sq check`` (an adopter's CI gate) must report one itself or say "no issues" while
    ``sq sync`` is impossible; workflow and playbook overrides are reported through their loaders.

    It resolves through ``resolve_role_with_base``, the seam both consumers use, so it never claims
    a refusal they do not make or misses one they do: a slug with a roster item gets the base they
    would build (:func:`~squads._roles._resolver.role_base_from_item` with this squad's *catalog*,
    so a project ``.overrides/roles.toml`` is included), and a file with no role under it is a layer
    with no base. Every override file is resolved, not only live roles, since ``sq role <slug>
    show`` reads one for a never-activated bundled role, so the message names which consumer
    refuses.
    """
    from squads._roles._resolver import (
        materialised_base,
        resolve_role_with_base,
        stored_values,
    )

    item = role_items_by_slug.get(slug)
    base_role = materialised_base(item, catalog) if item is not None else None

    try:
        resolve_role_with_base(
            slug, squad_dir, base=base_role, catalog=catalog, stored=stored_values(item)
        )
    except RoleNotFoundError:
        return [
            _issue(
                "error",
                display,
                f"role override has no role under it: no role item and no catalog entry for "
                f"{slug!r} — create the role first, or `sq role add {slug} --file "
                f"{path_from_process_dir(_role_overrides_dir(squad_dir) / f'{slug}.toml')}`",
                "override_loads",
            )
        ]
    except SquadsError as exc:
        return [
            _issue(
                "error",
                display,
                f"role override does not load: {exc} — `sq role {slug} show` refuses now, "
                f"and `sq sync` does too once {slug} is on the roster",
                "override_loads",
            )
        ]
    return []


def _text_or_none(path: Path, files: OverrideFiles) -> str | None:
    """The override's text, or ``None`` when it cannot be read or decoded; the document's loader
    reports that refusal."""
    try:
        return files.text(path)
    except (OSError, UnicodeDecodeError):  # fmt: skip
        return None


def _check_workflow_override_issues(squad_dir: Path, files: OverrideFiles) -> list[OverrideIssue]:
    """Return check issues for the workflow TOML override, via
    :func:`~squads._workflow._loader.workflow_stamp_finding`: an error when it shadows a bundled key
    without a stamp, a content-gated warn for drift, and nothing for an add-only unstamped override
    or one whose bundled counterpart is unchanged. ``sq workflow lint`` uses the same function, so
    the two cannot disagree.
    """
    wf_path = _workflow_override_path(squad_dir)
    if not override_present(wf_path):
        return []

    display = WORKFLOW_OVERRIDE_FILENAME
    text = _text_or_none(wf_path, files)
    if text is None:
        return []  # the loader reports the file
    stamp = read_toml_stamp(text)
    finding = workflow_stamp_finding(squad_dir, stamp, files)
    if finding is None:
        return []
    level, message = finding
    return [_stamp_issue(level, display, message)]


def _check_playbook_override_issues(squad_dir: Path, files: OverrideFiles) -> list[OverrideIssue]:
    """Return check issues for the playbook TOML override (if present) — mirrors
    :func:`_check_workflow_override_issues` exactly, sharing the same stamp-obligation
    decision shape via :func:`playbook_stamp_finding`."""
    pb_path = _playbook_override_path(squad_dir)
    if not override_present(pb_path):
        return []

    display = PLAYBOOK_OVERRIDE_FILENAME
    text = _text_or_none(pb_path, files)
    if text is None:
        return []  # the loader reports the file
    stamp = read_toml_stamp(text)
    finding = playbook_stamp_finding(squad_dir, stamp, files)
    if finding is None:
        return []
    level, message = finding
    return [_stamp_issue(level, display, message)]
