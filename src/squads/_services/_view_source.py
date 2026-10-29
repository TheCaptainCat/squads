"""A declared view's source resolved against an item, in the shape of the command the source
comes from, built by that command's own projection: ``sq tree --json`` nodes for a ``ref`` or
``subtree`` source, a sub-entity listing's rows for ``subentity``, ``sq role show --json`` for
``role``, ``sq show --json`` plus the spec's identity for ``self``, and the lane and roster for
``playbook``."""

import hashlib
import json
from typing import TYPE_CHECKING, cast

from squads._api._dto._items import ItemShowRequest
from squads._api._dto._roster import RosterAddress
from squads._api._dto._subentities import SubentityEntry
from squads._api._dto._tree import TreeNode
from squads._api._dto._workflow import (
    ItemShowWithSpec,
    PlaybookLane,
    PlaybookLaneRole,
    PlaybookRosterEntry,
    PlaybookView,
    SpecIdentity,
    ViewSource,
)
from squads._api._response import Response
from squads._models._item import Item
from squads._models._schema import SCHEMA_VERSION
from squads._models._subentity import SubEntity
from squads._paths import number_for_id
from squads._services import _results as results
from squads._services._item_dto import participant_names
from squads._services._item_read_dto import subentity_entry, tree_node
from squads._specload import override_present
from squads._views import PlaybookSource, children_by_parent
from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME

if TYPE_CHECKING:
    from squads._services._service import Service


def _subtree(item: Item, by_parent: dict[str, list[Item]], seen: set[str]) -> results.TreeNode:
    """*item* with every descendant, closed ones too, by number; *seen* stops a parent cycle."""
    children: list[results.TreeNode] = []
    for child in sorted(by_parent.get(item.id, []), key=lambda i: number_for_id(i.id)):
        if child.id not in seen:
            seen.add(child.id)
            children.append(_subtree(child, by_parent, seen))
    return results.TreeNode(item=item, path_only=False, children=children)


async def _tree_source(svc: Service, records: list[Item]) -> list[TreeNode]:
    blocked_ids = {t.id for t, _ in await svc.blocked()}
    db = await svc.store.load()
    by_parent = children_by_parent(db)
    names = participant_names(db)
    pronouns = await svc.shown_pronouns()
    return [
        tree_node(
            _subtree(r, by_parent, {r.id}),
            svc.spec,
            names,
            blocked_ids=blocked_ids,
            pronouns=pronouns,
            sort=None,
        )
        for r in records
    ]


async def _subentity_source(svc: Service, kind: str, subs: list[SubEntity]) -> list[SubentityEntry]:
    db = await svc.store.load()
    names = participant_names(db)
    entries: list[SubentityEntry] = []
    for sub in subs:
        carrier = db.get(sub.deferred_to) if sub.deferred_to else None
        title = carrier.title if carrier is not None else None
        entries.append(subentity_entry(kind, sub, title, svc.spec, names))
    return entries


def _playbook_source(source: PlaybookSource) -> PlaybookView:
    lane = source.lane
    return PlaybookView(
        type=source.item_type,
        lane=None
        if lane is None
        else PlaybookLane(
            overview=lane.overview,
            lifecycle=lane.lifecycle,
            commands=list(lane.commands),
            roles=[
                PlaybookLaneRole(
                    slug=rg.slug,
                    enter=list(rg.enter),
                    do=list(rg.do),
                    handoff=list(rg.handoff),
                    watch=list(rg.watch),
                    authors=rg.authors,
                )
                for rg in lane.roles
            ],
        ),
        roster=[
            PlaybookRosterEntry(
                slug=rv.slug,
                full_name=rv.full_name,
                title=rv.title,
                is_default=rv.is_default,
                mission=rv.mission,
                responsibilities=list(rv.responsibilities),
                capabilities=list(rv.capabilities),
            )
            for rv in source.roster
        ],
    )


async def _self_source(svc: Service, item: Item, view_name: str) -> Response[ItemShowWithSpec]:
    """The item as ``sq show --json`` prints it, with the view's own tag left in its body, plus
    the spec's identity."""
    response = await svc.show_item(ItemShowRequest(id=item.id), keep_view=view_name)
    shown = response.data
    canonical = json.dumps(
        svc.spec.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")
    )
    spec = SpecIdentity(
        schema_version=SCHEMA_VERSION,
        override=override_present(svc.paths.squad_dir / WORKFLOW_OVERRIDE_FILENAME),
        digest=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )
    return Response(
        data=ItemShowWithSpec.model_validate({**dict(shown), "spec": spec}),
        warnings=response.warnings,
    )


async def view_source(svc: Service, view_name: str, item_id: str) -> Response[ViewSource]:
    """*view_name*'s source resolved against *item_id*, in the shape of its own command, with
    the warnings that command's read carries."""
    view, item, result = await svc.resolve_view_source(view_name, item_id)
    match view.source.kind:
        case "ref" | "subtree":
            return Response(data=await _tree_source(svc, cast("list[Item]", result)))
        case "subentity":
            kind = view.source.name or ""
            rows = await _subentity_source(svc, kind, cast("list[SubEntity]", result))
            return Response(data=rows)
        case "role":
            address = RosterAddress(addr=item.slug)
            role = await svc.show_role_entry(address, keep_view=view_name)
            return Response(data=role.data, warnings=role.warnings)
        case "playbook":
            return Response(data=_playbook_source(cast(PlaybookSource, result)))
        case _:
            shown = await _self_source(svc, item, view_name)
            return Response(data=shown.data, warnings=shown.warnings)
