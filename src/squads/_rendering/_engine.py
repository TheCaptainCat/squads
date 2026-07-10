"""Jinja2 environment for generating item files and Claude Code artifacts.

Templates are package data under ``templates/``. ``StrictUndefined`` makes a missing variable a
loud error rather than a silent blank.

Squad-aware lookup
------------------
Call ``set_active_squad_dir(squad_dir)`` before rendering to enable per-file project overrides.
Templates in ``<squad_dir>/.overrides/templates/`` shadow bundled templates by name; every other
template resolves to the bundled package default.  When no squad dir is active the bundled loader
is used directly — identical behaviour to the previous single-loader setup.

The function is idempotent for the same squad dir (the Environment is cached per-path); switching
squad dirs replaces the active one.  Call ``set_active_squad_dir(None)`` to revert to the
bundled-only loader (used by tests that want isolation).
"""

from contextvars import ContextVar
from pathlib import Path

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader, StrictUndefined

from squads import _badges as badges
from squads._interactions import authoring_owner, parent_chain
from squads._models import _markers as markers
from squads._paths import number_for_id
from squads._util import slugify
from squads._workflow._models import linearize_lifecycle

# The active squad directory for this logical call stack. None means bundled-only.
_active_squad_dir: ContextVar[Path | None] = ContextVar("_active_squad_dir", default=None)

# Per-squad-dir Environment cache. None is the bundled-only environment.
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
    # playbook helpers — the role->type authoring narrative in workflow.md.j2 renders from
    # CREATE_LANES + the role catalog + the spec's parent chain, not hardcoded prose.
    env.globals["authoring_owner"] = authoring_owner  # pyright: ignore[reportArgumentType]
    env.globals["parent_chain"] = parent_chain  # pyright: ignore[reportArgumentType]
    # badge-vocabulary helpers — item templates render an active `spec` and derive axis
    # labels/legends/examples from it rather than hardcoding bundled vocab (e.g. severity).
    env.globals["resolve_collection"] = badges.resolve_collection  # pyright: ignore[reportArgumentType]
    env.globals["field_label"] = badges.field_label  # pyright: ignore[reportArgumentType]
    env.globals["field_default"] = badges.field_default  # pyright: ignore[reportArgumentType]
    env.globals["collection_legend"] = badges.collection_legend  # pyright: ignore[reportArgumentType]
    return env


def _env() -> Environment:
    """Return the Environment for the currently-active squad dir (or bundled-only)."""
    squad_dir = _active_squad_dir.get()
    if squad_dir not in _env_cache:
        _env_cache[squad_dir] = _make_env(squad_dir)
    return _env_cache[squad_dir]


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
