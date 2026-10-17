"""Locate the active squad folder and map IDs/types to on-disk locations.

Resolution order for the active squad folder:
  1. ``--dir PATH`` override (operate on any self-contained squad).
  2. Walk up from cwd to a ``.squads.toml`` and use its ``squad_dir``.
  3. (init only) default ``squads/`` under the chosen root.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from squads._errors import InvalidIdError, NotInitializedError, SquadsError
from squads._models._config import CONFIG_FILENAME, INDEX_FILENAME, LOCK_FILENAME, SquadsConfig
from squads._models._item import prefix_from_id
from squads._workflow._models import WorkflowSpec


def find_config(start: Path | None = None) -> Path | None:
    """Walk up from ``start`` (cwd by default) looking for ``.squads.toml``."""
    cur = (start or Path.cwd()).resolve()
    for d in (cur, *cur.parents):
        candidate = d / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


def load_config(config_path: Path) -> SquadsConfig:
    try:
        with config_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:  # fmt: skip
        # tomllib decodes the bytes internally (before the TOML grammar is ever reached), so
        # a stray non-UTF-8 byte raises UnicodeDecodeError here rather than TOMLDecodeError —
        # config resolution runs before command dispatch, so an unguarded config read fails
        # every command, including the ones an operator would run to diagnose it.
        raise SquadsError(f"malformed {config_path}: {exc}") from exc
    try:
        return SquadsConfig.from_toml_dict(data)
    except ValidationError as exc:
        raise SquadsError(f"invalid {config_path.name}: {exc.errors()[0]['msg']}") from exc


@dataclass(frozen=True)
class SquadPaths:
    """Resolved locations for one active squad."""

    root: Path  # project root (holds .squads.toml)
    squad_dir: Path  # self-contained squad folder (holds .squads.json + type subfolders)
    config: SquadsConfig

    # --- index / lock ---
    @property
    def index_path(self) -> Path:
        return self.squad_dir / INDEX_FILENAME

    @property
    def lock_path(self) -> Path:
        return self.squad_dir / LOCK_FILENAME

    @property
    def config_path(self) -> Path:
        return self.root / CONFIG_FILENAME

    @property
    def reflog_path(self) -> Path:
        """Path to the append-only operation log."""
        return self.squad_dir / ".reflog.jsonl"

    # --- type folders / item files ---
    def folder_for(self, item_type: str, spec: WorkflowSpec | None = None) -> Path:
        """Return the absolute path of the folder for ``item_type``.

        The loaded spec is the sole vocabulary source for every type, built-in or custom
        Raises ``SquadsError`` when ``item_type`` is unknown and no spec is
        provided (or the spec does not declare it).
        """
        if spec is not None and item_type in spec.items:
            return self.squad_dir / spec.items[item_type].folder
        raise SquadsError(
            f"unknown item type {item_type!r} — is this a custom type without a spec?"
        )

    def abspath(self, squad_relative: str) -> Path:
        """Absolute path from a squad-folder-relative item path.

        Guards against path traversal: a ``path`` from a hand-edited index/frontmatter cannot
        escape the squad folder.
        """
        base = self.squad_dir.resolve()
        resolved = (base / squad_relative).resolve()
        if not resolved.is_relative_to(base):
            raise InvalidIdError(f"path {squad_relative!r} escapes the squad folder")
        return self.squad_dir / squad_relative

    def squad_relative(
        self, item_type: str, filename: str, spec: WorkflowSpec | None = None
    ) -> str:
        """Return a squad-folder-relative path string for an item file.

        The loaded spec is the sole vocabulary source for every type, built-in or custom
        Raises ``SquadsError`` when ``item_type`` is unknown and no spec is
        provided (or the spec does not declare it).
        """
        if spec is not None and item_type in spec.items:
            return f"{spec.items[item_type].folder}/{filename}"
        raise SquadsError(
            f"unknown item type {item_type!r} — is this a custom type without a spec?"
        )


def _holds_squad_data(folder: Path) -> bool:
    """Whether *folder* is a squad's own: it has an index, or item files in a subfolder."""
    return (folder / ".squads.json").is_file() or any(folder.glob("*/[A-Za-z]*-[0-9]*-*.md"))


def resolve(
    dir_override: str | None = None,
    *,
    client_cwd: Path | None = None,
) -> SquadPaths:
    """Resolve the active squad: ``--dir`` > ``.squads.toml`` walk-up from the client cwd.

    ``--dir`` names the squad folder: the first ``.squads.toml`` above it must name that
    folder as its ``squad_dir``, else resolution refuses; a folder with no config above it
    that still holds squad data is refused too, and one that holds none gets a default config.

    ``client_cwd`` is the resolution base for the ``.squads.toml`` walk-up — the requesting
    *client's* working directory, not necessarily this process's. Defaults to ``Path.cwd()``
    when omitted, so one-shot CLI use is unchanged (the client cwd IS the process cwd there); a
    caller resolving on behalf of a specific request passes its own client cwd explicitly.
    Irrelevant when ``dir_override`` is given — ``--dir`` never touches any cwd.
    """
    if dir_override:
        squad_dir = Path(dir_override).resolve()
        found = find_config(squad_dir)
        if found is not None:
            config = load_config(found)
            root = found.parent
            if (root / config.squad_dir).resolve() == squad_dir:
                return SquadPaths(root=root, squad_dir=squad_dir, config=config)
            raise SquadsError(
                f"{squad_dir} is not the squad folder of the squad configured at {found} "
                f"(its squad_dir is {config.squad_dir!r}); name that folder with --dir"
            )
        if _holds_squad_data(squad_dir):
            raise SquadsError(
                f"{squad_dir} holds squad data but no .squads.toml above it names it as its "
                "squad folder (a squad_dir outside its project tree is not found from here); "
                "run from the project directory instead"
            )
        root = squad_dir.parent
        return SquadPaths(
            root=root, squad_dir=squad_dir, config=SquadsConfig(squad_dir=squad_dir.name)
        )

    base = client_cwd or Path.cwd()
    config_path = find_config(base)
    if config_path is None:
        raise NotInitializedError(
            "no .squads.toml found in this or any parent directory — run `sq init`"
        )

    root = config_path.parent
    config = load_config(config_path)
    return SquadPaths(root=root, squad_dir=root / config.squad_dir, config=config)


def type_for_id(item_id: str, spec: WorkflowSpec | None = None) -> str:
    """Map an ID (e.g. ``TASK-nnn`` or ``INC-nnn``) back to its item type string.

    Resolves via ``spec.prefix_to_type`` — the loaded spec is the sole vocabulary source
    for every type, built-in or custom. Raises ``InvalidIdError`` when no spec is
    supplied, or the prefix is not recognised by it.
    """
    prefix = prefix_from_id(item_id)
    if spec is not None and prefix in spec.prefix_to_type:
        return spec.prefix_to_type[prefix]
    raise InvalidIdError(f"unknown ID prefix in {item_id!r}")


def number_for_id(item_id: str) -> int:
    try:
        return int(item_id.rsplit("-", 1)[-1])
    except ValueError:
        raise InvalidIdError(f"malformed ID {item_id!r}") from None
