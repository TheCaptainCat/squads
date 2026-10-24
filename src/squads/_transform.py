"""View transforms: load a declared function, call it on a resolved source, validate its output.

A transform is declared on a view as ``{ module, function }`` (bundled code, a normal import) or
``{ path, function }`` (an override file under ``<squad-dir>/.overrides/``). It is called as
``fn(source, *, item, spec)`` with only the keywords it declares, and returns plain JSON data
that feeds the view's template as ``data`` and ``show --json`` as ``views.<name>``.

Override files are trusted code. Each one is executed under a module name derived from its
resolved path, held in ``sys.modules`` only while it executes, and remembered only by the
:class:`TransformLoader` that loaded it, which a caller creates per read and drops afterwards.
"""

import copy
import hashlib
import importlib
import importlib.util
import inspect
import math
import sys
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, cast

from pydantic import BaseModel

from squads._errors import SquadsError
from squads._models._item import Item

if TYPE_CHECKING:
    from squads._workflow._models import ViewSpec, ViewTransform, WorkflowSpec

#: The folder, inside the squad directory, an override transform ``path`` resolves against.
OVERRIDES_DIR = ".overrides"

#: What a transform may return inside its top-level dict or list.
type JsonValue = dict[str, JsonValue] | list[JsonValue] | str | int | float | bool | None
#: What a transform must return: a JSON object or array.
type TransformData = dict[str, JsonValue] | list[JsonValue]

_MODULE_NAME_PREFIX = "_squads_view_transform_"
_MAX_DEPTH = 100


class ViewTransformError(SquadsError):
    """Every way a view transform can fail: unresolvable file, failed import, missing or
    refused function, an exception inside it, or output that is not JSON data."""


@dataclass(frozen=True)
class _Loaded:
    function: Callable[..., object]
    own_file: str | None
    takes_item: bool
    takes_spec: bool


def declaration(transform: ViewTransform) -> str:
    """``<path>:<function>`` or ``<module>:<function>``, as error messages name a transform."""
    return f"{transform.path or transform.module}:{transform.function}"


class TransformLoader:
    """Loads and calls the transforms of one read. Create one per read and drop it after: a file
    loaded here is executed once for the read and never outlives it."""

    def __init__(self, squad_dir: Path | None) -> None:
        self._squad_dir = squad_dir
        self._files: dict[Path, ModuleType] = {}

    def run(
        self,
        view_name: str,
        transform: ViewTransform,
        source: object,
        *,
        item: Item,
        spec: WorkflowSpec,
    ) -> TransformData:
        """The validated output of *transform* called on *source* for host *item*."""
        where = _Where(view_name, transform, item.id)
        loaded = self._load(where, transform)
        kwargs: dict[str, object] = {}
        if loaded.takes_item:
            kwargs["item"] = _copy(item)
        if loaded.takes_spec:
            kwargs["spec"] = _copy(spec)
        try:
            value = loaded.function(_copy(source), **kwargs)
        except (Exception, SystemExit) as exc:
            raise where.error(_raised(exc, loaded.own_file)) from exc
        problem = _json_problem(value, "$", ())
        if problem is not None:
            raise where.error(f"returned a value that is not JSON data: {problem}")
        return value  # pyright: ignore[reportReturnType]

    def check(self, view_name: str, transform: ViewTransform) -> str | None:
        """Why *transform* cannot be called, or ``None``. Imports an override file, so its
        top-level code runs; the function itself is never called."""
        try:
            self._load(_Where(view_name, transform, None), transform)
        except ViewTransformError as exc:
            return str(exc)
        return None

    def _load(self, where: _Where, transform: ViewTransform) -> _Loaded:
        if transform.path is not None:
            module = self._load_file(where, transform.path)
        else:
            module = self._import(where, transform.module or "")
        function = getattr(module, transform.function, None)
        if function is None:
            raise where.error(f"module has no attribute {transform.function!r}")
        takes_item, takes_spec = _bind(where, function)
        own_file = getattr(module, "__file__", None)
        return _Loaded(function, own_file, takes_item, takes_spec)

    def _import(self, where: _Where, name: str) -> ModuleType:
        try:
            return importlib.import_module(name)
        except (Exception, SystemExit) as exc:
            raise where.error(f"import failed: {type(exc).__name__}: {exc}") from exc

    def _load_file(self, where: _Where, relative: str) -> ModuleType:
        if self._squad_dir is None:
            raise where.error("no squad directory to resolve the path against")
        from squads._paths import resolve_within

        target, inside = resolve_within(self._squad_dir / OVERRIDES_DIR, relative)
        if not inside:
            raise where.error(f"path resolves to {target}, outside {OVERRIDES_DIR}/")
        if not target.is_file():
            raise where.error(f"{target} is not a file")
        cached = self._files.get(target)
        if cached is not None:
            return cached
        module = _exec_file(where, target)
        self._files[target] = module
        return module


@dataclass(frozen=True)
class _Where:
    """What an error names: the view, the host item (when there is one), the declaration."""

    view: str
    transform: ViewTransform
    host: str | None

    def error(self, cause: str) -> ViewTransformError:
        host = f" on {self.host}" if self.host else ""
        return ViewTransformError(
            f"view {self.view!r}{host} (transform {declaration(self.transform)}): {cause}"
        )


def check_view_transforms(spec: WorkflowSpec, squad_dir: Path) -> list[tuple[str, str]]:
    """``(view name, message)`` for each override transform of *spec* that cannot be called."""
    loader = TransformLoader(squad_dir)
    found: list[tuple[str, str]] = []
    for name, view in sorted(spec.views.items()):
        transform = _path_transform(view)
        if transform is not None and (message := loader.check(name, transform)) is not None:
            found.append((name, message))
    return found


def _path_transform(view: ViewSpec) -> ViewTransform | None:
    transform = view.transform
    return transform if transform is not None and transform.path is not None else None


def _exec_file(where: _Where, target: Path) -> ModuleType:
    name = _MODULE_NAME_PREFIX + hashlib.sha256(str(target).encode()).hexdigest()[:16]
    file_spec = importlib.util.spec_from_file_location(name, target)
    if file_spec is None or file_spec.loader is None:
        raise where.error(f"{target} cannot be loaded as a Python module")
    module = importlib.util.module_from_spec(file_spec)
    sys.modules[name] = module
    try:
        # Compiled from the bytes read now, never through the bytecode cache, so an edit made
        # within the cache's one-second mtime window is still seen.
        exec(compile(target.read_bytes(), str(target), "exec"), module.__dict__)
    except (Exception, SystemExit) as exc:
        raise where.error(f"import failed: {_raised(exc, str(target))}") from exc
    finally:
        sys.modules.pop(name, None)
    return module


def _bind(where: _Where, function: object) -> tuple[bool, bool]:
    """Whether *function* takes ``item`` and ``spec``; refuses anything sq cannot call."""
    if not callable(function):
        raise where.error(f"{where.transform.function!r} is not callable")
    if inspect.iscoroutinefunction(function) or inspect.iscoroutinefunction(
        type(function).__call__
    ):
        raise where.error("an async function cannot be a transform")
    try:
        params = list(inspect.signature(function).parameters.values())
    except (ValueError, TypeError) as exc:
        raise where.error(f"its signature cannot be read: {exc}") from exc
    positional = (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    if not params or (
        params[0].kind not in positional and params[0].kind is not inspect.Parameter.VAR_POSITIONAL
    ):
        raise where.error("its first parameter must accept the source positionally")
    takes = {"item": False, "spec": False}
    for param in params[1:]:
        if param.kind is inspect.Parameter.VAR_KEYWORD:
            takes = dict.fromkeys(takes, True)
        elif param.name in takes and param.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            takes[param.name] = True
        elif param.default is inspect.Parameter.empty and param.kind is not (
            inspect.Parameter.VAR_POSITIONAL
        ):
            raise where.error(f"it requires an unsupported parameter {param.name!r}")
    return takes["item"], takes["spec"]


def _copy(value: object) -> object:
    if isinstance(value, list):
        return [_copy(v) for v in cast("list[object]", value)]
    if isinstance(value, BaseModel):
        return value.model_copy(deep=True)
    return copy.deepcopy(value)


def _raised(exc: BaseException, own_file: str | None) -> str:
    """``Type: message`` plus the last traceback frame inside *own_file*."""
    text = f"{type(exc).__name__}: {exc}"
    frames = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename == own_file]
    if frames:
        text += f" (at {frames[-1].filename}:{frames[-1].lineno})"
    return text


def _json_problem(value: object, path: str, ancestors: tuple[int, ...]) -> str | None:
    """The first way *value* is not JSON data, naming its JSON path; ``None`` when it is."""
    if path == "$" and not isinstance(value, dict | list):
        return f"{path}: the top level must be a dict or a list, not {type(value).__name__}"
    if isinstance(value, dict | list):
        return _container_problem(
            cast("dict[object, object] | list[object]", value), path, ancestors
        )
    return _scalar_problem(value, path)


def _scalar_problem(value: object, path: str) -> str | None:
    if isinstance(value, float) and not math.isfinite(value):
        return f"{path}: {value} is not a finite number"
    if isinstance(value, int):
        try:
            str(value)
        except ValueError:
            return f"{path}: the integer is too large to serialize"
        return None
    if value is None or isinstance(value, str | float):
        return None
    return f"{path}: {type(value).__name__} is not JSON data"


def _container_problem(
    value: dict[object, object] | list[object], path: str, ancestors: tuple[int, ...]
) -> str | None:
    if id(value) in ancestors or len(ancestors) > _MAX_DEPTH:
        return f"{path}: the value refers to itself or nests too deeply"
    inside = (*ancestors, id(value))
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                return f"{path}: key {key!r} is not a str"
            if problem := _json_problem(child, f"{path}.{key}", inside):
                return problem
        return None
    for index, child in enumerate(value):
        if problem := _json_problem(child, f"{path}[{index}]", inside):
            return problem
    return None
