"""Agent roster: activating bundled roles, on-demand stack developers, and skills."""

from dataclasses import replace
from typing import Any

from squads import _actor as actor
from squads import _clock as clock
from squads import _pronouns
from squads._errors import RoleNotFoundError, SquadsError
from squads._index._resolver import item_file, require_item
from squads._itemfile import update_frontmatter
from squads._models import _attributes as attrs
from squads._models._attributes import ORIGIN_PROJECT, AttributeKey, parse_invocable_choice
from squads._models._item import Item
from squads._paths import path_from_process_dir
from squads._pronouns import checked_pronouns
from squads._roles._catalog import RoleDef, refuse_blank_name
from squads._roles._loader import ROLES_OVERRIDE_FILENAME
from squads._roles._models import CAPABILITY_NAME_PATTERN, malformed_capability_names
from squads._roles._resolver import (
    holds_default_designation,
    merge_definition_delta,
    model_problem,
    override_file_keys,
    override_full_name,
    resolve_role,
    resolve_role_for_item,
    role_base_from_item,
    role_from_definition,
)
from squads._roles._templates import proposed_name, proposed_slug, takes_parameter
from squads._services._base import ServiceCore
from squads._services._results import (
    DefaultRoleMoveResult,
    MineRow,
    RoleUpdateResult,
    WorkloadRow,
)
from squads._specmerge import RawMapping
from squads._util import (
    legacy_operator_slug,
    legacy_slugify,
    operator_slug,
    slugify,
)
from squads._workflow import ROSTER_OPERATOR, ROSTER_ROLE, ROSTER_SKILL


class RosterMixin(ServiceCore):
    async def activate_role(
        self,
        slug: str | None,
        *,
        name: str | None = None,
        model: str | None = None,
        pronouns: str | None = None,
        from_template: str | None = None,
        tech: str | None = None,
    ) -> Item:
        """Activate a role the catalog declares, or build one from a role template
        (``from_template``, with its ``tech``); ``name`` overrides the catalog or template name. The
        returned role is live: an existing live catalog role is returned untouched
        (``init``/``adopt`` rely on that), a retired one is refused (revive it with ``sq role <slug>
        status``), and a template role whose slug is taken is refused.
        """
        own_pronouns = checked_pronouns(pronouns)
        self._refuse_invalid_model(model)
        if from_template is not None:
            return await self._activate_from_template(
                slug, from_template, tech=tech, name=name, model=model, pronouns=own_pronouns
            )
        if slug is None:
            raise SquadsError("name the role to activate: `sq role activate <slug>`")
        if tech is not None:
            raise SquadsError("--tech applies to a role built with --from <template>")
        existing = await self.roster_item(ROSTER_ROLE, slug)
        if existing is not None:
            return self._existing_role(
                existing, slug, name=name, model=model, pronouns=own_pronouns
            )
        role = self._catalog_role(slug)
        return await self._create_role(
            role.slug,
            role.full_name if name is None else name,
            attributes={**self._model_attribute(model), **self._pronouns_attribute(own_pronouns)},
        )

    def _existing_role(
        self,
        existing: Item,
        slug: str,
        *,
        name: str | None,
        model: str | None,
        pronouns: str | None,
    ) -> Item:
        """The outcome of activating a role that already has an item: a live one is returned
        untouched (a retired one is refused, as is any value asking for a change)."""
        if existing.status not in self.spec.live_statuses(ROSTER_ROLE):
            raise SquadsError(
                f"role {slug!r} already exists and is {existing.status} ({existing.id}); "
                f"`activate` creates a role, it does not revive one — "
                f"run `sq role {slug} status {self.spec.live_initial(ROSTER_ROLE)}`"
            )
        asked = [
            flag
            for flag, given, stored in (
                ("--name", name, existing.title),
                ("--model", model, attrs.model(existing)),
                ("--pronouns", pronouns, _pronouns.pronouns(existing)),
            )
            if given is not None and given != stored
        ]
        if asked:
            raise SquadsError(
                f"role {slug!r} is already active; change {', '.join(asked)} with "
                f"`sq role {slug} update {asked[0]} <value>`"
            )
        return existing

    def _catalog_role(self, slug: str) -> RoleDef:
        """The catalog entry for *slug* with any per-slug file laid over it. A slug only a
        per-slug file declares is refused with the command that turns the file into a role."""
        try:
            return resolve_role(slug, self.paths.squad_dir, catalog=self.catalog)
        except RoleNotFoundError:
            path = self.paths.squad_dir / ".overrides" / "roles" / f"{slug}.toml"
            if path.is_file():
                raise SquadsError(
                    f"role {slug!r} is declared only by .overrides/roles/{slug}.toml, which "
                    "layers over a role and does not define one; create the role with "
                    f"`sq role add {slug} --file {path_from_process_dir(path)}`"
                ) from None
            raise

    async def _activate_from_template(
        self,
        slug: str | None,
        template_name: str,
        *,
        tech: str | None,
        name: str | None,
        model: str | None,
        pronouns: str | None,
    ) -> Item:
        templates = self.catalog().templates
        template = templates.get(template_name)
        if template is None:
            declared = ", ".join(sorted(templates)) or "none"
            raise SquadsError(
                f"no role template {template_name!r}; the declared templates are: {declared}"
            )
        parameter = takes_parameter(template)
        label = (tech or "").strip()
        if parameter and not label:
            raise SquadsError(f"role template {template_name!r} takes a technology: pass --tech")
        if not parameter and tech is not None:
            raise SquadsError(f"role template {template_name!r} takes no --tech")
        chosen = slug if slug is not None else proposed_slug(template, label or None)
        if chosen is None:
            raise SquadsError(
                f"role template {template_name!r} declares no slug pattern: name the role, "
                f"`sq role activate <slug> --from {template_name}`"
            )
        self._refuse_catalog_slug(chosen)
        self.check_role_slug(chosen)
        legacy = None
        if slug is None and template.slug is not None:
            legacy = proposed_slug(template, label or None, slugifier=legacy_slugify)
        await self._refuse_duplicate_role(chosen, legacy)
        roles = await self.list_items(item_type=ROSTER_ROLE)
        position = sum(1 for it in roles if attrs.template(it) == template_name)
        full_name = name
        if full_name is None:
            full_name = override_full_name(chosen, self.paths.squad_dir)
        if full_name is None:
            full_name = proposed_name(template, label or None, position)
        if full_name is None:
            raise SquadsError(
                f"role template {template_name!r} declares no name pattern: pass --name"
            )
        return await self._create_role(
            chosen,
            full_name,
            attributes={
                AttributeKey.TEMPLATE: template_name,
                **({AttributeKey.TECH: label} if parameter else {}),
                **self._model_attribute(model),
                **self._pronouns_attribute(pronouns),
            },
        )

    def _refuse_catalog_slug(self, slug: str) -> None:
        if slug in {r.slug for r in self.catalog().roles}:
            raise SquadsError(
                f"slug {slug!r} belongs to a role the catalog declares; "
                f"`sq role activate {slug}` activates it, or pick another slug"
            )

    async def add_role(  # noqa: PLR0913 — a flag per definition field
        self,
        slug: str,
        *,
        name: str | None = None,
        job_title: str | None = None,
        description: str | None = None,
        mission: str | None = None,
        capabilities: list[str] | None = None,
        model: str | None = None,
        pronouns: str | None = None,
        definition: RawMapping | None = None,
        source: str = "the role definition",
    ) -> Item:
        """Create a role that defines itself: its definition fields are stored on the item.

        *definition* is a per-slug file's grammar (``full_name`` is the name, ``title`` the job
        title), read from *source*; the keyword arguments win over its keys. Every missing
        required field is named in one refusal, with nothing written.
        """
        own_pronouns = checked_pronouns(pronouns)
        self._refuse_invalid_model(model)
        self.check_role_slug(slug)
        self._refuse_catalog_slug(slug)
        await self._refuse_duplicate_role(slug, None)
        self._refuse_bad_flags(
            {"--name": name, "--job-title": job_title, "--desc": description, "--mission": mission},
            capabilities,
        )
        data = self._definition_data(
            slug,
            definition or {},
            {
                "full_name": name,
                "title": job_title,
                "description": description,
                "mission": mission,
                "capabilities": capabilities,
                "model": model,
            },
        )
        role = role_from_definition(data, slug, source)
        attributes: dict[str, Any] = {
            AttributeKey.JOB_TITLE: role.title,
            AttributeKey.MISSION: role.mission,
            **self._definition_attributes(role),
            **self._pronouns_attribute(own_pronouns),
        }
        return await self._create_role(
            slug,
            role.full_name,
            attributes=attributes,
            description=role.description,
        )

    @staticmethod
    def _definition_data(
        slug: str, definition: RawMapping, flags: dict[str, Any]
    ) -> dict[str, Any]:
        """The per-slug-file grammar for a new role: *definition* with the *flags* given laid
        over it, refusing a key a role definition may not carry and naming every required key
        still missing."""
        if "is_default" in definition:
            raise SquadsError(
                "is_default is not a role definition key: designate the default with "
                f"`sq role {slug} set-default`"
            )
        data: dict[str, Any] = {**definition, **{k: v for k, v in flags.items() if v is not None}}
        flag_for = {
            "full_name": "--name",
            "title": "--job-title",
            "description": "--desc",
            "mission": "--mission",
        }
        missing = [f"{flag_for[k]} ({k})" for k in flag_for if k not in data]
        if missing:
            raise SquadsError(
                f"role {slug!r} is missing required fields: {', '.join(missing)}; "
                "pass the flags, or a --file that sets them"
            )
        return data

    @staticmethod
    def _definition_attributes(role: RoleDef) -> dict[str, Any]:
        """The optional definition attributes an item-defined role stores for *role*: only the
        ones that hold a value."""
        optional: dict[str, Any] = {
            AttributeKey.RESPONSIBILITIES: list(role.responsibilities),
            AttributeKey.AGREEMENTS: list(role.agreements),
            AttributeKey.COLOR: role.color,
            AttributeKey.CAN_SPAWN: True if role.can_spawn else None,
            AttributeKey.CAPABILITIES: list(role.capabilities),
            AttributeKey.MODEL: role.model,
        }
        return {k: v for k, v in optional.items() if v}

    async def _create_role(
        self,
        slug: str,
        name: str,
        *,
        attributes: dict[str, Any],
        description: str = "",
    ) -> Item:
        """Create the role item and materialise its entry in every backend when it is live:
        the one creation path every role verb ends in."""
        refuse_blank_name(name)
        res = await self.create(
            ROSTER_ROLE,
            name,
            description=description,
            slug=slug,
            author=slug,  # a role authors itself
            attributes=attributes,
        )
        if res.item.status in self.spec.live_statuses(ROSTER_ROLE):
            role = resolve_role_for_item(res.item, self.paths.squad_dir, catalog=self.catalog)
            ctx = self._ctx
            for backend in self._backends():
                await backend.generate_role_entry(ctx, res.item, role)
        return res.item

    @staticmethod
    def _model_attribute(model: str | None) -> dict[str, str]:
        return {} if model is None else {AttributeKey.MODEL: model}

    @staticmethod
    def _refuse_invalid_model(model: str | None) -> None:
        problem = model_problem(model)
        if problem is not None:
            raise SquadsError(problem)

    async def update_role(  # noqa: PLR0913 — a flag per role field
        self,
        item_id: str,
        *,
        title: str | None = None,
        pronouns: str | None = None,
        model: str | None = None,
        job_title: str | None = None,
        description: str | None = None,
        mission: str | None = None,
        capabilities: list[str] | None = None,
        color: str | None = None,
        can_spawn: bool | None = None,
        definition: RawMapping | None = None,
        source: str = "the role definition",
    ) -> RoleUpdateResult:
        """Edit a role. Name, pronouns and model are editable on every role (a blank *model* clears
        it); the definition fields (job title, description, mission, capabilities, colour, spawn
        authority, *definition*) only on a self-defining role, being refused on a catalog or
        template role with the file that holds them. A role whose catalog entry vanished becomes
        self-defining given a job title, description and mission. Every check runs before the first
        write.
        """
        item = await self.get(item_id)
        if item.type != ROSTER_ROLE:
            raise SquadsError(f"{item.id} is not a role")
        if title is not None and not title.strip():
            raise SquadsError("a role's name cannot be blank")
        own_pronouns = checked_pronouns(pronouns) if pronouns is not None else None
        if model:
            self._refuse_invalid_model(model)
        flags = {
            "--job-title": job_title,
            "--desc": description,
            "--mission": mission,
            "--capabilities": capabilities,
            "--color": color,
            "--can-spawn": can_spawn,
            "--file": definition,
        }
        given = [flag for flag, value in flags.items() if value is not None]
        written: dict[str, Any] = {}
        if given:
            written = self._definition_update(
                item,
                given,
                job_title=job_title,
                description=description,
                mission=mission,
                capabilities=capabilities,
                color=color,
                can_spawn=can_spawn,
                definition=definition,
                source=source,
            )
        stored: dict[str, Any] = {}
        if pronouns is not None:
            stored[AttributeKey.PRONOUNS] = own_pronouns
        if model is not None:
            stored[AttributeKey.MODEL] = model or None
        item, changed = await self._write_role_fields(
            item_id, title=title, definition=written, stored=stored
        )
        if item.status in self.spec.live_statuses(ROSTER_ROLE):
            role = resolve_role_for_item(item, self.paths.squad_dir, catalog=self.catalog)
            for backend in self._backends():
                await backend.generate_role_entry(self._ctx, item, role)
        return RoleUpdateResult(item=item, warnings=self._shadowing_warnings(item.slug, changed))

    def _definition_update(  # noqa: PLR0913 — the definition fields of one update
        self,
        item: Item,
        given: list[str],
        *,
        job_title: str | None,
        description: str | None,
        mission: str | None,
        capabilities: list[str] | None,
        color: str | None,
        can_spawn: bool | None,
        definition: RawMapping | None,
        source: str,
    ) -> dict[str, Any]:
        """The definition attributes (and the core ``description``) to write for *item*, keyed
        by name, a ``None`` value removing the key. Refuses the update on a role whose
        definition lives elsewhere."""
        slug = item.slug
        template = attrs.template(item)
        if template is not None:
            raise SquadsError(
                f"{slug}'s definition ({', '.join(given)}) comes from the role template "
                f"{template!r}; set it in .overrides/roles/{slug}.toml "
                f"(sq override scaffold --role {slug}), or in [templates.{template}] of "
                f"{ROLES_OVERRIDE_FILENAME} for every role built from the template"
            )
        defines_itself = attrs.mission(item) is not None
        if not defines_itself and role_base_from_item(item, self.catalog) is not None:
            raise SquadsError(
                f"{slug}'s definition ({', '.join(given)}) comes from the role catalog; set it "
                f"in .overrides/roles/{slug}.toml (sq override scaffold --role {slug})"
            )
        refused = sorted({"slug", "full_name", "is_default"} & set(definition or {}))
        if refused:
            raise SquadsError(
                f"--file may not set {', '.join(refused)}: rename the role with "
                f"`sq role {slug} update --title`, designate the default with "
                f"`sq role {slug} set-default`"
            )
        flag_values = {
            "title": job_title,
            "description": description,
            "mission": mission,
        }
        self._refuse_bad_flags(
            {
                "--job-title": job_title,
                "--desc": description,
                "--mission": mission,
            },
            capabilities,
        )
        if not defines_itself:
            return self._self_definition(
                item, flag_values, capabilities, color, can_spawn, definition, source
            )
        current = RoleDef.from_item(item)
        role = merge_definition_delta(current, definition, slug, source) if definition else current
        changes: dict[str, Any] = {k: v for k, v in flag_values.items() if v is not None}
        if capabilities is not None:
            self._refuse_bad_capabilities(capabilities)
            changes["capabilities"] = tuple(dict.fromkeys(capabilities))
        if color is not None:
            changes["color"] = color.strip() or None
        if can_spawn is not None:
            changes["can_spawn"] = can_spawn
        return self._definition_fields(replace(role, **changes))

    def _self_definition(
        self,
        item: Item,
        flag_values: dict[str, str | None],
        capabilities: list[str] | None,
        color: str | None,
        can_spawn: bool | None,
        definition: RawMapping | None,
        source: str,
    ) -> dict[str, Any]:
        """The fields that make *item*, whose catalog entry is gone, define itself."""
        data = self._definition_data(
            item.slug,
            definition or {},
            {
                "full_name": item.title,
                **flag_values,
                "capabilities": capabilities,
                "color": color,
                "can_spawn": can_spawn,
            },
        )
        fields = self._definition_fields(role_from_definition(data, item.slug, source))
        return {**fields, AttributeKey.ORIGIN: ORIGIN_PROJECT}

    @classmethod
    def _refuse_bad_flags(
        cls, texts: dict[str, str | None], capabilities: list[str] | None
    ) -> None:
        """Refuse a blank text flag or a malformed capability, naming the flag."""
        blank = [flag for flag, value in texts.items() if value is not None and not value.strip()]
        if blank:
            raise SquadsError(f"{', '.join(blank)} cannot be blank")
        if capabilities is not None:
            cls._refuse_bad_capabilities(capabilities)

    @staticmethod
    def _refuse_bad_capabilities(names: list[str]) -> None:
        bad = malformed_capability_names(names)
        if bad:
            raise SquadsError(
                "--capabilities entries must match "
                + CAPABILITY_NAME_PATTERN
                + ": "
                + ", ".join(bad)
            )

    def _definition_fields(self, role: RoleDef) -> dict[str, Any]:
        """Every definition key a self-defining role stores for *role*, ``None`` removing a key the
        role no longer holds.
        """
        optional = self._definition_attributes(role)
        keys = (
            AttributeKey.RESPONSIBILITIES,
            AttributeKey.AGREEMENTS,
            AttributeKey.COLOR,
            AttributeKey.CAN_SPAWN,
            AttributeKey.CAPABILITIES,
            AttributeKey.MODEL,
        )
        return {
            "description": role.description,
            AttributeKey.JOB_TITLE: role.title,
            AttributeKey.MISSION: role.mission,
            **{key: optional.get(key) for key in keys},
        }

    async def _write_role_fields(
        self,
        item_id: str,
        *,
        title: str | None,
        definition: dict[str, Any],
        stored: dict[str, Any],
    ) -> tuple[Item, set[str]]:
        """Write a role's new name, definition keys and stored per-role keys (a ``None`` value
        removing the key) in one transaction. Nothing is written when nothing differs. Returns
        the role and the keys that changed."""
        default_kind = self.spec.default_ref_kind()
        async with self.store.transaction() as db:
            item = require_item(db, item_id)
            await self._refuse_any_duplicated_id()
            base = item.model_copy(deep=True)
            delta: dict[str, Any] = {}
            if title is not None and title != item.title:
                delta["title"] = [item.title, title]
                item.title = title
            for key, value in {**definition, **stored}.items():
                before = item.description if key == "description" else item.attributes.get(key)
                if before == value:
                    continue
                delta[key] = [before, value]
                if key == "description":
                    item.description = value
                elif value is None:
                    item.attributes.pop(key, None)
                else:
                    item.attributes[key] = value
            if delta:
                item.updated_at = clock.now()
                item.modified_session, _ = actor.current_session()
                await update_frontmatter(
                    item_file(self.paths, item), item, base, default_kind=default_kind
                )
                self.store.log("update", item.id, delta)
        return item, set(delta)

    def _shadowing_warnings(self, slug: str, changed: set[str]) -> list[str]:
        """A notice for the *changed* fields that the role's per-slug file also sets: the file
        wins over the stored definition."""
        file_key = {
            "description": "description",
            AttributeKey.JOB_TITLE: "title",
            AttributeKey.MISSION: "mission",
            AttributeKey.RESPONSIBILITIES: "responsibilities",
            AttributeKey.AGREEMENTS: "agreements",
            AttributeKey.COLOR: "color",
            AttributeKey.CAN_SPAWN: "can_spawn",
            AttributeKey.CAPABILITIES: "capabilities",
        }
        in_file = override_file_keys(slug, self.paths.squad_dir)
        shadowed = sorted(file_key[k] for k in changed if k in file_key and file_key[k] in in_file)
        if not shadowed:
            return []
        return [
            f".overrides/roles/{slug}.toml also sets {', '.join(shadowed)}: the file wins over "
            "the role's stored definition, so the change has no effect until the file drops "
            "the key"
        ]

    async def _refuse_duplicate_role(self, slug: str, legacy_slug: str | None) -> None:
        """Refuse a role creation when *slug*, or the slug the earlier rule would have produced,
        is already stored; a retired role's refusal names the verb that revives it."""
        for candidate in dict.fromkeys(s for s in (slug, legacy_slug) if s):
            existing = await self.roster_item(ROSTER_ROLE, candidate)
            if existing is None:
                continue
            if existing.status in self.spec.live_statuses(ROSTER_ROLE):
                raise SquadsError(f"a role with slug {candidate!r} already exists")
            raise SquadsError(
                f"role {candidate!r} already exists and is {existing.status} ({existing.id}); "
                "creating a role does not revive one — "
                f"run `sq role {candidate} status {self.spec.live_initial(ROSTER_ROLE)}`"
            )

    async def add_skill(
        self,
        name: str,
        *,
        description: str = "",
        when_to_use: str = "",
        allowed_tools: str = "",
        parent: str | None = None,
        operator_invocable: str | None = None,
    ) -> Item:
        chosen = None if operator_invocable is None else parse_invocable_choice(operator_invocable)
        slug = slugify(name)
        await self._refuse_duplicate_slug(ROSTER_SKILL, "a skill", slug, legacy_slugify(name))
        res = await self.create(
            ROSTER_SKILL,
            name,
            description=description,
            parent=parent,
            slug=slug,
            author=slug,  # a skill authors itself
            attributes={
                AttributeKey.WHEN_TO_USE: when_to_use,
                AttributeKey.ALLOWED_TOOLS: allowed_tools,
                **({} if chosen is None else {AttributeKey.OPERATOR_INVOCABLE: chosen}),
            },
        )
        # Materialise iff live — see the matching comment in activate_role.
        if res.item.status in self.spec.live_statuses(ROSTER_SKILL):
            ctx = self._ctx
            for backend in self._backends():
                await backend.generate_skill_entry(ctx, res.item)
        return res.item

    async def _refuse_duplicate_slug(
        self, item_type: str, noun: str, slug: str, legacy_slug: str | None
    ) -> None:
        """Refuse when *slug*, or the slug the earlier rule would have produced, is already
        stored for *item_type*; the message names the stored slug."""
        for candidate in dict.fromkeys(s for s in (slug, legacy_slug) if s):
            if await self.roster_item(item_type, candidate) is not None:
                raise SquadsError(f"{noun} with slug {candidate!r} already exists")

    @staticmethod
    def _pronouns_attribute(own: str | None) -> dict[str, str]:
        """The attribute mapping that stores *own* pronouns, empty when there are none."""
        return {} if own is None else {AttributeKey.PRONOUNS: own}

    async def add_operator(
        self, name: str, *, slug: str | None = None, pronouns: str | None = None
    ) -> Item:
        """Register a human operator (assignable + can author items/comments), e.g. `op-alice`.

        ``pronouns`` is stored on the new item; blank stores nothing."""
        own_pronouns = checked_pronouns(pronouns)
        explicit = slug is not None
        slug = slug or operator_slug(name)
        await self._refuse_duplicate_slug(
            ROSTER_OPERATOR, "an operator", slug, None if explicit else legacy_operator_slug(name)
        )
        res = await self.create(
            ROSTER_OPERATOR,
            name,
            slug=slug,
            author=slug,  # an operator authors itself
            attributes=self._pronouns_attribute(own_pronouns),
        )
        await self.refresh_managed()  # so the CLAUDE.md operator roster picks it up
        return res.item

    async def list_operators(self) -> list[Item]:
        return await self.list_items(item_type=ROSTER_OPERATOR)

    async def list_roles(self) -> list[Item]:
        """The active roster — activated ``ROLE`` items — distinct from ``sq role catalog``
        (the bundled-but-not-necessarily-active catalog, which reads from ``PREDEFINED`` and
        has no notion of an index item at all)."""
        return await self.list_items(item_type=ROSTER_ROLE)

    async def default_role_slug(self) -> str | None:
        """The slug of the live role this squad designates as its default, or ``None`` when no live
        role carries the designation. It reads :meth:`~ServiceCore.roster`, the projection the
        generated default-role line is compiled from, so a display surface gets the same answer as
        the agent files.
        """
        return next((r.slug for r in await self.roster() if r.is_default), None)

    async def set_default_role(self, item_id: str) -> DefaultRoleMoveResult:
        """Move the ``is_default`` designation onto a live role: a move, not a set, since the
        projection takes the first holder, so every other holder is cleared in the same transaction.
        Holders are found by resolving (:func:`~squads._roles._resolver.role_base_from_item`), not
        the stored key, which only overrides the catalog; clearing writes an explicit ``False``. A
        non-live target is refused, the current holder is a reported no-op, and the projection is
        refreshed after commit when something changed.
        """
        async with self.store.transaction() as db:
            item = require_item(db, item_id)
            if item.type != ROSTER_ROLE:
                raise SquadsError(
                    f"{item.id} is not a role — the default designation applies to roles only"
                )
            live = self.spec.live_statuses(ROSTER_ROLE)
            if item.status not in live:
                slug = item.slug
                raise SquadsError(
                    f"{item.id} ({slug}) is not live — only a live role can be designated default"
                )

            await self._refuse_any_duplicated_id()
            # Resolved once for the whole pass (may clear several other roles below) rather
            # than once per role touched.
            default_kind = self.spec.default_ref_kind()
            cleared: list[str] = []
            for other in db.items.values():
                if (
                    other.type == ROSTER_ROLE
                    and other.id != item.id
                    and holds_default_designation(other, self.paths.squad_dir, catalog=self.catalog)
                ):
                    other_base = other.model_copy(deep=True)
                    other.attributes[AttributeKey.IS_DEFAULT] = False
                    other.updated_at = clock.now()
                    other.modified_session, _ = actor.current_session()
                    await update_frontmatter(
                        item_file(self.paths, other), other, other_base, default_kind=default_kind
                    )
                    cleared.append(other.id)

            was_default = holds_default_designation(
                item, self.paths.squad_dir, catalog=self.catalog
            )
            changed = bool(cleared) or not was_default
            if not was_default:
                base = item.model_copy(deep=True)
                item.attributes[AttributeKey.IS_DEFAULT] = True
                item.updated_at = clock.now()
                item.modified_session, _ = actor.current_session()
                await update_frontmatter(
                    item_file(self.paths, item), item, base, default_kind=default_kind
                )
            if changed:
                self.store.log("default_role", item.id, {"cleared": cleared})
        if changed:
            await self.refresh_managed()
        return DefaultRoleMoveResult(item=item, cleared=cleared, changed=changed)

    async def workload(self) -> list[WorkloadRow]:
        """Open/closed/total work-item counts per assignee (busiest first, unassigned last) plus
        separate sub-entity counts judged by the sub-entity's own status
        (:class:`~squads._services._results.WorkloadRow`); roster-category items are excluded. As a
        census it reads ``settled`` (``is_open``), unlike :meth:`mine`, which reads ``hidden``, so
        an ``in_force`` status counts closed here yet stays visible there, and ``sq mine`` and ``sq
        workload`` can disagree.
        """
        counts: dict[str | None, list[int]] = {}
        sub_counts: dict[str | None, list[int]] = {}
        for it in await self.list_items():
            if self.spec.item_is_roster(it.type):
                continue
            bucket = counts.setdefault(it.assignee, [0, 0])
            bucket[0 if self.spec.is_open(it.status) else 1] += 1
            if self.spec.item_subentity_kind(it.type) is None:
                continue
            for sub in it.subentities:
                sbucket = sub_counts.setdefault(sub.assignee, [0, 0])
                sbucket[0 if self.spec.is_open(sub.status) else 1] += 1
        rows = [
            WorkloadRow(
                assignee=a,
                open=o,
                closed=c,
                total=o + c,
                subentity_open=sub_counts.get(a, [0, 0])[0],
                subentity_closed=sub_counts.get(a, [0, 0])[1],
                subentity_total=sum(sub_counts.get(a, [0, 0])),
            )
            for a, (o, c) in counts.items()
        ]
        # An assignee owning only sub-entities (never an item) has no `counts` entry at all —
        # give them a zero-item row so their sub-entity counts are visible too.
        rows += [
            WorkloadRow(
                assignee=a,
                open=0,
                closed=0,
                total=0,
                subentity_open=o,
                subentity_closed=c,
                subentity_total=o + c,
            )
            for a, (o, c) in sub_counts.items()
            if a not in counts
        ]
        return sorted(rows, key=lambda r: (-r.open, -r.total, r.assignee or "~"))

    async def mine(self, slug: str, *, include_closed: bool = False) -> list[MineRow]:
        """Items assigned to ``slug`` directly or via a sub-entity. Unless ``include_closed``,
        visibility is judged per matched reason (the item's or sub-entity's own status, via
        ``spec.hidden_by_default``) and the row shows if any is open; roster-category items are
        excluded, as in :meth:`workload`. It reads ``hidden_by_default``, not ``is_open``, because
        it asks what belongs in a default listing, so keep it in step with ``sq list``.
        """
        rows: list[MineRow] = []
        for it in await self.list_items():
            if self.spec.item_is_roster(it.type):
                continue
            kind = self.spec.item_subentity_kind(it.type)
            matched_subs = [s for s in it.subentities if s.assignee == slug] if kind else []
            item_match = it.assignee == slug
            if not item_match and not matched_subs:
                continue
            if not include_closed:
                item_open = item_match and not self.spec.hidden_by_default(it.type, it.status)
                sub_open = kind is not None and any(
                    not self.spec.hidden_by_default(kind, s.status) for s in matched_subs
                )
                if not (item_open or sub_open):
                    continue
            rows.append(MineRow(item=it, matched_subentities=matched_subs))
        return rows
