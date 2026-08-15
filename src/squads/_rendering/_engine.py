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
from squads._interactions import (
    authoring_owner,
    cheatsheet_anchor_context,
    cheatsheet_anchor_type,
    example_assignee_slug,
    parent_chain,
)
from squads._models import _markers as markers
from squads._paths import number_for_id
from squads._util import slugify
from squads._workflow._models import linearize_lifecycle

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
        overrides_dir = squad_dir / ".overrides" / "templates"
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
    # workflow helper — callable as {{ linearize_lifecycle(spec.machine_for(type)) }} in templates
    env.globals["linearize_lifecycle"] = linearize_lifecycle  # pyright: ignore[reportArgumentType]
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


def render(template_name: str, /, **context: object) -> str:
    return _env().get_template(template_name).render(**context)
