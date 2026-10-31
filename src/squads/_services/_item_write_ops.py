"""The item write operations: create, update, body, retype, remove, refs and views, the comment
verbs of every discussion host, and the sub-entity writes, each answering with the resource it
wrote."""

from collections.abc import Mapping, Sized
from typing import Any, cast

from squads import _actor as actor
from squads import _badges as badges
from squads import _discussion as discussion
from squads._api._dto._comment_writes import (
    CommentAdded,
    CommentAddRequest,
    CommentEdited,
    CommentEditRequest,
    CommentRequest,
    CommentSelection,
    CommentShown,
    RosterCommentAddRequest,
    RosterCommentEditRequest,
    RosterCommentRequest,
    SubentityCommentAddRequest,
    SubentityCommentEditRequest,
    SubentityCommentRequest,
)
from squads._api._dto._comments import Comments
from squads._api._dto._item_writes import (
    AddedDisplay,
    ItemBodyRequest,
    ItemCreated,
    ItemCreateRequest,
    ItemRefAdded,
    ItemRefRemoved,
    ItemRefRemoveRequest,
    ItemRefRequest,
    ItemRemoved,
    ItemRemoveRequest,
    ItemRetyped,
    ItemRetypeRequest,
    ItemUpdated,
    ItemUpdateRequest,
    ItemViewChanged,
    ItemViewRequest,
    ItemWritten,
    SubentityAdded,
    SubentityAddRequest,
    SubentityBodyRequest,
    SubentityRemoved,
    SubentityRemoveRequest,
    SubentityUpdated,
    SubentityUpdateRequest,
    SubentityWritten,
)
from squads._api._dto._items import ItemRow
from squads._api._dto._roster import RosterAddress
from squads._api._dto._subentities import SubentityRequest, SubentityShow
from squads._api._response import Response
from squads._errors import SquadsError
from squads._models._item import Item, make_ref, split_ref
from squads._models._metadata import coerce_attribute, require_settable
from squads._services._item_dto import comment_dtos, item_display, item_row, row_fields
from squads._services._item_ops import ItemOpsMixin
from squads._services._item_read_ops import ItemReadOpsMixin
from squads._services._results import FoundComment
from squads._services._retype import RetypeMixin
from squads._services._roster_ops import RosterOpsMixin
from squads._workflow import ROSTER_OPERATOR, ROSTER_ROLE, ROSTER_SKILL

#: A discussion's address: the item id and, for a sub-entity's, its ``(kind, local id)``.
type Host = tuple[Item, tuple[str, str] | None]


def _asked(*values: object) -> bool:
    """Whether any value was given: a flag when true, a list or mapping when non-empty, any other
    value when not ``None``."""
    return any(
        bool(cast(Sized, v)) if isinstance(v, list | dict) else v not in (None, False)
        for v in values
    )


def _shown(found: FoundComment) -> CommentShown:
    first = found.group[0]
    return CommentShown.model_validate(
        {
            **discussion.comment_json(first, found.shown),
            "item": found.item.id,
            "scope": found.scope or None,
            "copies": len(found.group),
        }
    )


def _group(
    item: Item, scope: str, comments: list[discussion.Comment], shown: str
) -> CommentSelection:
    return CommentSelection.model_validate(
        {
            "items": [discussion.comment_json(c, shown) for c in comments],
            "item": item.id,
            "scope": scope or None,
        }
    )


class RetypeOpsMixin(ItemOpsMixin, RetypeMixin):
    async def retype_item(self, req: ItemRetypeRequest) -> Response[ItemRetyped]:
        """Reclassify the item, keeping its number."""
        item = await self.addressed_item(req)
        await self.adopt_declared_actor()
        res = await self.retype(item.id, req.target)
        names = await self.display_names()
        retyped = ItemRetyped(
            entry=item_row(res.item, self.spec, names),
            old_id=res.old_id,
            old_status=res.old_status,
            status_reset=res.status_reset,
            rewritten=[str(path) for path in res.rewritten],
        )
        return Response(data=retyped)


class ItemWriteOpsMixin(ItemReadOpsMixin, RosterOpsMixin):
    # ------------------------------------------------------------------------- rows

    async def _row(self, item: Item) -> ItemRow:
        """*item*'s row."""
        return item_row(item, self.spec, await self.display_names())

    # ------------------------------------------------------------------------- items

    def _coerced_create_attributes(
        self, item_type: str, given: Mapping[str, str | list[str]]
    ) -> dict[str, Any] | None:
        """The attributes a create request carries, each checked as ``update --set`` checks it:
        settable on the type and parsed to its kind by the same function (a list splits on commas
        and drops blanks, a date is ISO). A list of values is refused for a single-valued
        attribute."""
        declared = self.spec.item_attributes(item_type)
        out: dict[str, Any] = {}
        for key, value in given.items():
            if isinstance(value, list):
                if require_settable(item_type, key, declared).kind != "list":
                    raise SquadsError(f"{key!r} takes one value, not a list")
                value = ",".join(value)
            out[key] = coerce_attribute(item_type, key, value, declared)
        return out or None

    async def create_item(self, req: ItemCreateRequest) -> Response[ItemCreated]:
        """Create the item, written by its author, who must be a live participant."""
        author = await self.resolve_participant(req.author)
        actor.set_actor(author)
        assignee = await self.resolve_participant(req.assignee) if req.assignee else None
        parent = await self.resolve_any_id(req.parent) if req.parent is not None else None
        refs: list[str] = []
        for token in req.refs:
            target, kind = split_ref(token)
            refs.append(make_ref(await self.resolve_any_id(target), kind))
        res = await self.create(
            req.type,
            req.title,
            description=req.description,
            parent=parent,
            author=author,
            labels=req.labels or None,
            refs=refs or None,
            assignee=assignee,
            fields=req.fields or None,
            attributes=self._coerced_create_attributes(req.type, req.attributes),
            body=req.body,
        )
        names = await self.display_names()
        created = ItemCreated.model_validate(
            {
                **row_fields(res.item, self.spec),
                "lane_warning": res.lane_warning,
                "badges": badges.resolve_badges(self.spec, res.item.type, res.item.badge_value),
                "display": {
                    **dict(item_display(res.item, self.spec, names)),
                    "file": str(res.path),
                },
            }
        )
        return Response(data=created)

    async def update_item(self, req: ItemUpdateRequest) -> Response[ItemUpdated]:
        """Change the fields the request gives; clearing an assignee the item does not have is
        dropped, and alone it writes nothing."""
        item = await self.addressed_item(req)
        await self.adopt_declared_actor()
        clear_assignee = req.clear_assignee
        if clear_assignee and item.assignee is None:
            others = (
                req.title, req.description, req.author, req.status, req.parent, req.clear_parent,
                req.add_labels, req.rm_labels,
                req.set_attributes, req.unset_attributes,
            )  # fmt: skip
            if not _asked(*others):
                return Response(
                    data=ItemUpdated(entry=await self._row(item), nothing_to_clear=True)
                )
            clear_assignee = False
        assignee = await self.resolve_participant(req.assignee) if req.assignee else None
        author = await self.resolve_participant(req.author) if req.author else None
        parent = await self.resolve_any_id(req.parent) if req.parent is not None else None
        updated = await self.update(
            item.id,
            title=req.title,
            description=req.description,
            assignee=assignee,
            clear_assignee=clear_assignee,
            add_labels=req.add_labels or None,
            rm_labels=req.rm_labels or None,
            author=author,
            status=req.status,
            force=req.force,
            parent=parent,
            clear_parent=req.clear_parent,
            set_attributes=dict(req.set_attributes) or None,
            unset_attributes=req.unset_attributes or None,
        )
        return Response(data=ItemUpdated(entry=await self._row(updated), nothing_to_clear=False))

    async def set_item_body(self, req: ItemBodyRequest) -> Response[ItemWritten]:
        """Set or append to the item's body."""
        item = await self.addressed_item(req)
        await self.adopt_declared_actor()
        written = await self.set_body(item.id, req.text, append=req.append, force=req.force)
        return Response(data=ItemWritten(entry=await self._row(written)))

    async def remove_work_item_entry(self, req: ItemRemoveRequest) -> Response[ItemRemoved]:
        """Delete the item for good."""
        item = await self.addressed_item(req)
        await self.adopt_declared_actor()
        res = await self.remove_work_item(item.id, force=req.force)
        return Response(data=ItemRemoved(removed_id=res.removed_id, severed_refs=res.severed_refs))

    async def add_item_ref(self, req: ItemRefRequest) -> Response[ItemRefAdded]:
        """Add a ref from the item to the target, of the kind the target or the request names,
        else of the default kind."""
        item = await self.addressed_item(req)
        await self.adopt_declared_actor()
        token, embedded = split_ref(req.target)
        target = await self.resolve_any_id(token)
        kind = embedded or req.kind or self.spec.default_ref_kind()
        changed = await self.add_ref(item.id, target, kind=kind)
        return Response(data=ItemRefAdded(entry=await self._row(changed), target=target, kind=kind))

    async def remove_item_ref(self, req: ItemRefRemoveRequest) -> Response[ItemRefRemoved]:
        """Remove the item's refs to the target, answering the kind of each ref removed."""
        item = await self.addressed_item(req)
        await self.adopt_declared_actor()
        target = await self.resolve_any_id(split_ref(req.target)[0])
        changed = await self.rm_ref(item.id, target)
        remaining = list(changed.refs)
        kinds: list[str] = []
        for ref in item.refs:
            if ref in remaining:
                remaining.remove(ref)
            else:
                kinds.append(split_ref(ref)[1] or self.spec.default_ref_kind())
        return Response(
            data=ItemRefRemoved(entry=await self._row(changed), target=target, kinds=kinds)
        )

    async def add_item_view(self, req: ItemViewRequest) -> Response[ItemViewChanged]:
        """Place or re-enable a view tag in the item's body."""
        return Response(data=await self._item_view(req, enable=True))

    async def disable_item_view(self, req: ItemViewRequest) -> Response[ItemViewChanged]:
        """Disable a view tag in the item's body; the tag stays."""
        return Response(data=await self._item_view(req, enable=False))

    async def _item_view(self, req: ItemViewRequest, *, enable: bool) -> ItemViewChanged:
        item = await self.addressed_item(req)
        await self.adopt_declared_actor()
        was_present = await self.view_tag_present(item.id, req.name)
        if enable:
            changed = await self.add_view(item.id, req.name)
        else:
            changed = await self.disable_view(item.id, req.name)
        return ItemViewChanged(
            entry=await self._row(await self.get(item.id)),
            view=req.name,
            changed=changed,
            was_present=was_present,
        )

    # ------------------------------------------------------------------------- comments

    async def _item_host(self, req: CommentAddRequest | CommentRequest) -> Host:
        return await self.addressed_item(req), None

    async def _subentity_host(
        self, req: SubentityCommentAddRequest | SubentityCommentRequest
    ) -> Host:
        item = await self.addressed_item(req)
        return item, (self._hosted_kind(item, req.kind), req.local)

    async def _roster_host(self, kind: str, req: RosterAddress) -> Host:
        if kind == ROSTER_ROLE:
            return await self._live_role(req.addr), None
        return await self.roster_entry(kind, req.addr), None

    async def _add_comment(self, host: Host, texts: list[str]) -> Response[CommentAdded]:
        item, sub = host
        await self.adopt_declared_actor()
        written = await self.comment(item.id, texts, as_slug=actor.current_actor(), sub=sub)
        found = await self.find_comment(item.id, written, sub=sub)
        return Response(data=CommentAdded(entry=_shown(found)))

    async def _show_comment(self, host: Host, token: str) -> Response[CommentShown]:
        item, sub = host
        return Response(data=_shown(await self.find_comment(item.id, token, sub=sub)))

    async def _edit_comment(
        self, host: Host, token: str, texts: list[str]
    ) -> Response[CommentEdited]:
        item, sub = host
        await self.adopt_declared_actor()
        res = await self.edit_comment(item.id, token, texts, as_slug=actor.current_actor(), sub=sub)
        edited = CommentEdited.model_validate(
            {
                **discussion.comment_json(res.new, res.new_shown),
                "item": res.item.id,
                "scope": res.scope or None,
                "changed": res.changed,
                "previous": discussion.comment_json(res.old, res.old_shown),
            }
        )
        return Response(data=edited)

    async def _comment_removal(self, host: Host, token: str) -> Response[CommentSelection]:
        item, sub = host
        await self.adopt_declared_actor()
        slug = actor.current_actor()
        found = await self.find_comment(item.id, token, sub=sub, as_slug=slug)
        return Response(data=_group(found.item, found.scope, found.group, found.shown))

    async def _remove_comment(self, host: Host, token: str) -> Response[CommentSelection]:
        item, sub = host
        await self.adopt_declared_actor()
        slug = actor.current_actor()
        await self.find_comment(item.id, token, sub=sub, as_slug=slug)
        res = await self.remove_comment(item.id, token, as_slug=slug, sub=sub)
        return Response(data=_group(res.item, res.scope, res.removed, res.shown))

    async def add_item_comment(self, req: CommentAddRequest) -> Response[CommentAdded]:
        """Add a comment to the item's discussion."""
        return await self._add_comment(await self._item_host(req), req.texts)

    async def show_item_comment(self, req: CommentRequest) -> Response[CommentShown]:
        """One comment of the item's discussion."""
        return await self._show_comment(await self._item_host(req), req.hash)

    async def edit_item_comment(self, req: CommentEditRequest) -> Response[CommentEdited]:
        """Replace a comment's text in the item's discussion."""
        return await self._edit_comment(await self._item_host(req), req.hash, req.texts)

    async def item_comment_removal(self, req: CommentRequest) -> Response[CommentSelection]:
        """The comments a removal by this hash would delete from the item's discussion."""
        return await self._comment_removal(await self._item_host(req), req.hash)

    async def remove_item_comment(self, req: CommentRequest) -> Response[CommentSelection]:
        """Delete a comment from the item's discussion."""
        return await self._remove_comment(await self._item_host(req), req.hash)

    async def add_subentity_comment(
        self, req: SubentityCommentAddRequest
    ) -> Response[CommentAdded]:
        """Add a comment to the sub-entity's discussion."""
        return await self._add_comment(await self._subentity_host(req), req.texts)

    async def show_subentity_comment(self, req: SubentityCommentRequest) -> Response[CommentShown]:
        """One comment of the sub-entity's discussion."""
        return await self._show_comment(await self._subentity_host(req), req.hash)

    async def edit_subentity_comment(
        self, req: SubentityCommentEditRequest
    ) -> Response[CommentEdited]:
        """Replace a comment's text in the sub-entity's discussion."""
        return await self._edit_comment(await self._subentity_host(req), req.hash, req.texts)

    async def subentity_comment_removal(
        self, req: SubentityCommentRequest
    ) -> Response[CommentSelection]:
        """The comments a removal by this hash would delete from the sub-entity's discussion."""
        return await self._comment_removal(await self._subentity_host(req), req.hash)

    async def remove_subentity_comment(
        self, req: SubentityCommentRequest
    ) -> Response[CommentSelection]:
        """Delete a comment from the sub-entity's discussion."""
        return await self._remove_comment(await self._subentity_host(req), req.hash)

    async def _roster_comments(self, kind: str, req: RosterAddress) -> Response[Comments]:
        item, _ = await self._roster_host(kind, req)
        return Response(data=Comments(items=comment_dtos(await self.comments(item.id))))

    async def role_comments(self, req: RosterAddress) -> Response[Comments]:
        """The role's discussion."""
        return await self._roster_comments(ROSTER_ROLE, req)

    async def add_role_comment(self, req: RosterCommentAddRequest) -> Response[CommentAdded]:
        """Add a comment to the role's discussion."""
        return await self._add_comment(await self._roster_host(ROSTER_ROLE, req), req.texts)

    async def show_role_comment(self, req: RosterCommentRequest) -> Response[CommentShown]:
        """One comment of the role's discussion."""
        return await self._show_comment(await self._roster_host(ROSTER_ROLE, req), req.hash)

    async def edit_role_comment(self, req: RosterCommentEditRequest) -> Response[CommentEdited]:
        """Replace a comment's text in the role's discussion."""
        host = await self._roster_host(ROSTER_ROLE, req)
        return await self._edit_comment(host, req.hash, req.texts)

    async def role_comment_removal(self, req: RosterCommentRequest) -> Response[CommentSelection]:
        """The comments a removal by this hash would delete from the role's discussion."""
        return await self._comment_removal(await self._roster_host(ROSTER_ROLE, req), req.hash)

    async def remove_role_comment(self, req: RosterCommentRequest) -> Response[CommentSelection]:
        """Delete a comment from the role's discussion."""
        return await self._remove_comment(await self._roster_host(ROSTER_ROLE, req), req.hash)

    async def skill_comments(self, req: RosterAddress) -> Response[Comments]:
        """The skill's discussion."""
        return await self._roster_comments(ROSTER_SKILL, req)

    async def add_skill_comment(self, req: RosterCommentAddRequest) -> Response[CommentAdded]:
        """Add a comment to the skill's discussion."""
        return await self._add_comment(await self._roster_host(ROSTER_SKILL, req), req.texts)

    async def show_skill_comment(self, req: RosterCommentRequest) -> Response[CommentShown]:
        """One comment of the skill's discussion."""
        return await self._show_comment(await self._roster_host(ROSTER_SKILL, req), req.hash)

    async def edit_skill_comment(self, req: RosterCommentEditRequest) -> Response[CommentEdited]:
        """Replace a comment's text in the skill's discussion."""
        host = await self._roster_host(ROSTER_SKILL, req)
        return await self._edit_comment(host, req.hash, req.texts)

    async def skill_comment_removal(self, req: RosterCommentRequest) -> Response[CommentSelection]:
        """The comments a removal by this hash would delete from the skill's discussion."""
        return await self._comment_removal(await self._roster_host(ROSTER_SKILL, req), req.hash)

    async def remove_skill_comment(self, req: RosterCommentRequest) -> Response[CommentSelection]:
        """Delete a comment from the skill's discussion."""
        return await self._remove_comment(await self._roster_host(ROSTER_SKILL, req), req.hash)

    async def operator_comments(self, req: RosterAddress) -> Response[Comments]:
        """The operator's discussion."""
        return await self._roster_comments(ROSTER_OPERATOR, req)

    async def add_operator_comment(self, req: RosterCommentAddRequest) -> Response[CommentAdded]:
        """Add a comment to the operator's discussion."""
        return await self._add_comment(await self._roster_host(ROSTER_OPERATOR, req), req.texts)

    async def show_operator_comment(self, req: RosterCommentRequest) -> Response[CommentShown]:
        """One comment of the operator's discussion."""
        return await self._show_comment(await self._roster_host(ROSTER_OPERATOR, req), req.hash)

    async def edit_operator_comment(self, req: RosterCommentEditRequest) -> Response[CommentEdited]:
        """Replace a comment's text in the operator's discussion."""
        host = await self._roster_host(ROSTER_OPERATOR, req)
        return await self._edit_comment(host, req.hash, req.texts)

    async def operator_comment_removal(
        self, req: RosterCommentRequest
    ) -> Response[CommentSelection]:
        """The comments a removal by this hash would delete from the operator's discussion."""
        host = await self._roster_host(ROSTER_OPERATOR, req)
        return await self._comment_removal(host, req.hash)

    async def remove_operator_comment(
        self, req: RosterCommentRequest
    ) -> Response[CommentSelection]:
        """Delete a comment from the operator's discussion."""
        host = await self._roster_host(ROSTER_OPERATOR, req)
        return await self._remove_comment(host, req.hash)

    # ------------------------------------------------------------------------- sub-entities

    def _field_values(self, kind: str, given: dict[str, str]) -> dict[str, str]:
        """The badge code of each field *kind* declares: the one given, else the field's
        default."""
        values: dict[str, str] = {}
        for field in self.spec.fields_for(kind):
            value = given.get(field.code) or self.field_default(kind, field.code)
            if not value:
                continue
            collection = badges.resolve_collection(kind, field.code, self.spec)
            declared = self.spec.collections.get(collection)
            code = value.strip().lower()
            if declared is None or code not in declared.badge_codes:
                choices = ", ".join(b.code for b in declared.badges) if declared else ""
                raise SquadsError(f"unknown {collection} {value!r} (one of: {choices})")
            values[field.code] = code
        return values

    async def _subentity_show(self, item: Item, kind: str, local: str) -> SubentityShow:
        shown = await self.show_subentity(SubentityRequest(id=item.id, kind=kind, local=local))
        return shown.data

    async def add_subentity(self, req: SubentityAddRequest) -> Response[SubentityAdded]:
        """Scaffold a sub-entity of the requested kind on the item; an omitted field takes its
        default."""
        item = await self.addressed_item(req)
        await self.adopt_declared_actor()
        self._check_type(item, req.kind)
        assignee = await self.resolve_participant(req.assignee) if req.assignee else None
        fields = self._field_values(req.kind, req.fields)
        deferred_to = await self.resolve_any_id(req.deferred_to) if req.deferred_to else None
        res = await self.add_block(
            item.id,
            req.kind,
            req.title,
            maps_to=req.maps_to,
            fields=fields or None,
            assignee=assignee,
            status=req.status,
            deferred_to=deferred_to,
            body=req.body,
        )
        added = SubentityAdded(
            local_id=res.local_id,
            path=str(res.path),
            region=res.body_tag,
            start_line=res.start_line,
            end_line=res.end_line,
            title_advisory=res.title_advisory,
            display=AddedDisplay(item=item.id, body_command=res.body_command),
        )
        return Response(data=added)

    async def update_subentity(self, req: SubentityUpdateRequest) -> Response[SubentityUpdated]:
        """Change the sub-entity's fields the request gives; clearing an assignee it does not have
        is dropped, and alone it writes nothing."""
        item = await self.addressed_item(req)
        await self.adopt_declared_actor()
        kind = self._hosted_kind(item, req.kind)
        clear_assignee = req.clear_assignee
        current = (await self.get_block(item.id, kind, req.local)).info
        nothing = False
        if clear_assignee and current.assignee is None:
            others = (
                req.title, req.fields, req.unset_fields, req.maps_to, req.clear_maps_to,
                req.status, req.deferred_to,
            )  # fmt: skip
            nothing = not _asked(*others)
            clear_assignee = False
        if not nothing:
            assignee = await self.resolve_participant(req.assignee) if req.assignee else None
            deferred_to = await self.resolve_any_id(req.deferred_to) if req.deferred_to else None
            await self.update_block(
                item.id,
                kind,
                req.local,
                title=req.title,
                fields=dict(req.fields) or None,
                unset_fields=req.unset_fields or None,
                maps_to=req.maps_to,
                clear_maps_to=req.clear_maps_to,
                assignee=assignee,
                clear_assignee=clear_assignee,
                status=req.status,
                deferred_to=deferred_to,
                force=req.force,
            )
        shown = await self._subentity_show(item, kind, req.local)
        updated = SubentityUpdated(entry=shown, nothing_to_clear=nothing)
        return Response(data=updated)

    async def set_subentity_body(self, req: SubentityBodyRequest) -> Response[SubentityWritten]:
        """Set or append to the sub-entity's body."""
        item = await self.addressed_item(req)
        await self.adopt_declared_actor()
        kind = self._hosted_kind(item, req.kind)
        await self.set_block_body(
            item.id, kind, req.local, req.text, append=req.append, force=req.force
        )
        return Response(
            data=SubentityWritten(entry=await self._subentity_show(item, kind, req.local))
        )

    async def remove_subentity(self, req: SubentityRemoveRequest) -> Response[SubentityRemoved]:
        """Delete the sub-entity with its body and discussion."""
        item = await self.addressed_item(req)
        await self.adopt_declared_actor()
        kind = self._hosted_kind(item, req.kind)
        await self.remove_block(item.id, kind, req.local)
        return Response(data=SubentityRemoved(removed=f"{kind} {req.local}", item=item.id))
