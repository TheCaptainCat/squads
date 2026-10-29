"""Jinja2 environment for generating item files and Claude Code artifacts.

Templates are package data under ``templates/``. ``StrictUndefined`` makes a missing variable
a loud error rather than a silent blank.

Every entry point takes the squad directory whose templates may override the bundled ones
(``from_squad``): templates in ``<squad_dir>/.overrides/templates/`` shadow bundled ones by
name, every other template resolves to the bundled default, and ``None`` means the bundled
templates alone. The Environment is cached per squad directory, LRU-bounded so a long-lived
process serving many squads does not keep one per squad forever; :func:`invalidate_squad_dir`
evicts one.
"""

from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any, cast

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader, StrictUndefined
from jinja2.loaders import split_template_path

from squads import _badges as badges
from squads._errors import SquadsError
from squads._interactions._cheatsheet import (
    ReviewGate,
    cheatsheet_alias_example,
    cheatsheet_anchor_context,
    cheatsheet_anchor_type,
    cheatsheet_review_gate,
)
from squads._interactions._models import PlaybookSpec
from squads._interactions._playbook import authoring_owners, get_playbook_spec, parent_chain
from squads._interactions._role_guidance import (
    example_assignee_slug,
    item_skill_role_sections,
    live_roster_text,
)
from squads._interactions._skills import custom_item_skill_commands
from squads._models import _markers as markers
from squads._models._item import Item
from squads._models._vocab import label_for
from squads._paths import number_for_id
from squads._sections import get_section
from squads._specload import TEMPLATE_OVERRIDE_MESSAGES, override_present, read_override_text
from squads._util import slugify
from squads._workflow import bundled_spec
from squads._workflow._lifecycle_order import linearize_lifecycle
from squads._workflow._models import WorkflowSpec

#: Where a project's own template overrides live, relative to the squad dir — the one place
#: this path is spelled, so a message naming where to author a view template override (e.g.
#: :func:`~squads._views.skill_authoring_surface`) never hand-spells it differently.
TEMPLATES_OVERRIDE_DIR = ".overrides/templates"

#: Cap on distinct squad dirs (plus the bundled-only ``None`` key) kept warm. Unbounded growth
#: of this compiled-template cache would leak an Environment per squad ever touched.
_ENV_CACHE_MAX_SIZE = 16

# Per-squad-dir Environment cache, LRU-bounded at _ENV_CACHE_MAX_SIZE; None is the bundled-only
# environment. Insertion order gives LRU if a hit is re-inserted (pop + set), see _env().
#
# NOT thread-safe: _env()'s hit and evicting-miss paths are each two steps on this dict with no
# lock. That holds only while the async model is one event loop on one OS thread, with no
# `await` inside _env() (the assumption IndexStore's `_proc_mutex` documents). A server that
# calls render() from several OS threads MUST add a lock around _env() first.
_env_cache: dict[Path | None, Environment] = {}


class _OverrideLoader(FileSystemLoader):
    """The project's template overrides; a file at an override path that cannot be read or
    decoded, a directory included, is refused with :class:`OverrideReadError`, not skipped."""

    def get_source(
        self, environment: Environment, template: str
    ) -> tuple[str, str, Callable[[], bool]]:
        for base in self.searchpath:
            path = Path(base, *split_template_path(template))
            if override_present(path):
                read_override_text(path, TEMPLATE_OVERRIDE_MESSAGES)
        return super().get_source(environment, template)


def _make_env(squad_dir: Path | None) -> Environment:
    """Build a Jinja2 Environment for *squad_dir* (or bundled-only when ``None``)."""
    bundled = PackageLoader("squads._rendering", "templates")
    if squad_dir is not None:
        overrides_dir = squad_dir / TEMPLATES_OVERRIDE_DIR
        if overrides_dir.is_dir():
            loader = ChoiceLoader([_OverrideLoader(str(overrides_dir)), bundled])
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
    # "InProgress" | badge → "🟡 In Progress", reusing squads._badges.status_badge: a join or
    # lookup arrives as a registered filter or a new source kind, never as template logic. A
    # second arg ({{ status | badge(spec) }}) selects an overridden spec; without it the
    # bundled vocabulary applies, so a template written without the spec keeps rendering.
    env.filters["badge"] = _badge
    # {{ spec.machine_for(type) | linearize_lifecycle }}: a filter, the extension point for
    # render-time logic, so every playbook-derivation helper shares one calling convention.
    env.filters["linearize_lifecycle"] = linearize_lifecycle  # pyright: ignore[reportArgumentType]
    # DEPRECATED alias kept for scaffolded overrides that call {{ linearize_lifecycle(x) }};
    # drop it only when the project decides such overrides are unsupported.
    env.globals["linearize_lifecycle"] = linearize_lifecycle  # pyright: ignore[reportArgumentType]
    # per-item-type skill helpers — pure functions reachable from
    # templates/views/item_skill.md.j2 (and any adopter override) as filters, never
    # reimplemented in the template itself.
    env.filters["item_skill_role_sections"] = item_skill_role_sections  # pyright: ignore[reportArgumentType]
    env.filters["live_roster_text"] = live_roster_text  # pyright: ignore[reportArgumentType]
    env.filters["custom_item_skill_commands"] = custom_item_skill_commands  # pyright: ignore[reportArgumentType]
    env.filters["label_for"] = label_for  # pyright: ignore[reportArgumentType]
    # playbook helpers — the role->type authoring narrative in workflow.md.j2 renders from the
    # playbook's declared create-lanes + the role catalog + the spec's parent chain, not
    # hardcoded prose.
    env.globals["authoring_owners"] = _authoring_owners  # pyright: ignore[reportArgumentType]
    env.globals["parent_chain"] = parent_chain  # pyright: ignore[reportArgumentType]
    # the "--assignee <who>" value in a generated example block: a slug off the LIVE roster,
    # never a bundled slug literal that exits 1 on a squad that doesn't carry that role.
    env.globals["example_assignee_slug"] = example_assignee_slug  # pyright: ignore[reportArgumentType]
    # the generic "Common commands" example-block anchor type (squads skill, AGENTS.md) —
    # never a hardcoded type literal, so dropping/renaming its previous anchor ("task")
    # still yields a fully runnable example built from whatever type qualifies best.
    env.globals["cheatsheet_anchor_type"] = cheatsheet_anchor_type  # pyright: ignore[reportArgumentType]
    env.globals["cheatsheet_anchor_context"] = cheatsheet_anchor_context  # pyright: ignore[reportArgumentType]
    env.globals["cheatsheet_review_gate"] = _review_gate  # pyright: ignore[reportArgumentType]
    env.globals["cheatsheet_alias_example"] = cheatsheet_alias_example  # pyright: ignore[reportArgumentType]
    # badge-vocabulary helpers — item templates render an active `spec` and derive axis
    # labels/legends/examples from it rather than hardcoding bundled vocab (e.g. severity).
    env.globals["resolve_collection"] = badges.resolve_collection  # pyright: ignore[reportArgumentType]
    env.globals["field_label"] = badges.field_label  # pyright: ignore[reportArgumentType]
    env.globals["field_default"] = badges.field_default  # pyright: ignore[reportArgumentType]
    env.globals["collection_legend"] = badges.collection_legend  # pyright: ignore[reportArgumentType]
    env.globals["primary_field_code"] = badges.primary_field_code  # pyright: ignore[reportArgumentType]
    return env


def _env(squad_dir: Path | None) -> Environment:
    """Return the Environment for *squad_dir* (or bundled-only).

    LRU-bounded at :data:`_ENV_CACHE_MAX_SIZE`: a hit is moved to the most-recently-used
    end (pop + re-insert — relies on dict insertion order); a miss that would push the
    cache past the cap evicts the least-recently-used entry first.
    """
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


def invalidate_squad_dir(squad_dir: Path | None) -> None:
    """Evict the cached Environment for *squad_dir*, forcing a rebuild on next use.

    Useful in tests that mutate ``.overrides/`` after a service is already constructed.
    """
    _env_cache.pop(squad_dir, None)


def _idnum(item_id: str) -> str:
    return str(number_for_id(item_id))


def _authoring_owners(
    item_type: str,
    roster: Iterable[Any] | None,
    playbook: PlaybookSpec | None,
    role_titles: Mapping[str, str] | None = None,
) -> list[tuple[str, str]]:
    """``authoring_owners`` for templates; a render that carries no playbook is a reference
    render and reads the bundled one."""
    active = playbook if playbook is not None else get_playbook_spec()
    return authoring_owners(item_type, roster, active, role_titles)


def _review_gate(
    spec: WorkflowSpec, roster: Iterable[Any] | None, playbook: PlaybookSpec | None
) -> ReviewGate:
    """``cheatsheet_review_gate`` for templates; a render with no playbook reads the bundled one."""
    active = playbook if playbook is not None else get_playbook_spec()
    return cheatsheet_review_gate(spec, roster, active)


def _badge(status_value: str, spec: WorkflowSpec | None = None) -> str:
    return badges.status_badge(status_value, spec if spec is not None else bundled_spec())


def has_template(template_name: str, *, from_squad: Path | None) -> bool:
    """Return True when *template_name* exists in *from_squad*'s environment.

    Used by ``_template_for`` to detect whether a per-type item template exists so
    custom types can fall back to ``items/_default.md.j2`` without raising
    ``TemplateNotFound``.
    """
    from jinja2 import TemplateNotFound

    env = _env(from_squad)
    if env.loader is None:
        return False
    try:
        env.loader.get_source(env, template_name)
    except TemplateNotFound:
        return False
    return True


def creation_template_name(item_type: str, spec: WorkflowSpec, *, from_squad: Path | None) -> str:
    """The Jinja2 template path *item_type*'s creation writes from.

    The create path (:meth:`~squads._services._base.ServiceCore._template_for`, a thin wrapper)
    and the template-seeded-view derivation (:func:`~squads._views.template_seeded_view_names`)
    both read it, so they cannot disagree about which file "the creation template" names. A
    roster type always resolves to ``agents/<type>.md.j2``. Any other declared type resolves to
    ``items/<type>.md.j2`` when one exists (:func:`has_template`, so an override shadowing a
    bundled per-type template is honoured), else to ``items/_default.md.j2``, which lets a custom
    type render at all.
    """
    if spec.item_is_roster(item_type):
        return f"agents/{item_type}.md.j2"
    per_type = f"items/{item_type}.md.j2"
    if has_template(per_type, from_squad=from_squad):
        return per_type
    return "items/_default.md.j2"


def scaffold_body(item: Item, spec: WorkflowSpec, *, from_squad: Path | None) -> str | None:
    """The ``:body`` region a freshly-created *item* would carry: its creation template's
    unwritten scaffold, derived by re-rendering through the squad-aware loader so a per-type
    template, an interpolated field and a project's overriding template are all honoured.
    ``None`` when the template no longer renders for the item; a caller reads that as "assume
    authored", since refusing a first write is recoverable and discarding a real body is not."""
    try:
        rendered = render(
            creation_template_name(item.type, spec, from_squad=from_squad),
            from_squad=from_squad,
            item=item,
            description=item.description,
            spec=spec,
        )
    except SquadsError:
        return None
    return (get_section(rendered, markers.BODY) or "").strip("\n")


def template_source(template_name: str, *, from_squad: Path | None) -> str:
    """*template_name*'s raw source text, through the override-aware loader :func:`render` uses.

    It is never rendered: a caller reading a template's authored content (which ``sq:view:<name>``
    tags its creation scaffold seeds) has no item to render against. Raises :class:`SquadsError`
    wrapping ``jinja2.TemplateNotFound`` when *template_name* does not resolve, as :func:`render`
    does.
    """
    from jinja2 import TemplateNotFound

    env = _env(from_squad)
    if env.loader is None:
        raise SquadsError(f"template {template_name!r} not found (no loader configured)")
    try:
        source, _filename, _uptodate = env.loader.get_source(env, template_name)
    except TemplateNotFound as exc:
        raise SquadsError(f"template {template_name!r} not found") from exc
    return source


def template_compile_error(template_name: str, *, from_squad: Path | None) -> str | None:
    """Why *template_name* does not compile as *from_squad* resolves it, or ``None`` when it
    does: a syntax error or an unknown filter, never a failure that only rendering finds."""
    from jinja2 import TemplateError, TemplateSyntaxError

    try:
        _env(from_squad).get_template(template_name)
    except TemplateSyntaxError as exc:
        return f"line {exc.lineno}: {exc.message}"
    except TemplateError as exc:
        return str(exc)
    return None


class _FlatItem:
    """An item as a template sees it: its fields, and each stored attribute as a field of the
    same name (``item.target_ref``), so a template never reaches into a nested container."""

    def __init__(self, item: Item) -> None:
        self._item = item

    def __getattr__(self, name: str) -> object:
        try:
            return getattr(self._item, name)
        except AttributeError:
            if name in self._item.attributes:
                return self._item.attributes[name]
            raise


def render(template_name: str, /, *, from_squad: Path | None, **context: object) -> str:
    """Render *template_name* against *context* through the one Jinja2 environment.

    *from_squad* selects it. Every rendering path uses it (item scaffolds, backend artifacts,
    view presentation, roster entries, …). A ``jinja2.TemplateError`` (missing template, syntax
    error, or commonly an undefined variable under ``StrictUndefined``) becomes a
    :class:`~squads._errors.SquadsError` here, once: per-consumer translation would let
    consumers disagree about one failure and leave others raising the raw exception. So a typo
    in an overridden creation template and the same typo in a view template give the same clean
    message, not one message and one traceback. A consumer wanting more context catches the
    :class:`SquadsError` and re-raises (see
    :func:`~squads._views.render_resolved_source_or_raise`); one that swallows a failure returns
    its own sentinel (see :func:`scaffold_body`).
    """
    from jinja2 import TemplateError

    if isinstance(context.get("item"), Item):
        context = {**context, "item": _FlatItem(cast("Item", context["item"]))}
    try:
        return _env(from_squad).get_template(template_name).render(**context)
    except TemplateError as exc:
        raise SquadsError(f"template {template_name!r} failed to render: {exc}") from exc
