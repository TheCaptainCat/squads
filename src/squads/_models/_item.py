"""The tracked item — the unit behind every ID."""

from datetime import UTC, datetime
from typing import Any, cast

from pydantic import BaseModel

from squads import _clock as clock
from squads._models._enums import ItemType, Status
from squads._util import NonEmpty

REF_SEP = ":"
DEFAULT_KIND = "related"


def split_ref(ref: str) -> tuple[str, str]:
    """``"ID"`` → ``(ID, "related")``; ``"ID:kind"`` → ``(ID, kind)``. IDs never contain ``:``."""
    rid, _, kind = ref.partition(REF_SEP)
    return rid, (kind or DEFAULT_KIND)


def make_ref(item_id: str, kind: str = DEFAULT_KIND) -> str:
    """A bare ID for the default kind, else ``"ID:kind"`` (kind carried with the edge)."""
    return item_id if not kind or kind == DEFAULT_KIND else f"{item_id}{REF_SEP}{kind}"


def fold_legacy_kinds(refs: list[str], legacy: dict[str, str]) -> list[str]:
    """Merge a pre-2 ``extra.ref_kinds`` ``{ID: kind}`` map into inline ``ID:kind`` ref strings."""
    return [make_ref(rid, legacy.get(rid, kind)) for rid, kind in (split_ref(r) for r in refs)]


class Item(BaseModel):
    id: NonEmpty
    type: ItemType
    title: NonEmpty
    slug: NonEmpty
    status: Status
    description: str = ""
    parent: str | None = None
    assignee: str | None = None
    labels: list[str] = []
    #: Forward edges only. Backrefs are computed by inverting these across all items.
    refs: list[str] = []
    #: Squad-folder-relative path to the item's markdown file.
    path: NonEmpty
    created_at: datetime
    updated_at: datetime
    #: Type-specific fields (e.g. agent role config, dev tech, adr context).
    extra: dict[str, Any] = {}

    model_config = {"use_enum_values": False}

    def to_frontmatter_dict(self) -> dict[str, Any]:
        """The mapping written into the markdown file's YAML frontmatter (durable truth)."""
        data: dict[str, Any] = {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "status": self.status.value,
        }
        if self.parent:
            data["parent"] = self.parent
        if self.assignee:
            data["assignee"] = self.assignee
        if self.refs:
            data["refs"] = list(self.refs)
        if self.labels:
            data["labels"] = list(self.labels)
        if self.description:
            data["description"] = self.description
        data["created_at"] = clock.iso(self.created_at)
        data["updated_at"] = clock.iso(self.updated_at)
        if self.extra:
            data["extra"] = self.extra
        return data

    @classmethod
    def from_frontmatter(cls, data: dict[str, Any], *, path: str) -> Item:
        """Reconstruct an Item from parsed frontmatter — used by ``sq repair``."""
        return cls(
            id=data["id"],
            type=ItemType(data["type"]),
            title=data.get("title", ""),
            slug=data.get("slug") or _slug_from_path(path),
            status=Status(data["status"]),
            description=data.get("description", ""),
            parent=data.get("parent"),
            assignee=data.get("assignee"),
            labels=list(data.get("labels", []) or []),
            refs=_read_refs(data),
            path=path,
            created_at=_parse_dt(data.get("created_at")),
            updated_at=_parse_dt(data.get("updated_at")),
            extra=_read_extra(data),
        )


def _read_refs(data: dict[str, Any]) -> list[str]:
    """Refs as inline ``ID[:kind]`` strings, folding a pre-2 ``extra.ref_kinds`` map if present."""
    refs: list[str] = list(data.get("refs", []) or [])
    legacy: Any = dict(data.get("extra", {}) or {}).get("ref_kinds")
    if isinstance(legacy, dict):
        return fold_legacy_kinds(refs, cast("dict[str, str]", legacy))
    return refs


def _read_extra(data: dict[str, Any]) -> dict[str, Any]:
    """Item ``extra``, minus the legacy ``ref_kinds`` (now carried inline on the refs)."""
    extra: dict[str, Any] = dict(data.get("extra", {}) or {})
    extra.pop("ref_kinds", None)
    return extra


def _slug_from_path(path: str) -> str:
    name = path.rsplit("/", 1)[-1].removesuffix(".md")
    # strip leading "PREFIX-NNNNNN-"
    parts = name.split("-", 2)
    return parts[2] if len(parts) == 3 else name


def _parse_dt(value: object) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        return datetime.now(UTC).replace(microsecond=0)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt
