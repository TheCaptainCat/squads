"""The binding table: the ``Service`` method that handles each operation.

Each resource group has its own section, matching the operation table's.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from pydantic import BaseModel

from squads._api import _ops as ops
from squads._api._api import Operation
from squads._api._response import Response
from squads._services._creation_ops import adopt_squad, init_squad
from squads._services._service import Service
from squads._spec_documents import SpecSources

type Handler[Req, Res] = Callable[[Service, Req], Awaitable[Response[Res]]]
type LocalHandler[Req, Res] = Callable[
    [Callable[[Path], SpecSources], Req], Awaitable[Response[Res]]
]


@dataclass(frozen=True)
class Binding[Req: BaseModel, Res]:
    """An operation and the method that handles it."""

    op: Operation[Req, Res]
    handler: Handler[Req, Res]


@dataclass(frozen=True)
class LocalBinding[Req: BaseModel, Res]:
    """A local-only operation and the function that handles it."""

    op: Operation[Req, Res]
    handler: LocalHandler[Req, Res]


def bind_local[Req: BaseModel, Res](
    op: Operation[Req, Res], handler: LocalHandler[Req, Res]
) -> LocalBinding[Req, Res]:
    """Pair the local-only *op* with *handler*, whose request and response types must be the
    operation's."""
    return LocalBinding(op, handler)


def bind[Req: BaseModel, Res](
    op: Operation[Req, Res], handler: Handler[Req, Res]
) -> Binding[Req, Res]:
    """Pair *op* with *handler*, whose request and response types must be the operation's."""
    return Binding(op, handler)


#: Left unannotated, so pyright checks each pair against its own operation rather than ``Any``.
BINDINGS = (
    # --- items
    bind(ops.ITEMS_LIST, Service.list_item_rows),
    # --- item reads
    bind(ops.ITEM_SHOW, Service.show_item),
    bind(ops.TREE, Service.tree_items),
    bind(ops.GRAPH, Service.graph_items),
    bind(ops.SEARCH, Service.search_items),
    bind(ops.INBOX, Service.inbox_items),
    bind(ops.MINE, Service.mine_items),
    bind(ops.BLOCKED, Service.blocked_items),
    bind(ops.WORKLOAD, Service.workload_items),
    bind(ops.ITEM_REFS, Service.item_refs),
    bind(ops.ITEM_COMMENTS, Service.item_comments),
    bind(ops.ITEM_SUBENTITIES, Service.list_subentities),
    bind(ops.ITEM_SUBENTITY, Service.show_subentity),
    # --- item writes
    bind(ops.ITEM_STATUS, Service.move_item_status),
    bind(ops.ITEMS_CREATE, Service.create_item),
    bind(ops.ITEM_UPDATE, Service.update_item),
    bind(ops.ITEM_BODY, Service.set_item_body),
    bind(ops.ITEM_RETYPE, Service.retype_item),
    bind(ops.ITEM_REMOVE, Service.remove_work_item_entry),
    bind(ops.ITEM_REF_ADD, Service.add_item_ref),
    bind(ops.ITEM_REF_RM, Service.remove_item_ref),
    bind(ops.ITEM_VIEW_ADD, Service.add_item_view),
    bind(ops.ITEM_VIEW_DISABLE, Service.disable_item_view),
    bind(ops.ITEM_COMMENT_ADD, Service.add_item_comment),
    bind(ops.ITEM_COMMENT_SHOW, Service.show_item_comment),
    bind(ops.ITEM_COMMENT_EDIT, Service.edit_item_comment),
    bind(ops.ITEM_COMMENT_REMOVAL, Service.item_comment_removal),
    bind(ops.ITEM_COMMENT_REMOVE, Service.remove_item_comment),
    bind(ops.SUBENTITY_ADD, Service.add_subentity),
    bind(ops.SUBENTITY_UPDATE, Service.update_subentity),
    bind(ops.SUBENTITY_BODY, Service.set_subentity_body),
    bind(ops.SUBENTITY_REMOVE, Service.remove_subentity),
    bind(ops.SUBENTITY_COMMENT_ADD, Service.add_subentity_comment),
    bind(ops.SUBENTITY_COMMENT_SHOW, Service.show_subentity_comment),
    bind(ops.SUBENTITY_COMMENT_EDIT, Service.edit_subentity_comment),
    bind(ops.SUBENTITY_COMMENT_REMOVAL, Service.subentity_comment_removal),
    bind(ops.SUBENTITY_COMMENT_REMOVE, Service.remove_subentity_comment),
    # --- roster
    bind(ops.ROLES_CATALOG, Service.role_catalog_listing),
    bind(ops.ROLES_LIST, Service.role_listing),
    bind(ops.ROLES_ACTIVATE, Service.activate_role_entry),
    bind(ops.ROLES_ADD, Service.add_role_entry),
    bind(ops.ROLE_SHOW, Service.show_role_entry),
    bind(ops.ROLE_UPDATE, Service.update_role_entry),
    bind(ops.ROLE_BODY, Service.set_role_body),
    bind(ops.ROLE_STATUS, Service.move_role_status),
    bind(ops.ROLE_SET_DEFAULT, Service.set_default_role_entry),
    bind(ops.ROLE_REGEN, Service.regen_role_entry),
    bind(ops.ROLE_REMOVE, Service.remove_role_entry),
    bind(ops.ROLE_VIEW_ADD, Service.add_role_view),
    bind(ops.ROLE_VIEW_DISABLE, Service.disable_role_view),
    bind(ops.DEVELOPERS_LIST, Service.developer_listing),
    bind(ops.SKILLS_ADD, Service.add_skill_entry),
    bind(ops.SKILL_SHOW, Service.show_skill_entry),
    bind(ops.SKILL_UPDATE, Service.update_skill_entry),
    bind(ops.SKILL_BODY, Service.set_skill_body),
    bind(ops.SKILL_STATUS, Service.move_skill_status),
    bind(ops.SKILL_REGEN, Service.regen_skill_entry),
    bind(ops.SKILL_REMOVE, Service.remove_skill_entry),
    bind(ops.SKILL_REFS, Service.skill_refs),
    bind(ops.SKILL_REF_ADD, Service.add_skill_ref),
    bind(ops.SKILL_REF_RM, Service.remove_skill_ref),
    bind(ops.SKILL_LINK_ROLE, Service.link_skill_role),
    bind(ops.SKILL_UNLINK_ROLE, Service.unlink_skill_role),
    bind(ops.SKILL_VIEW_ADD, Service.add_skill_view),
    bind(ops.SKILL_VIEW_DISABLE, Service.disable_skill_view),
    bind(ops.OPERATORS_LIST, Service.operator_listing),
    bind(ops.OPERATORS_ADD, Service.add_operator_entry),
    bind(ops.OPERATOR_SHOW, Service.show_operator_entry),
    bind(ops.OPERATOR_UPDATE, Service.update_operator_entry),
    bind(ops.OPERATOR_BODY, Service.set_operator_body),
    bind(ops.OPERATOR_STATUS, Service.move_operator_status),
    bind(ops.OPERATOR_REMOVE, Service.remove_operator_entry),
    bind(ops.ROLE_COMMENTS, Service.role_comments),
    bind(ops.ROLE_COMMENT_ADD, Service.add_role_comment),
    bind(ops.ROLE_COMMENT_SHOW, Service.show_role_comment),
    bind(ops.ROLE_COMMENT_EDIT, Service.edit_role_comment),
    bind(ops.ROLE_COMMENT_REMOVAL, Service.role_comment_removal),
    bind(ops.ROLE_COMMENT_REMOVE, Service.remove_role_comment),
    bind(ops.SKILL_COMMENTS, Service.skill_comments),
    bind(ops.SKILL_COMMENT_ADD, Service.add_skill_comment),
    bind(ops.SKILL_COMMENT_SHOW, Service.show_skill_comment),
    bind(ops.SKILL_COMMENT_EDIT, Service.edit_skill_comment),
    bind(ops.SKILL_COMMENT_REMOVAL, Service.skill_comment_removal),
    bind(ops.SKILL_COMMENT_REMOVE, Service.remove_skill_comment),
    bind(ops.OPERATOR_COMMENTS, Service.operator_comments),
    bind(ops.OPERATOR_COMMENT_ADD, Service.add_operator_comment),
    bind(ops.OPERATOR_COMMENT_SHOW, Service.show_operator_comment),
    bind(ops.OPERATOR_COMMENT_EDIT, Service.edit_operator_comment),
    bind(ops.OPERATOR_COMMENT_REMOVAL, Service.operator_comment_removal),
    bind(ops.OPERATOR_COMMENT_REMOVE, Service.remove_operator_comment),
    # --- squad state
    bind(ops.BOARD_LIST, Service.list_board),
    bind(ops.BOARD_POST, Service.post_to_board),
    bind(ops.BOARD_CLEAR, Service.clear_from_board),
    bind(ops.MEMORY_LIST, Service.list_memories),
    bind(ops.MEMORY_SEARCH, Service.search_memories),
    bind(ops.MEMORY_SHOW, Service.show_memory),
    bind(ops.MEMORY_ADD, Service.add_memory),
    bind(ops.MEMORY_FORGET, Service.forget_memory),
    bind(ops.WORKFLOW_SHOW, Service.render_cheatsheet),
    bind(ops.WORKFLOW_TYPES, Service.list_types),
    bind(ops.WORKFLOW_SUBENTITY_KINDS, Service.list_subentity_kinds),
    bind(ops.WORKFLOW_LIFECYCLES, Service.list_lifecycles),
    bind(ops.WORKFLOW_COLLECTIONS, Service.list_collections),
    bind(ops.WORKFLOW_STATUSES, Service.list_statuses),
    bind(ops.WORKFLOW_ROLES, Service.list_status_roles),
    bind(ops.WORKFLOW_REF_KINDS, Service.list_ref_kinds),
    bind(ops.WORKFLOW_VIEWS, Service.list_views),
    bind(ops.WORKFLOW_VIEW, Service.resolve_view),
    bind(ops.WORKFLOW_LINT, Service.lint_workflow),
    bind(ops.OVERRIDES_LIST, Service.list_overrides),
    bind(ops.OVERRIDES_DIFF, Service.diff_overrides),
    bind(ops.OVERRIDES_SCAFFOLD, Service.scaffold_override),
    bind(ops.OVERRIDES_UPDATE, Service.stamp_overrides),
    bind(ops.REFLOG, Service.list_reflog),
    bind(ops.CHECK, Service.check_squad),
    bind(ops.SYNC, Service.sync_squad),
    # --- corpus-wide
    bind(ops.REPAIR, Service.repair_squad),
    bind(ops.RENUMBER, Service.renumber_squad),
    bind(ops.MIGRATE, Service.migrate_squad),
    bind(ops.REPAD, Service.repad_squad),
    bind(ops.RENAME_TYPE, Service.rename_type_items),
    bind(ops.RENAME_STATUS, Service.rename_status_items),
    bind(ops.IMPORT, Service.import_squad_events),
)

#: The operations that create the squad a service is composed on: each handler takes the
#: documents the invocation reads for a squad directory, not a service.
LOCAL_BINDINGS = (
    bind_local(ops.INIT, init_squad),
    bind_local(ops.ADOPT, adopt_squad),
)


def handler_for[Req: BaseModel, Res](op: Operation[Req, Res]) -> Handler[Req, Res]:
    """The method bound to *op*."""
    for binding in BINDINGS:
        if binding.op is op:
            return cast(Handler[Req, Res], binding.handler)
    raise LookupError(f"no handler is bound to the operation {op.name!r}")


def local_handler_for[Req: BaseModel, Res](op: Operation[Req, Res]) -> LocalHandler[Req, Res]:
    """The function bound to the local-only *op*."""
    for binding in LOCAL_BINDINGS:
        if binding.op is op:
            return cast(LocalHandler[Req, Res], binding.handler)
    raise LookupError(f"no handler is bound to the operation {op.name!r}")
