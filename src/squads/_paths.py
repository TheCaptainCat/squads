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
    with config_path.open("rb") as fh:
        data = tomllib.load(fh)
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


def resolve(dir_override: str | None = None, *, require_init: bool = True) -> SquadPaths:
    """Resolve the active squad. ``require_init=False`` is used by ``init`` itself."""
    if dir_override:
        squad_dir = Path(dir_override).resolve()
        root = squad_dir.parent
        config_path = root / CONFIG_FILENAME
        config = (
            load_config(config_path)
            if config_path.is_file()
            else SquadsConfig(squad_dir=squad_dir.name)
        )
        return SquadPaths(root=root, squad_dir=squad_dir, config=config)

    config_path = find_config()
    if config_path is None:
        if require_init:
            raise NotInitializedError(
                "no .squads.toml found in this or any parent directory — run `sq init`"
            )
        root = Path.cwd().resolve()
        config = SquadsConfig()
        return SquadPaths(root=root, squad_dir=root / config.squad_dir, config=config)

    root = config_path.parent
    config = load_config(config_path)
    return SquadPaths(root=root, squad_dir=root / config.squad_dir, config=config)


def type_for_id(item_id: str, spec: WorkflowSpec | None = None) -> str:
    """Map an ID (e.g. ``TASK-nnn`` or ``INC-nnn``) back to its item type string.

    Resolves via ``spec.prefix_to_type`` — the loaded spec is the sole vocabulary source
    for every type, built-in or custom. Raises ``InvalidIdError`` when no spec is
    supplied, or the prefix is not recognised by it.
    """
    prefix = item_id.split("-", 1)[0]
    if spec is not None and prefix in spec.prefix_to_type:
        return spec.prefix_to_type[prefix]
    raise InvalidIdError(f"unknown ID prefix in {item_id!r}")


def number_for_id(item_id: str) -> int:
    try:
        return int(item_id.rsplit("-", 1)[-1])
    except ValueError:
        raise InvalidIdError(f"malformed ID {item_id!r}") from None
