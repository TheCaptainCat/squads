"""The roster operations: roles, skills, operators and developers, each answering with its DTO.

Every addressed operation resolves its address within its own roster kind, and every write that
changes what the managed files list regenerates them before it answers."""

from pathlib import Path

from squads import _pronouns
from squads._api._dto._items import ItemAddress
from squads._api._dto._operators import (
    OperatorAddRequest,
    OperatorList,
    OperatorListRequest,
    OperatorRow,
    OperatorShow,
    OperatorShowDisplay,
    OperatorStatusMove,
    OperatorUpdateRequest,
    OperatorWrite,
)
from squads._api._dto._roles import (
    DeveloperList,
    DeveloperListRequest,
    RoleActivateRequest,
    RoleAddRequest,
    RoleCatalog,
    RoleCatalogRequest,
    RoleDefaultMove,
    RoleList,
    RoleListRequest,
    RoleRow,
    RoleShow,
    RoleShowDisplay,
    RoleStatusMove,
    RoleUpdateRequest,
    RoleViewChange,
    RoleWrite,
)
from squads._api._dto._roster import (
    RosterAddress,
    RosterBodyRequest,
    RosterRemoveRequest,
    RosterStatusRequest,
    SeveredRef,
    ViewRequest,
)
from squads._api._dto._skills import (
    RefEntry,
    SkillAddRequest,
    SkillRefChange,
    SkillRefRemoveRequest,
    SkillRefRequest,
    SkillRefs,
    SkillRefsRequest,
    SkillRoleLink,
    SkillRoleRequest,
    SkillShow,
    SkillShowDisplay,
    SkillStatusMove,
    SkillUpdateRequest,
    SkillViewChange,
    SkillWrite,
)
from squads._api._response import Response
from squads._errors import ItemNotFoundError, RoleNotFoundError
from squads._interactions._role_guidance import allowed_create_types, developer_roles
from squads._interactions._skills import role_origin
from squads._models import _attributes as attrs
from squads._models._attributes import AttributeKey
from squads._models._item import (
    DISPLAY_ID_PADDING,
    Item,
    format_item_id,
    parse_item_token,
    split_ref,
)
from squads._models._vocab import prefix_for
from squads._roles._listing import catalog_listing, catalog_row
from squads._roles._models import DEV_TEMPLATE_NAME
from squads._roles._resolver import (
    materialised_base,
    read_role_toml,
    resolve_pronouns,
    resolve_role_for_item,
    resolve_role_tolerantly,
    resolve_role_with_base,
    role_base_from_item,
    stored_values,
)
from squads._services._item_dto import comment_dtos
from squads._services._item_ops import ItemOpsMixin
from squads._services._refs import RefsMixin
from squads._services._roster import RosterMixin
from squads._services._roster_dto import (
    DEVELOPER_LIST_COLUMNS,
    OPERATOR_LIST_COLUMNS,
    ROLE_LIST_COLUMNS,
    change_role_hint,
    developer_row,
    name_display,
    operator_row,
    role_empty_body_hint,
    role_row,
    severed_refs,
    skill_empty_body_hint,
    skill_row,
    skill_view_name,
)
from squads._services._views import ViewsMixin
from squads._views import ROLE_DEFINITION_VIEW_NAME, empty_body_hint_state
from squads._workflow import ROSTER_OPERATOR, ROSTER_ROLE, ROSTER_SKILL

#: The note the duplicate-id warning carries on a read.
_DUPLICATE_READ_NOTE = "showing the indexed file; run `sq check`"

#: The roster kinds whose entries the managed files list, so a removal regenerates them.
_LISTED_KINDS = frozenset({ROSTER_ROLE, ROSTER_OPERATOR})


def _id_shaped(token: str) -> bool:
    """Whether *token* is a number or has the shape of a full id (``PREFIX-<digits>``)."""
    _, sep, tail = token.rpartition("-")
    return token.isdigit() or (bool(sep) and tail.isdigit())


def _definition(text: str | None, source: str | None) -> dict[str, object] | None:
    """The definition a file's *text* holds, parsed with *source* naming it in messages."""
    if text is None:
        return None
    return read_role_toml(Path(source or "-"), lambda _path: text)


class RosterOpsMixin(ItemOpsMixin, RefsMixin, RosterMixin, ViewsMixin):
    # ------------------------------------------------------------------------- addresses

    async def roster_entry(self, kind: str, addr: str, *, missing: str = "") -> Item:
        """The *kind* entry *addr* names: a number or a full id must be an item of that kind, and
        a slug must be an entry's; *missing* is appended to the refusal of an unknown slug."""
        token = addr.strip()
        if _id_shaped(token):
            seq, given = parse_item_token(token)
            item_id = format_item_id(given or prefix_for(kind, self.spec), seq, DISPLAY_ID_PADDING)
            return await self.addressed_item(ItemAddress(id=item_id, type=kind, address=addr))
        item = await self.roster_item(kind, token)
        if item is None:
            raise ItemNotFoundError(f"no {kind} with slug, ID, or number {addr!r}{missing}")
        return item

    async def _live_role(self, addr: str) -> Item:
        return await self.roster_entry(ROSTER_ROLE, addr, missing=" — activate it first")

    async def _write_target(self, kind: str, addr: str) -> Item:
        """The entry a write addresses, then the declared actor checked against the roster."""
        item = (
            await self._live_role(addr)
            if kind == ROSTER_ROLE
            else await self.roster_entry(kind, addr)
        )
        await self.adopt_declared_actor()
        return item

    async def _duplicate_warnings(self, item: Item) -> list[str]:
        duplicate = await self.duplicate_id_error(item)
        return [] if duplicate is None else [f"{duplicate} -- {_DUPLICATE_READ_NOTE}"]

    def _shows_pronouns(self) -> bool:
        return self.paths.config.display.pronouns

    # ------------------------------------------------------------------------- rows

    def _role_row(self, item: Item) -> RoleRow:
        role = resolve_role_tolerantly(item, self.paths.squad_dir, catalog=self.catalog)
        return role_row(item, role, self.spec, pronouns=self._shows_pronouns())

    def _operator_row(self, item: Item) -> OperatorRow:
        return operator_row(item, pronouns=self._shows_pronouns())

    # ------------------------------------------------------------------------- roles

    async def role_catalog_listing(self, req: RoleCatalogRequest) -> Response[RoleCatalog]:
        """The catalog's roles, then each activated role it does not declare, the live default
        holder marked."""
        roles = self.catalog().roles
        live_default = await self.default_role_slug()
        items = {it.slug: it for it in await self.list_roles()}

        def origin(slug: str) -> str:
            return (attrs.origin(items[slug]) if slug in items else role_origin(slug)) or ""

        resolved = list(roles)
        declared = {r.slug for r in roles}
        resolved += [
            resolve_role_for_item(it, self.paths.squad_dir, catalog=self.catalog)
            for it in items.values()
            if it.slug not in declared
        ]
        rows = [
            catalog_row(
                role,
                is_default=role.slug == live_default,
                origin=origin(role.slug),
                default_role=live_default,
                source="roster",
            )
            for role in resolved
        ]
        return Response(data=catalog_listing(rows))

    async def role_listing(self, req: RoleListRequest) -> Response[RoleList]:
        """The activated roles, each resolved as ``sq role <slug> show`` resolves it."""
        rows = [
            role_row(
                it,
                resolve_role_for_item(it, self.paths.squad_dir, catalog=self.catalog),
                self.spec,
                pronouns=self._shows_pronouns(),
            )
            for it in await self.list_roles()
        ]
        return Response(data=RoleList(items=rows, columns=list(ROLE_LIST_COLUMNS)))

    async def activate_role_entry(self, req: RoleActivateRequest) -> Response[RoleWrite]:
        """Activate a catalog role or build one from a template, then regenerate the managed
        files."""
        await self.adopt_declared_actor()
        item = await self.activate_role(
            req.slug,
            name=req.name,
            model=req.model,
            pronouns=req.pronouns,
            from_template=req.from_template,
            tech=req.tech,
        )
        await self.refresh_managed()
        return Response(data=RoleWrite(entry=self._role_row(item)))

    async def add_role_entry(self, req: RoleAddRequest) -> Response[RoleWrite]:
        """Create a role that defines itself, then regenerate the managed files."""
        await self.adopt_declared_actor()
        item = await self.add_role(
            req.slug,
            name=req.name,
            job_title=req.job_title,
            description=req.description,
            mission=req.mission,
            capabilities=req.capabilities,
            model=req.model,
            pronouns=req.pronouns,
            definition=_definition(req.definition, req.source),
            source=req.source or "the role definition",
        )
        await self.refresh_managed()
        return Response(data=RoleWrite(entry=self._role_row(item)))

    async def show_role_entry(self, req: RosterAddress) -> Response[RoleShow]:
        """A role as resolved: an activated one with its body and discussion, or one the catalog
        declares and nobody activated."""
        token = req.addr.strip()
        it = (
            await self.roster_entry(ROSTER_ROLE, req.addr)
            if _id_shaped(token)
            else await self.roster_item(ROSTER_ROLE, token)
        )
        slug = it.slug if it is not None else req.addr
        base = materialised_base(it, self.catalog) if it is not None else None
        base_resolves = it is None or role_base_from_item(it, self.catalog) is not None
        pronouns = resolve_pronouns(
            _pronouns.pronouns(it) if it is not None else None, self.catalog
        )
        warnings = await self._duplicate_warnings(it) if it is not None else []
        skills = await self.resolved_skills_for_role(slug)
        try:
            role = resolve_role_with_base(
                slug,
                self.paths.squad_dir,
                base=base,
                catalog=self.catalog,
                stored=stored_values(it),
            )
        except RoleNotFoundError:
            raise ItemNotFoundError(f"no role with slug, ID, or number {req.addr!r}") from None
        body = empty_hint = None
        discussion = []
        if it is not None:
            disabled = await self.view_tag_state(it.id, ROLE_DEFINITION_VIEW_NAME) is True
            state = empty_body_hint_state(ROLE_DEFINITION_VIEW_NAME, self.spec, disabled=disabled)
            empty_hint = role_empty_body_hint(state, slug)
            body = await self.read_body(it.id)
            discussion = comment_dtos(await self.comments(it.id))
        shown = name_display(role.full_name, pronouns, enabled=self._shows_pronouns())
        data = RoleShow(
            slug=slug,
            id=it.id if it is not None else None,
            activated=it is not None,
            origin=role_origin(slug) if it is None else attrs.origin(it),
            full_name=role.full_name,
            pronouns=pronouns,
            title=role.title,
            mission=role.mission,
            model=role.model,
            is_default=role.is_default,
            can_spawn=role.can_spawn,
            capabilities=list(role.capabilities),
            create_lane=sorted(allowed_create_types(role, self.spec, self.playbook)),
            responsibilities=list(role.responsibilities),
            skills=skills,
            display=RoleShowDisplay(
                **dict(shown),
                color=role.color,
                body=body,
                empty_hint=empty_hint,
                definition_resolves=base_resolves,
                change_hint=change_role_hint(slug, it, base_resolves),
                discussion=discussion,
            ),
        )
        return Response(data=data, warnings=warnings)

    async def update_role_entry(self, req: RoleUpdateRequest) -> Response[RoleWrite]:
        """Edit a role, then regenerate the managed files; a per-slug file that also sets a
        written field is a warning."""
        item = await self._write_target(ROSTER_ROLE, req.addr)
        result = await self.update_role(
            item.id,
            title=req.title,
            pronouns=req.pronouns,
            model=req.model,
            job_title=req.job_title,
            description=req.description,
            mission=req.mission,
            capabilities=req.capabilities,
            color=req.color,
            can_spawn=req.can_spawn,
            definition=_definition(req.definition, req.source),
            source=req.source or "the role definition",
        )
        await self.refresh_managed()
        return Response(data=RoleWrite(entry=self._role_row(result.item)), warnings=result.warnings)

    async def set_default_role_entry(self, req: RosterAddress) -> Response[RoleDefaultMove]:
        """Move the default designation to the role, clearing every other holder."""
        item = await self._write_target(ROSTER_ROLE, req.addr)
        result = await self.set_default_role(item.id)
        return Response(
            data=RoleDefaultMove(
                entry=self._role_row(result.item), changed=result.changed, cleared=result.cleared
            )
        )

    async def regen_role_entry(self, req: RosterAddress) -> Response[RoleWrite]:
        """Regenerate the role's pointer."""
        item = await self._live_role(req.addr)
        return Response(data=RoleWrite(entry=self._role_row(await self.regen(item.id))))

    async def set_role_body(self, req: RosterBodyRequest) -> Response[RoleWrite]:
        """Set or append to the role's body."""
        item = await self._entry_body(ROSTER_ROLE, req)
        return Response(data=RoleWrite(entry=self._role_row(item)))

    async def move_role_status(self, req: RosterStatusRequest) -> Response[RoleStatusMove]:
        """Move the role to another status."""
        moved, severed, warnings = await self._entry_status(ROSTER_ROLE, req)
        return Response(
            data=RoleStatusMove(entry=self._role_row(moved), severed=severed), warnings=warnings
        )

    async def remove_role_entry(self, req: RosterRemoveRequest) -> Response[RoleWrite]:
        """Delete the role, then regenerate the managed files."""
        removed, warnings = await self._entry_remove(ROSTER_ROLE, req)
        return Response(data=RoleWrite(entry=self._role_row(removed)), warnings=warnings)

    async def add_role_view(self, req: ViewRequest) -> Response[RoleViewChange]:
        """Place or re-enable a view tag in the role's body."""
        item, changed, was_present = await self._entry_view(ROSTER_ROLE, req, enable=True)
        return Response(
            data=RoleViewChange(
                entry=self._role_row(item), view=req.name, changed=changed, was_present=was_present
            )
        )

    async def disable_role_view(self, req: ViewRequest) -> Response[RoleViewChange]:
        """Disable a view tag in the role's body; the tag stays."""
        item, changed, was_present = await self._entry_view(ROSTER_ROLE, req, enable=False)
        return Response(
            data=RoleViewChange(
                entry=self._role_row(item), view=req.name, changed=changed, was_present=was_present
            )
        )

    async def developer_listing(self, req: DeveloperListRequest) -> Response[DeveloperList]:
        """The live roles that hold a capability the catalog's developer template declares."""
        live = self.spec.live_statuses(ROSTER_ROLE)
        items = [it for it in await self.list_items(item_type=ROSTER_ROLE) if it.status in live]
        roles = {
            it.slug: resolve_role_tolerantly(it, self.paths.squad_dir, catalog=self.catalog)
            for it in items
        }
        developers = {r.slug for r in developer_roles(roles.values(), self.catalog())}
        rows = [
            developer_row(it, roles[it.slug], pronouns=self._shows_pronouns())
            for it in items
            if it.slug in developers
        ]
        return Response(
            data=DeveloperList(
                items=rows,
                columns=list(DEVELOPER_LIST_COLUMNS),
                template_available=DEV_TEMPLATE_NAME in self.catalog().templates,
            )
        )

    # ------------------------------------------------------------------------- skills

    async def add_skill_entry(self, req: SkillAddRequest) -> Response[SkillWrite]:
        """Create a skill and its pointer."""
        await self.adopt_declared_actor()
        parent = await self.resolve_any_id(req.parent) if req.parent else None
        item = await self.add_skill(
            req.name,
            description=req.description,
            when_to_use=req.when_to_use,
            allowed_tools=req.allowed_tools,
            parent=parent,
            operator_invocable=req.operator_invocable,
        )
        return Response(data=SkillWrite(entry=skill_row(item, self.spec)))

    async def show_skill_entry(self, req: RosterAddress) -> Response[SkillShow]:
        """A skill with its stored and expanded body, its views and its discussion."""
        it = await self.roster_entry(ROSTER_SKILL, req.addr)
        warnings = await self._duplicate_warnings(it)
        view_name = skill_view_name(it.slug, self.spec)
        disabled = view_name is not None and await self.view_tag_state(it.id, view_name) is True
        row = skill_row(it, self.spec)
        data = SkillShow.model_validate(
            {
                **row.model_dump(),
                "body": await self.read_stored_body(it.id),
                "views": await self.view_data(it.id),
                "display": SkillShowDisplay(
                    body=await self.read_body(it.id),
                    empty_hint=skill_empty_body_hint(
                        it.slug, self.spec, self.playbook, view_disabled=disabled
                    ),
                    discussion=comment_dtos(await self.comments(it.id)),
                ),
            }
        )
        return Response(data=data, warnings=warnings)

    async def update_skill_entry(self, req: SkillUpdateRequest) -> Response[SkillWrite]:
        """Edit a skill's display fields."""
        item = await self._write_target(ROSTER_SKILL, req.addr)
        updated = await self.update(
            item.id,
            title=req.title,
            description=req.description,
            set_attributes=(
                {AttributeKey.WHEN_TO_USE: req.when_to_use} if req.when_to_use is not None else None
            ),
            operator_invocable=req.operator_invocable,
        )
        return Response(data=SkillWrite(entry=skill_row(updated, self.spec)))

    async def skill_refs(self, req: SkillRefsRequest) -> Response[SkillRefs]:
        """The refs the skill carries, the refs carried to it, or both."""
        item = await self.roster_entry(ROSTER_SKILL, req.addr)
        out = in_ = None
        if req.out or not req.incoming:
            out = [RefEntry(id=i, kind=k) for i, k in await self.refs_out(item.id)]
        if req.incoming:
            in_ = [RefEntry(id=i, kind=k) for i, k in await self.refs_in(item.id)]
        return Response(data=SkillRefs.model_validate({"out": out, "in": in_}))

    async def add_skill_ref(self, req: SkillRefRequest) -> Response[SkillRefChange]:
        """Add a ref from the skill; a kind embedded in the target wins over the requested one,
        and without either the default kind applies."""
        item = await self._write_target(ROSTER_SKILL, req.addr)
        raw, embedded = split_ref(req.target)
        target = await self.resolve_any_id(raw)
        kind = embedded or req.kind or self.spec.default_ref_kind()
        updated = await self.add_ref(item.id, target, kind=kind)
        return Response(
            data=SkillRefChange(entry=skill_row(updated, self.spec), target=target, kind=kind)
        )

    async def remove_skill_ref(self, req: SkillRefRemoveRequest) -> Response[SkillRefChange]:
        """Remove the skill's ref to the target, whatever its kind."""
        item = await self._write_target(ROSTER_SKILL, req.addr)
        raw, _ = split_ref(req.target)
        target = await self.resolve_any_id(raw)
        updated = await self.rm_ref(item.id, target)
        return Response(
            data=SkillRefChange(entry=skill_row(updated, self.spec), target=target, kind=None)
        )

    async def link_skill_role(self, req: SkillRoleRequest) -> Response[SkillRoleLink]:
        """Scope the skill to a role and regenerate that role's pointer."""
        item = await self._write_target(ROSTER_SKILL, req.addr)
        role = await self.roster_entry(ROSTER_ROLE, req.role)
        updated = await self.link_role(item.id, role.id)
        return Response(data=SkillRoleLink(entry=skill_row(updated, self.spec), role=role.id))

    async def unlink_skill_role(self, req: SkillRoleRequest) -> Response[SkillRoleLink]:
        """Unscope the skill from a role and regenerate that role's pointer."""
        item = await self._write_target(ROSTER_SKILL, req.addr)
        role = await self.roster_entry(ROSTER_ROLE, req.role)
        updated = await self.unlink_role(item.id, role.id)
        return Response(data=SkillRoleLink(entry=skill_row(updated, self.spec), role=role.id))

    async def regen_skill_entry(self, req: RosterAddress) -> Response[SkillWrite]:
        """Regenerate the skill's pointer."""
        item = await self.roster_entry(ROSTER_SKILL, req.addr)
        return Response(data=SkillWrite(entry=skill_row(await self.regen(item.id), self.spec)))

    async def set_skill_body(self, req: RosterBodyRequest) -> Response[SkillWrite]:
        """Set or append to the skill's body."""
        return Response(
            data=SkillWrite(entry=skill_row(await self._entry_body(ROSTER_SKILL, req), self.spec))
        )

    async def move_skill_status(self, req: RosterStatusRequest) -> Response[SkillStatusMove]:
        """Move the skill to another status."""
        moved, severed, warnings = await self._entry_status(ROSTER_SKILL, req)
        return Response(
            data=SkillStatusMove(entry=skill_row(moved, self.spec), severed=severed),
            warnings=warnings,
        )

    async def remove_skill_entry(self, req: RosterRemoveRequest) -> Response[SkillWrite]:
        """Delete the skill."""
        removed, warnings = await self._entry_remove(ROSTER_SKILL, req)
        return Response(data=SkillWrite(entry=skill_row(removed, self.spec)), warnings=warnings)

    async def add_skill_view(self, req: ViewRequest) -> Response[SkillViewChange]:
        """Place or re-enable a view tag in the skill's body."""
        item, changed, was_present = await self._entry_view(ROSTER_SKILL, req, enable=True)
        return Response(
            data=SkillViewChange(
                entry=skill_row(item, self.spec),
                view=req.name,
                changed=changed,
                was_present=was_present,
            )
        )

    async def disable_skill_view(self, req: ViewRequest) -> Response[SkillViewChange]:
        """Disable a view tag in the skill's body; the tag stays."""
        item, changed, was_present = await self._entry_view(ROSTER_SKILL, req, enable=False)
        return Response(
            data=SkillViewChange(
                entry=skill_row(item, self.spec),
                view=req.name,
                changed=changed,
                was_present=was_present,
            )
        )

    # ------------------------------------------------------------------------- operators

    async def operator_listing(self, req: OperatorListRequest) -> Response[OperatorList]:
        """The registered people."""
        rows = [self._operator_row(it) for it in await self.list_operators()]
        return Response(data=OperatorList(items=rows, columns=list(OPERATOR_LIST_COLUMNS)))

    async def add_operator_entry(self, req: OperatorAddRequest) -> Response[OperatorWrite]:
        """Register a person."""
        await self.adopt_declared_actor()
        item = await self.add_operator(req.name, slug=req.slug, pronouns=req.pronouns)
        return Response(data=OperatorWrite(entry=self._operator_row(item)))

    async def show_operator_entry(self, req: RosterAddress) -> Response[OperatorShow]:
        """A registered person with their body and discussion."""
        it = await self.roster_entry(ROSTER_OPERATOR, req.addr)
        warnings = await self._duplicate_warnings(it)
        own = _pronouns.pronouns(it)
        shown = name_display(it.title, own, enabled=self._shows_pronouns())
        data = OperatorShow(
            id=it.id,
            slug=it.slug,
            full_name=it.title,
            pronouns=own,
            status=it.status,
            path=it.path,
            display=OperatorShowDisplay(
                **dict(shown),
                body=await self.read_body(it.id),
                discussion=comment_dtos(await self.comments(it.id)),
            ),
        )
        return Response(data=data, warnings=warnings)

    async def update_operator_entry(self, req: OperatorUpdateRequest) -> Response[OperatorWrite]:
        """Rename an operator or set their pronouns, then regenerate the managed files."""
        item = await self._write_target(ROSTER_OPERATOR, req.addr)
        updated = await self.update(item.id, title=req.title, pronouns=req.pronouns)
        await self.refresh_managed()
        return Response(data=OperatorWrite(entry=self._operator_row(updated)))

    async def set_operator_body(self, req: RosterBodyRequest) -> Response[OperatorWrite]:
        """Set or append to the operator's body."""
        return Response(
            data=OperatorWrite(
                entry=self._operator_row(await self._entry_body(ROSTER_OPERATOR, req))
            )
        )

    async def move_operator_status(self, req: RosterStatusRequest) -> Response[OperatorStatusMove]:
        """Move the operator to another status."""
        moved, severed, warnings = await self._entry_status(ROSTER_OPERATOR, req)
        return Response(
            data=OperatorStatusMove(entry=self._operator_row(moved), severed=severed),
            warnings=warnings,
        )

    async def remove_operator_entry(self, req: RosterRemoveRequest) -> Response[OperatorWrite]:
        """Delete the operator, then regenerate the managed files."""
        removed, warnings = await self._entry_remove(ROSTER_OPERATOR, req)
        return Response(data=OperatorWrite(entry=self._operator_row(removed)), warnings=warnings)

    # ------------------------------------------------------------------------- shared verbs

    async def _entry_body(self, kind: str, req: RosterBodyRequest) -> Item:
        item = await self._write_target(kind, req.addr)
        return await self.set_body(item.id, req.text, append=req.append, force=req.force)

    async def _entry_status(
        self, kind: str, req: RosterStatusRequest
    ) -> tuple[Item, list[SeveredRef], list[str]]:
        item = await self._write_target(kind, req.addr)
        result = await self.set_roster_status(
            item.id, req.status, force=req.force, unlink=req.unlink
        )
        return result.item, severed_refs(result.severed), result.warnings

    async def _entry_remove(self, kind: str, req: RosterRemoveRequest) -> tuple[Item, list[str]]:
        item = await self._write_target(kind, req.addr)
        removal = await self.remove_item(item.id, purge=req.purge)
        if kind in _LISTED_KINDS:
            await self.refresh_managed()
        return removal.item, removal.warnings

    async def _entry_view(
        self, kind: str, req: ViewRequest, *, enable: bool
    ) -> tuple[Item, bool, bool]:
        item = await self._write_target(kind, req.addr)
        was_present = await self.view_tag_present(item.id, req.name)
        if enable:
            changed = await self.add_view(item.id, req.name)
        else:
            changed = await self.disable_view(item.id, req.name)
        return await self.get(item.id), changed, was_present
