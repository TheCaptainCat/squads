"""The tracked item — the unit behind every ID."""

from datetime import UTC, datetime
from typing import Any, cast

from pydantic import BaseModel, computed_field

from squads import _clock as clock
from squads._models._enums import ItemType, Priority, Status
from squads._models._subentity import SubEntity
from squads._util import NonEmpty

REF_SEP = ":"
DEFAULT_KIND = "related"

#: The closed vocabulary of ref kinds for 1.0 — exhaustive, no custom-kind escape hatch.
#: See ADR-000049. Consumers: blocks/depends-on → sq blocked; fixes/addresses → sq check
#: task rules; supersedes → decision checks; the rest → navigation.
VALID_REF_KINDS: frozenset[str] = frozenset(
    {
        "related",
        "blocks",
        "depends-on",
        "implements",
        "fixes",
        "addresses",
        "supersedes",
        "duplicates",
    }
)


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
    #: The global counter number — the item's real identity. ``id`` is derived from it + ``type``.
    sequence_id: int
    type: ItemType
    title: NonEmpty
    slug: NonEmpty
    status: Status
    description: str = ""
    parent: str | None = None
    #: The registered agent (role slug) who authored the item.
    author: str | None = None
    assignee: str | None = None
    #: Optional importance, independent of status. Unset means no priority assigned.
    priority: Priority | None = None
    labels: list[str] = []
    #: Forward edges only. Backrefs are computed by inverting these across all items.
    refs: list[str] = []
    #: Body-local sub-entities (stories/subtasks/findings). A given item type hosts exactly one
    #: kind; their prose stays in the markdown markers, their state lives here.
    subentities: list[SubEntity] = []
    #: Squad-folder-relative path to the item's markdown file.
    path: NonEmpty
    created_at: datetime
    updated_at: datetime
    #: Type-specific fields (e.g. agent role config, dev tech, adr context).
    extra: dict[str, Any] = {}

    model_config = {"use_enum_values": False}

    @computed_field
    @property
    def id(self) -> str:
        """The formatted id (``TASK-000007``) — derived from ``type`` + ``sequence_id``.

        Written to frontmatter as the durable human id; reconstructed via ``from_frontmatter``.
        """
        return f"{self.type.prefix}-{self.sequence_id:06d}"

    def to_frontmatter_dict(self) -> dict[str, Any]:
        """The mapping written into the markdown file's YAML frontmatter (durable truth)."""
        data: dict[str, Any] = {
            "id": self.id,
            "sequence_id": self.sequence_id,
            "type": self.type.value,
            "title": self.title,
            "status": self.status.value,
        }
        if self.parent:
            data["parent"] = self.parent
        if self.author:
            data["author"] = self.author
        if self.assignee:
            data["assignee"] = self.assignee
        if self.priority:
            data["priority"] = self.priority.value
        if self.refs:
            data["refs"] = list(self.refs)
        if self.labels:
            data["labels"] = list(self.labels)
        if self.description:
            data["description"] = self.description
        if self.subentities:
            data["subentities"] = [s.to_frontmatter_dict() for s in self.subentities]
        data["created_at"] = clock.iso(self.created_at)
        data["updated_at"] = clock.iso(self.updated_at)
        if self.extra:
            data["extra"] = self.extra
        return data

    @classmethod
    def from_frontmatter(cls, data: dict[str, Any], *, path: str) -> Item:
        """Reconstruct an Item from parsed frontmatter — used by ``sq repair``."""
        return cls(
            sequence_id=data["sequence_id"],
            type=ItemType(data["type"]),
            title=data.get("title", ""),
            slug=data.get("slug") or _slug_from_path(path),
            status=Status(data["status"]),
            description=data.get("description", ""),
            parent=data.get("parent"),
            author=data.get("author"),
            assignee=data.get("assignee"),
            priority=Priority(data["priority"]) if data.get("priority") else None,
            labels=list(data.get("labels", []) or []),
            refs=_read_refs(data),
            subentities=[
                SubEntity.from_frontmatter(s)
                for s in cast("list[dict[str, Any]]", data.get("subentities") or [])
            ],
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
