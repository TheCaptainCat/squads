"""Jinja2 environment for generating item files and Claude Code artifacts.

Templates are package data under ``templates/``. ``StrictUndefined`` makes a missing variable a
loud error rather than a silent blank.

Squad-aware lookup
------------------
Call ``set_active_squad_dir(squad_dir)`` before rendering to enable per-file project overrides.
Templates in ``<squad_dir>/.overrides/templates/`` shadow bundled templates by name; every other
template resolves to the bundled package default.  When no squad dir is active the bundled loader
is used directly — identical behaviour to the previous single-loader setup.

The function is idempotent for the same squad dir (the Environment is cached per-path, LRU-bounded
so a long-lived process serving many distinct squads doesn't retain an Environment per squad
forever); switching squad dirs replaces the active one.  Call ``set_active_squad_dir(None)`` to
revert to the bundled-only loader (used by tests that want isolation).
"""

from contextvars import ContextVar
from pathlib import Path

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader, StrictUndefined

from squads import _badges as badges
from squads._errors import SquadsError
from squads._interactions import (
    authoring_owner,
    cheatsheet_anchor_context,
    cheatsheet_anchor_type,
    custom_item_skill_commands,
    example_assignee_slug,
    item_skill_role_sections,
    parent_chain,
)
from squads._models import _markers as markers
from squads._models._vocab import label_for
from squads._paths import number_for_id
from squads._util import slugify
from squads._workflow._models import WorkflowSpec, linearize_lifecycle

#: Where a project's own template overrides live, relative to the squad dir — the one place
#: this path is spelled, so a message naming where to author a view template override (e.g.
#: :func:`~squads._views.skill_authoring_surface`) never hand-spells it differently.
TEMPLATES_OVERRIDE_DIR = ".overrides/templates"

# The active squad directory for this logical call stack. None means bundled-only.
_active_squad_dir: ContextVar[Path | None] = ContextVar("_active_squad_dir", default=None)

#: Cap on distinct squad dirs (+ the bundled-only ``None`` key) kept warm at once. A CODE
#: cache (compiled templates), so unbounded growth is a resource leak, not a correctness bug —
#: bound it so a long-lived multi-squad process doesn't retain an Environment (and its
#: per-squad override loader) for every squad it has ever touched.
_ENV_CACHE_MAX_SIZE = 16

# Per-squad-dir Environment cache, LRU-bounded at _ENV_CACHE_MAX_SIZE. None is the
# bundled-only environment. A plain dict (not OrderedDict) is enough: a dict's insertion
# order already gives LRU semantics as long as a hit is re-inserted (pop + set) to move it
# to the most-recently-used end — see _env() below.
#
# NOT thread-safe: _env()'s pop+reinsert (hit) and insert+del (evicting miss) are each two
# steps against this shared dict with no lock. Safe today only because the project's async
# model is pinned to one event loop / one OS thread (anyio_backend="asyncio", no `await`
# inside _env() to interleave on) — the same single-thread assumption IndexStore's Layer 2
# `_proc_mutex` documents. A future thread-pool-backed server calling render() from multiple
# OS threads MUST add a lock around _env() before that model change lands.
_env_cache: dict[Path | None, Environment] = {}


def _make_env(squad_dir: Path | None) -> Environment:
    """Build a Jinja2 Environment for *squad_dir* (or bundled-only when ``None``)."""
    bundled = PackageLoader("squads._rendering", "templates")
    if squad_dir is not None:
        overrides_dir = squad_dir / TEMPLATES_OVERRIDE_DIR
        if overrides_dir.is_dir():
            loader = ChoiceLoader([FileSystemLoader(str(overrides_dir)), bundled])
        else:
            loader = bundled
    else:
        loader = bundled

    env = Environment(
        loader=loader,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
        # Templates render Markdown/TOML/JSON files (never HTML served to a browser), so HTML
        # autoescaping would corrupt output (e.g. turn `>` into `&gt;`). Safe to disable here.
        autoescape=False,
    )
    env.filters["slugify"] = slugify
    # marker helpers so templates emit sq anchors: "tag" | open_marker → "<!-- sq:tag -->"
    env.filters["open_marker"] = markers.open_marker
    env.filters["close_marker"] = markers.close_marker
    env.filters["idnum"] = _idnum  # "PREFIX-000007" | idnum → "7", for `sq task 7 …` hints
    # "InProgress" | badge → "🟡 In Progress" — squads._badges.status_badge reused rather than
    # reimplemented in Jinja (the source-widening decision's guard: a join/lookup arrives as a
    # registered filter or a new source kind, never as logic accreting inside a template).
    # Callable with a second arg for a project's own overridden spec ({{ status | badge(spec) }});
    # with none it degrades to the bundled vocabulary, matching status_badge's own default.
    env.filters["badge"] = badges.status_badge
    # workflow helper — callable as {{ spec.machine_for(type) | linearize_lifecycle }} in
    # templates. A filter, per the sanctioned extension point for render-time logic (a pure
    # function of the spec, exposed to templates rather than reimplemented in Jinja) — not a
    # global, so every registered playbook-derivation helper shares one calling convention.
    env.filters["linearize_lifecycle"] = linearize_lifecycle  # pyright: ignore[reportArgumentType]
    # DEPRECATED one-release compatibility alias for the global-callable form this filter
    # replaced (0.15.0) — the same callable under both entry points, not a second
    # implementation of anything. An adopter who scaffolded workflow.md.j2 on 0.14.x and
    # changed nothing still calls it as {{ linearize_lifecycle(x) }}; removing the global
    # outright breaks that override's render with no recovery but hand-editing the override.
    # Drop this line (and only this line) once 0.15.x is no longer a supported upgrade source.
    env.globals["linearize_lifecycle"] = linearize_lifecycle  # pyright: ignore[reportArgumentType]
    # per-item-type skill helpers — pure functions reachable from
    # templates/views/item_skill.md.j2 (and any adopter override) as filters, never
    # reimplemented in the template itself.
    env.filters["item_skill_role_sections"] = item_skill_role_sections  # pyright: ignore[reportArgumentType]
    env.filters["custom_item_skill_commands"] = custom_item_skill_commands  # pyright: ignore[reportArgumentType]
    env.filters["label_for"] = label_for  # pyright: ignore[reportArgumentType]
    # playbook helpers — the role->type authoring narrative in workflow.md.j2 renders from the
    # playbook's declared create-lanes + the role catalog + the spec's parent chain, not
    # hardcoded prose.
    env.globals["authoring_owner"] = authoring_owner  # pyright: ignore[reportArgumentType]
    env.globals["parent_chain"] = parent_chain  # pyright: ignore[reportArgumentType]
    # the "--assignee <who>" value in a generated example block: a slug off the LIVE roster,
    # never a bundled slug literal that exits 1 on a squad that doesn't carry that role.
    env.globals["example_assignee_slug"] = example_assignee_slug  # pyright: ignore[reportArgumentType]
    # the generic "Common commands" example-block anchor type (squads skill, AGENTS.md) —
    # never a hardcoded type literal, so dropping/renaming its previous anchor ("task")
    # still yields a fully runnable example built from whatever type qualifies best.
    env.globals["cheatsheet_anchor_type"] = cheatsheet_anchor_type  # pyright: ignore[reportArgumentType]
    env.globals["cheatsheet_anchor_context"] = cheatsheet_anchor_context  # pyright: ignore[reportArgumentType]
    # badge-vocabulary helpers — item templates render an active `spec` and derive axis
    # labels/legends/examples from it rather than hardcoding bundled vocab (e.g. severity).
    env.globals["resolve_collection"] = badges.resolve_collection  # pyright: ignore[reportArgumentType]
    env.globals["field_label"] = badges.field_label  # pyright: ignore[reportArgumentType]
    env.globals["field_default"] = badges.field_default  # pyright: ignore[reportArgumentType]
    env.globals["collection_legend"] = badges.collection_legend  # pyright: ignore[reportArgumentType]
    env.globals["primary_field_code"] = badges.primary_field_code  # pyright: ignore[reportArgumentType]
    return env


def _env() -> Environment:
    """Return the Environment for the currently-active squad dir (or bundled-only).

    LRU-bounded at :data:`_ENV_CACHE_MAX_SIZE`: a hit is moved to the most-recently-used
    end (pop + re-insert — relies on dict insertion order); a miss that would push the
    cache past the cap evicts the least-recently-used entry first.
    """
    squad_dir = _active_squad_dir.get()
    if squad_dir in _env_cache:
        env = _env_cache.pop(squad_dir)
        _env_cache[squad_dir] = env
        return env
    env = _make_env(squad_dir)
    _env_cache[squad_dir] = env
    if len(_env_cache) > _ENV_CACHE_MAX_SIZE:
        oldest = next(iter(_env_cache))
        del _env_cache[oldest]
    return env


def set_active_squad_dir(squad_dir: Path | None) -> None:
    """Set the squad dir used by ``render()`` for the current logical call stack.

    Pass ``None`` to revert to bundled-only resolution.  Calling with the same path a second time
    is a no-op (the cached Environment is reused).  The cache entry for a squad dir is evicted
    when ``invalidate_squad_dir(squad_dir)`` is called, or when the process exits.
    """
    _active_squad_dir.set(squad_dir)


def invalidate_squad_dir(squad_dir: Path | None) -> None:
    """Evict the cached Environment for *squad_dir*, forcing a rebuild on next use.

    Useful in tests that mutate ``.overrides/`` after a service is already constructed.
    """
    _env_cache.pop(squad_dir, None)


def _idnum(item_id: str) -> str:
    return str(number_for_id(item_id))


def has_template(template_name: str) -> bool:
    """Return True when *template_name* exists in the active environment's loader.

    Used by ``_template_for`` to detect whether a per-type item template exists so
    custom types can fall back to ``items/_default.md.j2`` without raising
    ``TemplateNotFound``.
    """
    from jinja2 import TemplateNotFound

    env = _env()
    if env.loader is None:
        return False
    try:
        env.loader.get_source(env, template_name)
    except TemplateNotFound:
        return False
    return True


def creation_template_name(item_type: str, spec: WorkflowSpec) -> str:
    """The Jinja2 template path *item_type*'s creation writes from — the one resolution the
    create path (:meth:`~squads._services._base.ServiceCore._template_for`, a thin wrapper
    over this) and the template-seeded-view derivation
    (:func:`~squads._views.template_seeded_view_names`) both read, so the two can never
    disagree about which file "the creation template" names.

    A roster type (role/skill/operator) always resolves to its dedicated
    ``agents/<type>.md.j2``. Every other declared type resolves to its dedicated
    ``items/<type>.md.j2`` when one exists (checked via :func:`has_template`, so a project
    override shadowing a bundled per-type template is honoured), else the generic
    ``items/_default.md.j2`` fallback that lets a custom type render at all.
    """
    if spec.item_is_roster(item_type):
        return f"agents/{item_type}.md.j2"
    per_type = f"items/{item_type}.md.j2"
    if has_template(per_type):
        return per_type
    return "items/_default.md.j2"


def template_source(template_name: str) -> str:
    """*template_name*'s raw source text, resolved through the same override-aware loader
    :func:`render` uses — never rendered, since a caller reading a template's own authored
    content (which ``sq:view:<name>`` tags its creation scaffold seeds statically) has no item
    to render against and a render would need a context this question does not have.

    Raises :class:`SquadsError` wrapping ``jinja2.TemplateNotFound`` when *template_name*
    doesn't resolve — the same failure :func:`render` converts, for the same reason.
    """
    from jinja2 import TemplateNotFound

    env = _env()
    if env.loader is None:
        raise SquadsError(f"template {template_name!r} not found (no loader configured)")
    try:
        source, _filename, _uptodate = env.loader.get_source(env, template_name)
    except TemplateNotFound as exc:
        raise SquadsError(f"template {template_name!r} not found") from exc
    return source


def render(template_name: str, /, **context: object) -> str:
    """Render *template_name* against *context* through the one Jinja2 environment every
    rendering path in the codebase uses (item-file scaffolds, backend artifacts,
    declared-view presentation, roster entries, …).

    A ``jinja2.TemplateError`` — a missing template, a syntax error, or (the common case) an
    undefined-variable failure under ``StrictUndefined`` — is translated into
    :class:`~squads._errors.SquadsError` **here**, once, rather than at each consumer:
    translating per-consumer instead lets two consumers disagree about the same failure, and
    leaves every other renderer propagating the raw jinja2 exception. The adopter-visible
    property this gives: a typo in an overridden item-creation template and the identical typo
    in a view template surface identically — the same clean message, not one clean message and
    one traceback. A consumer that wants a more specific message catches this
    :class:`SquadsError` and re-raises with its own context (see
    :func:`~squads._views._render_resolved_source_or_raise`); a consumer that wants to swallow
    a rendering
    failure entirely catches it and returns its own sentinel (see
    :meth:`~squads._services._base.ServiceCore.pristine_body`).
    """
    from jinja2 import TemplateError

    try:
        return _env().get_template(template_name).render(**context)
    except TemplateError as exc:
        raise SquadsError(f"template {template_name!r} failed to render: {exc}") from exc
