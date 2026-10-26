"""One load path for the spec documents: the workflow spec, the role catalog and the playbook.

A :class:`SpecDocument` says where a document lives (the packaged file and the project override
beside it), which top-level keys and ``[selected]`` sections its override may carry, and the
wording of its read errors. :func:`bundled_raw` reads the packaged file; :func:`load_override`
reads the project override, merges it over a base mapping fail-fast and refuses a merge that
reports nothing. Each document's own loader builds and validates the model, since what is
checked and how a failure is worded differs per document.

The packaged file is parsed once per process; :func:`bundled_raw` hands each caller its own
copy, so the bundled model and every merged model come from the same read.
"""

import copy
import functools
import importlib.resources
import threading
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import cast

from squads._errors import SquadsError
from squads._specmerge import Deselection, MergeResult, RawMapping, merge_override


class OverrideReadError(SquadsError):
    """A project override that cannot be read or parsed; ``fix_hint`` is the document's own
    remedy, when it has one."""

    def __init__(self, message: str, fix_hint: str | None = None):
        super().__init__(message)
        self.fix_hint = fix_hint


@dataclass(frozen=True)
class OverrideMessages:
    """The wording of a document's override read errors; ``{path}`` and ``{exc}`` are filled in."""

    malformed: str
    unreadable: str
    not_utf8: str
    malformed_hint: str | None = None
    unreadable_hint: str | None = None


@dataclass(frozen=True)
class SpecDocument:
    """Where a spec document lives and how its project override merges over it."""

    bundled_file: str
    override_file: str
    override_name: str
    top_level_keys: frozenset[str]
    selected_sections: frozenset[str]
    messages: OverrideMessages
    empty_selected_hint: str | None = None
    #: Raises ``SquadsError`` on an override that must be refused before it is merged.
    check_override: Callable[[RawMapping, str], None] | None = None
    #: Converts a mapping into the keyed form the merge engine works on, and back.
    to_merge_form: Callable[[RawMapping, str], RawMapping] | None = None
    from_merge_form: Callable[[RawMapping], RawMapping] | None = None


@dataclass(frozen=True)
class MergedOverride:
    """A project override merged over its base: the merged mapping, the override file it came
    from, and the keys it deselected."""

    raw: RawMapping
    origin: str
    deselections: tuple[Deselection, ...]
    #: The override document as written, before the merge.
    override: RawMapping


def bundled_bytes(document: SpecDocument) -> bytes:
    """The packaged file's bytes."""
    try:
        pkg = importlib.resources.files("squads._specs")
        return (pkg / document.bundled_file).read_bytes()
    except Exception as exc:
        raise SquadsError(f"Failed to read bundled {document.bundled_file}: {exc}") from exc


def bundled_text(document: SpecDocument) -> str:
    """The packaged file's raw text."""
    return bundled_bytes(document).decode()


@functools.cache
def _parse_bundled(document: SpecDocument) -> RawMapping:
    """The packaged file parsed, once per process; callers take it through :func:`bundled_raw`."""
    try:
        return tomllib.loads(bundled_text(document))
    except tomllib.TOMLDecodeError as exc:
        raise SquadsError(f"Malformed bundled {document.bundled_file}: {exc}") from exc


def bundled_raw(document: SpecDocument) -> RawMapping:
    """A copy of the packaged file's parse, not yet built into a model — the merge engine's
    ``base``. The copy keeps a caller's edits out of every other caller's view."""
    return copy.deepcopy(_parse_bundled(document))


def override_text(path: Path, files: OverrideFiles | None) -> str:
    """The UTF-8 text of the override at *path*, through *files* when given."""
    return files.text(path) if files is not None else path.read_text(encoding="utf-8")


def override_mapping(path: Path, files: OverrideFiles | None) -> RawMapping:
    """A copy of the override at *path* parsed, through *files* when given so the file is read and
    parsed once; raises what reading or parsing it raised."""
    if files is None:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    return copy.deepcopy(files.parsed(path))


def override_present(path: Path) -> bool:
    """Whether anything sits at an override path, a directory or a dangling link included: such an
    entry is read, and refused by :func:`read_override_text`, never taken for an absent file."""
    return path.exists() or path.is_symlink()


def _refusal(exc: Exception, messages: OverrideMessages, path: Path) -> OverrideReadError:
    """The :class:`OverrideReadError` worded by *messages* for a failed read or parse of *path*."""
    if isinstance(exc, tomllib.TOMLDecodeError):
        return OverrideReadError(
            messages.malformed.format(path=path, exc=exc), messages.malformed_hint
        )
    if isinstance(exc, UnicodeDecodeError):
        return OverrideReadError(messages.not_utf8.format(path=path, exc=exc))
    return OverrideReadError(
        messages.unreadable.format(path=path, exc=exc), messages.unreadable_hint
    )


def read_override_text(
    path: Path, messages: OverrideMessages, files: OverrideFiles | None = None
) -> str:
    """The UTF-8 text of the override at *path*; the one read every kind of override file goes
    through. Raises :class:`OverrideReadError` worded by *messages* when it cannot be read,
    decoded or is not a file."""
    try:
        return override_text(path, files)
    except (OSError, UnicodeDecodeError) as exc:  # fmt: skip
        raise _refusal(exc, messages, path) from exc


def read_override(
    document: SpecDocument, path: Path, files: OverrideFiles | None = None
) -> RawMapping:
    """The project override at *path*, parsed; read through *files* when given. Raises
    :class:`OverrideReadError` worded by *document* when it cannot be read or parsed."""
    try:
        return override_mapping(path, files)
    except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError) as exc:  # fmt: skip
        raise _refusal(exc, document.messages, path) from exc


#: The wording for a per-role override (``.overrides/roles/<slug>.toml``) and for a template
#: override (``.overrides/templates/…``).
ROLE_OVERRIDE_MESSAGES = OverrideMessages(
    malformed="malformed role override {path}: {exc}",
    unreadable="Cannot read role override {path}: {exc}",
    not_utf8="Role override {path} is not valid UTF-8; save it as UTF-8 and re-run.",
)
TEMPLATE_OVERRIDE_MESSAGES = OverrideMessages(
    malformed="Malformed template override {path}: {exc}",
    unreadable="Cannot read template override {path}: {exc}",
    not_utf8="Template override {path} is not valid UTF-8; save it as UTF-8 and re-run.",
)


def merge_collecting(
    document: SpecDocument, base: RawMapping, raw_override: RawMapping, origin: str
) -> MergeResult:
    """Merge *raw_override* over *base* and report every violation rather than the first."""
    return merge_override(
        base,
        raw_override,
        document.selected_sections,
        origin,
        top_level_keys=document.top_level_keys,
        collect_all=True,
        empty_selected_hint=document.empty_selected_hint,
    )


def load_override(
    document: SpecDocument,
    squad_dir: Path | None,
    base: Callable[[], RawMapping],
    files: OverrideFiles | None = None,
) -> MergedOverride | None:
    """The project override merged over ``base()``, or ``None`` when *squad_dir* is ``None`` or
    holds no override file for *document*.

    Fail-fast: the first violation raises ``SquadsError``.
    """
    if squad_dir is None:
        return None
    path = squad_dir / document.override_file
    if not override_present(path):
        return None
    raw_override = read_override(document, path, files)
    origin = str(path)
    if document.check_override is not None:
        document.check_override(raw_override, origin)
    merge_in = document.to_merge_form
    base_label = f"<bundled {document.bundled_file}>"
    result = merge_override(
        merge_in(base(), base_label) if merge_in else base(),
        merge_in(raw_override, origin) if merge_in else raw_override,
        document.selected_sections,
        origin,
        top_level_keys=document.top_level_keys,
        collect_all=False,
        empty_selected_hint=document.empty_selected_hint,
    )
    merged = result.merged
    if merged is None:
        # Unreachable in fail-fast mode: merge_override raises on its own first violation before
        # ever returning one. Fails closed rather than asserting, matching the "never a
        # traceback" contract even for a case that should not occur.
        raise SquadsError(
            f"{document.override_name} merge failed with no violation reported — {origin}"
        )
    out = document.from_merge_form(merged) if document.from_merge_form else merged
    return MergedOverride(
        raw=out, origin=origin, deselections=result.deselections, override=raw_override
    )


class Lazy[T]:
    """A value built on first use and kept: later calls return it, or raise the error the build
    raised (a ``SquadsError``, an ``OSError`` or a ``ValueError``), so a failing document is read
    once and fails the same way each time."""

    def __init__(self, build: Callable[[], T]) -> None:
        self._build = build
        self._value: T | None = None
        self._error: Exception | None = None
        self._traceback: TracebackType | None = None
        self._done = False
        self._lock = threading.Lock()

    def __call__(self) -> T:
        with self._lock:
            if not self._done:
                try:
                    self._value = self._build()
                except (SquadsError, OSError, ValueError) as exc:  # fmt: skip
                    self._error, self._traceback = exc, exc.__traceback__
                self._done = True
        if self._error is not None:
            raise self._error.with_traceback(self._traceback)
        return cast("T", self._value)


class OverrideFiles:
    """The override files one invocation reads, each opened at most once: a later read of the
    same path gets the text, or the error, the first read produced."""

    def __init__(self) -> None:
        self._reads: dict[Path, Lazy[str]] = {}
        self._parses: dict[Path, Lazy[RawMapping]] = {}

    def text(self, path: Path) -> str:
        """The UTF-8 text of *path*; raises what reading it raised."""
        read = self._reads.setdefault(path, Lazy(lambda: path.read_text(encoding="utf-8")))
        return read()

    def parsed(self, path: Path) -> RawMapping:
        """The TOML parse of *path*, shared by every reader: callers copy it before editing."""
        parse = self._parses.setdefault(path, Lazy(lambda: tomllib.loads(self.text(path))))
        return parse()
