"""The operation table: one entry per operation, the single source of the routes, the request
and response types and how each runs.

Each resource group has its own section; a new operation is defined in its group's section and
listed in the same section of :data:`OPERATIONS`.
"""

from typing import Any

from squads._api._api import Grant, Ground, Mode, Operation, Timeout
from squads._api._dto._board import (
    BoardClearRequest,
    BoardListRequest,
    BoardPostRequest,
    NoticeList,
    NoticeWrite,
)
from squads._api._dto._check import CheckReport, CheckRequest, SyncReport, SyncRequest
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
from squads._api._dto._comments import Comments, CommentsRequest
from squads._api._dto._graph import GraphNode, GraphRequest
from squads._api._dto._item_writes import (
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
from squads._api._dto._items import (
    ItemList,
    ItemListRequest,
    ItemShow,
    ItemShowRequest,
    ItemStatusRequest,
)
from squads._api._dto._memory import (
    Memory,
    MemoryAdded,
    MemoryAddRequest,
    MemoryForgetRequest,
    MemoryForgotten,
    MemoryList,
    MemoryListRequest,
    MemorySearch,
    MemorySearchRequest,
    MemoryShowRequest,
)
from squads._api._dto._operators import (
    OperatorAddRequest,
    OperatorList,
    OperatorListRequest,
    OperatorShow,
    OperatorStatusMove,
    OperatorUpdateRequest,
    OperatorWrite,
)
from squads._api._dto._overrides import (
    OverrideDiff,
    OverrideDiffRequest,
    OverrideList,
    OverrideListRequest,
    OverrideScaffoldRequest,
    OverrideUpdateRequest,
    ScaffoldedOverride,
    StampedOverrides,
)
from squads._api._dto._queues import (
    Blocked,
    BlockedRequest,
    Inbox,
    InboxRequest,
    Mine,
    MineRequest,
    Workload,
    WorkloadRequest,
)
from squads._api._dto._reflog import Reflog, ReflogRequest
from squads._api._dto._refs import Refs, RefsRequest
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
    RoleShow,
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
    ViewRequest,
)
from squads._api._dto._search import SearchRequest, SearchResults
from squads._api._dto._skills import (
    SkillAddRequest,
    SkillRefChange,
    SkillRefRemoveRequest,
    SkillRefRequest,
    SkillRefs,
    SkillRefsRequest,
    SkillRoleLink,
    SkillRoleRequest,
    SkillShow,
    SkillStatusMove,
    SkillUpdateRequest,
    SkillViewChange,
    SkillWrite,
)
from squads._api._dto._squad import (
    AdoptReport,
    AdoptRequest,
    ImportReport,
    ImportRequest,
    InitReport,
    InitRequest,
    MigrateRequest,
    MigrationReport,
    RenameFieldReport,
    RenameFieldRequest,
    RenameKindReport,
    RenameKindRequest,
    RenameStatusReport,
    RenameStatusRequest,
    RenameTypeReport,
    RenameTypeRequest,
    RenumberReport,
    RenumberRequest,
    RepadReport,
    RepadRequest,
    RepairReport,
    RepairRequest,
)
from squads._api._dto._subentities import (
    SubentitiesRequest,
    SubentityList,
    SubentityRequest,
    SubentityShow,
)
from squads._api._dto._tree import TreeRequest, TreeView
from squads._api._dto._workflow import (
    CatalogRequest,
    Cheatsheet,
    CheatsheetRequest,
    CollectionCatalog,
    LifecycleCatalog,
    LintReport,
    LintRequest,
    RefKindCatalog,
    StatusCatalog,
    StatusRoleCatalog,
    SubentityKindCatalog,
    TypeCatalog,
    ViewCatalog,
    ViewResolveRequest,
    ViewResult,
)

# --- items --------------------------------------------------------------------------------------

ITEMS_LIST = Operation(
    "items.list", "GET", "/v1/items", ItemListRequest, ItemList, json_field="items"
)

# --- item reads ---------------------------------------------------------------------------------

ITEM_SHOW = Operation("items.show", "GET", "/v1/items/{id}", ItemShowRequest, ItemShow)
TREE = Operation("tree", "GET", "/v1/tree", TreeRequest, TreeView, json_field="items")
GRAPH = Operation("graph", "GET", "/v1/graph", GraphRequest, GraphNode)
SEARCH = Operation("search", "GET", "/v1/search", SearchRequest, SearchResults, json_field="items")
INBOX = Operation("inbox", "GET", "/v1/inbox/{slug}", InboxRequest, Inbox, json_field="items")
MINE = Operation("mine", "GET", "/v1/mine/{slug}", MineRequest, Mine, json_field="items")
BLOCKED = Operation("blocked", "GET", "/v1/blocked", BlockedRequest, Blocked, json_field="items")
WORKLOAD = Operation(
    "workload", "GET", "/v1/workload", WorkloadRequest, Workload, json_field="items"
)
ITEM_REFS = Operation("items.refs", "GET", "/v1/items/{id}/refs", RefsRequest, Refs)
ITEM_COMMENTS = Operation(
    "items.comments",
    "GET",
    "/v1/items/{id}/comments",
    CommentsRequest,
    Comments,
    json_field="items",
)
ITEM_SUBENTITIES = Operation(
    "items.subentities.list",
    "GET",
    "/v1/items/{id}/subentities",
    SubentitiesRequest,
    SubentityList,
    json_field="items",
)
ITEM_SUBENTITY = Operation(
    "items.subentities.show",
    "GET",
    "/v1/items/{id}/subentities/{local}",
    SubentityRequest,
    SubentityShow,
)

# --- item writes --------------------------------------------------------------------------------

ITEM_STATUS = Operation(
    "items.status", "POST", "/v1/items/{id}/status", ItemStatusRequest, ItemWritten
)
ITEMS_CREATE = Operation("items.create", "POST", "/v1/items", ItemCreateRequest, ItemCreated)
ITEM_UPDATE = Operation("items.update", "PATCH", "/v1/items/{id}", ItemUpdateRequest, ItemUpdated)
ITEM_BODY = Operation("items.body", "PUT", "/v1/items/{id}/body", ItemBodyRequest, ItemWritten)
ITEM_RETYPE = Operation(
    "items.retype", "POST", "/v1/items/{id}/retype", ItemRetypeRequest, ItemRetyped
)
ITEM_REMOVE = Operation("items.remove", "DELETE", "/v1/items/{id}", ItemRemoveRequest, ItemRemoved)
ITEM_REF_ADD = Operation(
    "items.ref_add", "POST", "/v1/items/{id}/refs", ItemRefRequest, ItemRefAdded
)
ITEM_REF_RM = Operation(
    "items.ref_rm", "DELETE", "/v1/items/{id}/refs/{target}", ItemRefRemoveRequest, ItemRefRemoved
)
ITEM_VIEW_ADD = Operation(
    "items.view_add", "POST", "/v1/items/{id}/views", ItemViewRequest, ItemViewChanged
)
ITEM_VIEW_DISABLE = Operation(
    "items.view_disable",
    "POST",
    "/v1/items/{id}/views/{name}/disable",
    ItemViewRequest,
    ItemViewChanged,
)
ITEM_COMMENT_ADD = Operation(
    "items.comments.add", "POST", "/v1/items/{id}/comments", CommentAddRequest, CommentAdded
)
ITEM_COMMENT_SHOW = Operation(
    "items.comments.show", "GET", "/v1/items/{id}/comments/{hash}", CommentRequest, CommentShown
)
ITEM_COMMENT_EDIT = Operation(
    "items.comments.edit",
    "PATCH",
    "/v1/items/{id}/comments/{hash}",
    CommentEditRequest,
    CommentEdited,
)
#: What a removal of the comment would delete, read before the user confirms it.
ITEM_COMMENT_REMOVAL = Operation(
    "items.comments.removal",
    "GET",
    "/v1/items/{id}/comments/{hash}/removal",
    CommentRequest,
    CommentSelection,
)
ITEM_COMMENT_REMOVE = Operation(
    "items.comments.remove",
    "DELETE",
    "/v1/items/{id}/comments/{hash}",
    CommentRequest,
    CommentSelection,
    json_field="items",
)
SUBENTITY_ADD = Operation(
    "items.subentities.add",
    "POST",
    "/v1/items/{id}/subentities",
    SubentityAddRequest,
    SubentityAdded,
)
SUBENTITY_UPDATE = Operation(
    "items.subentities.update",
    "PATCH",
    "/v1/items/{id}/subentities/{local}",
    SubentityUpdateRequest,
    SubentityUpdated,
)
SUBENTITY_BODY = Operation(
    "items.subentities.body",
    "PUT",
    "/v1/items/{id}/subentities/{local}/body",
    SubentityBodyRequest,
    SubentityWritten,
)
SUBENTITY_REMOVE = Operation(
    "items.subentities.remove",
    "DELETE",
    "/v1/items/{id}/subentities/{local}",
    SubentityRemoveRequest,
    SubentityRemoved,
)
SUBENTITY_COMMENT_ADD = Operation(
    "items.subentities.comments.add",
    "POST",
    "/v1/items/{id}/subentities/{local}/comments",
    SubentityCommentAddRequest,
    CommentAdded,
)
SUBENTITY_COMMENT_SHOW = Operation(
    "items.subentities.comments.show",
    "GET",
    "/v1/items/{id}/subentities/{local}/comments/{hash}",
    SubentityCommentRequest,
    CommentShown,
)
SUBENTITY_COMMENT_EDIT = Operation(
    "items.subentities.comments.edit",
    "PATCH",
    "/v1/items/{id}/subentities/{local}/comments/{hash}",
    SubentityCommentEditRequest,
    CommentEdited,
)
SUBENTITY_COMMENT_REMOVAL = Operation(
    "items.subentities.comments.removal",
    "GET",
    "/v1/items/{id}/subentities/{local}/comments/{hash}/removal",
    SubentityCommentRequest,
    CommentSelection,
)
SUBENTITY_COMMENT_REMOVE = Operation(
    "items.subentities.comments.remove",
    "DELETE",
    "/v1/items/{id}/subentities/{local}/comments/{hash}",
    SubentityCommentRequest,
    CommentSelection,
    json_field="items",
)

# --- roster -------------------------------------------------------------------------------------

#: A literal under ``/v1/roles/`` is a group verb of ``sq role``, which no role can be addressed by.
ROLES_CATALOG = Operation(
    "roles.catalog", "GET", "/v1/roles/catalog", RoleCatalogRequest, RoleCatalog, json_field="items"
)
ROLES_LIST = Operation(
    "roles.list", "GET", "/v1/roles", RoleListRequest, RoleList, json_field="items"
)
ROLES_ACTIVATE = Operation(
    "roles.activate", "POST", "/v1/roles/activate", RoleActivateRequest, RoleWrite
)
ROLES_ADD = Operation("roles.add", "POST", "/v1/roles", RoleAddRequest, RoleWrite)
ROLE_SHOW = Operation("roles.show", "GET", "/v1/roles/{addr}", RosterAddress, RoleShow)
ROLE_UPDATE = Operation("roles.update", "PATCH", "/v1/roles/{addr}", RoleUpdateRequest, RoleWrite)
ROLE_BODY = Operation("roles.body", "PUT", "/v1/roles/{addr}/body", RosterBodyRequest, RoleWrite)
ROLE_STATUS = Operation(
    "roles.status", "POST", "/v1/roles/{addr}/status", RosterStatusRequest, RoleStatusMove
)
ROLE_SET_DEFAULT = Operation(
    "roles.set_default", "POST", "/v1/roles/{addr}/set-default", RosterAddress, RoleDefaultMove
)
ROLE_REGEN = Operation("roles.regen", "POST", "/v1/roles/{addr}/regen", RosterAddress, RoleWrite)
ROLE_REMOVE = Operation(
    "roles.remove", "DELETE", "/v1/roles/{addr}", RosterRemoveRequest, RoleWrite
)
ROLE_VIEW_ADD = Operation(
    "roles.view_add", "POST", "/v1/roles/{addr}/views", ViewRequest, RoleViewChange
)
ROLE_VIEW_DISABLE = Operation(
    "roles.view_disable",
    "POST",
    "/v1/roles/{addr}/views/{name}/disable",
    ViewRequest,
    RoleViewChange,
)
#: Not under ``/v1/roles/``, where it would take an address a role can have.
DEVELOPERS_LIST = Operation(
    "developers.list", "GET", "/v1/developers", DeveloperListRequest, DeveloperList
)
SKILLS_ADD = Operation("skills.add", "POST", "/v1/skills", SkillAddRequest, SkillWrite)
SKILL_SHOW = Operation("skills.show", "GET", "/v1/skills/{addr}", RosterAddress, SkillShow)
SKILL_UPDATE = Operation(
    "skills.update", "PATCH", "/v1/skills/{addr}", SkillUpdateRequest, SkillWrite
)
SKILL_BODY = Operation(
    "skills.body", "PUT", "/v1/skills/{addr}/body", RosterBodyRequest, SkillWrite
)
SKILL_STATUS = Operation(
    "skills.status", "POST", "/v1/skills/{addr}/status", RosterStatusRequest, SkillStatusMove
)
SKILL_REGEN = Operation(
    "skills.regen", "POST", "/v1/skills/{addr}/regen", RosterAddress, SkillWrite
)
SKILL_REMOVE = Operation(
    "skills.remove", "DELETE", "/v1/skills/{addr}", RosterRemoveRequest, SkillWrite
)
SKILL_REFS = Operation("skills.refs", "GET", "/v1/skills/{addr}/refs", SkillRefsRequest, SkillRefs)
SKILL_REF_ADD = Operation(
    "skills.ref_add", "POST", "/v1/skills/{addr}/refs", SkillRefRequest, SkillRefChange
)
SKILL_REF_RM = Operation(
    "skills.ref_rm",
    "DELETE",
    "/v1/skills/{addr}/refs/{target}",
    SkillRefRemoveRequest,
    SkillRefChange,
)
SKILL_LINK_ROLE = Operation(
    "skills.link_role", "POST", "/v1/skills/{addr}/link-role", SkillRoleRequest, SkillRoleLink
)
SKILL_UNLINK_ROLE = Operation(
    "skills.unlink_role",
    "POST",
    "/v1/skills/{addr}/unlink-role",
    SkillRoleRequest,
    SkillRoleLink,
)
SKILL_VIEW_ADD = Operation(
    "skills.view_add", "POST", "/v1/skills/{addr}/views", ViewRequest, SkillViewChange
)
SKILL_VIEW_DISABLE = Operation(
    "skills.view_disable",
    "POST",
    "/v1/skills/{addr}/views/{name}/disable",
    ViewRequest,
    SkillViewChange,
)
OPERATORS_LIST = Operation(
    "operators.list",
    "GET",
    "/v1/operators",
    OperatorListRequest,
    OperatorList,
    json_field="items",
)
OPERATORS_ADD = Operation(
    "operators.add", "POST", "/v1/operators", OperatorAddRequest, OperatorWrite
)
OPERATOR_SHOW = Operation(
    "operators.show", "GET", "/v1/operators/{addr}", RosterAddress, OperatorShow
)
OPERATOR_UPDATE = Operation(
    "operators.update", "PATCH", "/v1/operators/{addr}", OperatorUpdateRequest, OperatorWrite
)
OPERATOR_BODY = Operation(
    "operators.body", "PUT", "/v1/operators/{addr}/body", RosterBodyRequest, OperatorWrite
)
OPERATOR_STATUS = Operation(
    "operators.status",
    "POST",
    "/v1/operators/{addr}/status",
    RosterStatusRequest,
    OperatorStatusMove,
)
OPERATOR_REMOVE = Operation(
    "operators.remove", "DELETE", "/v1/operators/{addr}", RosterRemoveRequest, OperatorWrite
)

ROLE_COMMENTS = Operation(
    "roles.comments",
    "GET",
    "/v1/roles/{addr}/comments",
    RosterAddress,
    Comments,
    json_field="items",
)
ROLE_COMMENT_ADD = Operation(
    "roles.comments.add", "POST", "/v1/roles/{addr}/comments", RosterCommentAddRequest, CommentAdded
)
ROLE_COMMENT_SHOW = Operation(
    "roles.comments.show",
    "GET",
    "/v1/roles/{addr}/comments/{hash}",
    RosterCommentRequest,
    CommentShown,
)
ROLE_COMMENT_EDIT = Operation(
    "roles.comments.edit",
    "PATCH",
    "/v1/roles/{addr}/comments/{hash}",
    RosterCommentEditRequest,
    CommentEdited,
)
ROLE_COMMENT_REMOVAL = Operation(
    "roles.comments.removal",
    "GET",
    "/v1/roles/{addr}/comments/{hash}/removal",
    RosterCommentRequest,
    CommentSelection,
)
ROLE_COMMENT_REMOVE = Operation(
    "roles.comments.remove",
    "DELETE",
    "/v1/roles/{addr}/comments/{hash}",
    RosterCommentRequest,
    CommentSelection,
    json_field="items",
)

SKILL_COMMENTS = Operation(
    "skills.comments",
    "GET",
    "/v1/skills/{addr}/comments",
    RosterAddress,
    Comments,
    json_field="items",
)
SKILL_COMMENT_ADD = Operation(
    "skills.comments.add",
    "POST",
    "/v1/skills/{addr}/comments",
    RosterCommentAddRequest,
    CommentAdded,
)
SKILL_COMMENT_SHOW = Operation(
    "skills.comments.show",
    "GET",
    "/v1/skills/{addr}/comments/{hash}",
    RosterCommentRequest,
    CommentShown,
)
SKILL_COMMENT_EDIT = Operation(
    "skills.comments.edit",
    "PATCH",
    "/v1/skills/{addr}/comments/{hash}",
    RosterCommentEditRequest,
    CommentEdited,
)
SKILL_COMMENT_REMOVAL = Operation(
    "skills.comments.removal",
    "GET",
    "/v1/skills/{addr}/comments/{hash}/removal",
    RosterCommentRequest,
    CommentSelection,
)
SKILL_COMMENT_REMOVE = Operation(
    "skills.comments.remove",
    "DELETE",
    "/v1/skills/{addr}/comments/{hash}",
    RosterCommentRequest,
    CommentSelection,
    json_field="items",
)

OPERATOR_COMMENTS = Operation(
    "operators.comments",
    "GET",
    "/v1/operators/{addr}/comments",
    RosterAddress,
    Comments,
    json_field="items",
)
OPERATOR_COMMENT_ADD = Operation(
    "operators.comments.add",
    "POST",
    "/v1/operators/{addr}/comments",
    RosterCommentAddRequest,
    CommentAdded,
)
OPERATOR_COMMENT_SHOW = Operation(
    "operators.comments.show",
    "GET",
    "/v1/operators/{addr}/comments/{hash}",
    RosterCommentRequest,
    CommentShown,
)
OPERATOR_COMMENT_EDIT = Operation(
    "operators.comments.edit",
    "PATCH",
    "/v1/operators/{addr}/comments/{hash}",
    RosterCommentEditRequest,
    CommentEdited,
)
OPERATOR_COMMENT_REMOVAL = Operation(
    "operators.comments.removal",
    "GET",
    "/v1/operators/{addr}/comments/{hash}/removal",
    RosterCommentRequest,
    CommentSelection,
)
OPERATOR_COMMENT_REMOVE = Operation(
    "operators.comments.remove",
    "DELETE",
    "/v1/operators/{addr}/comments/{hash}",
    RosterCommentRequest,
    CommentSelection,
    json_field="items",
)

# --- squad state --------------------------------------------------------------------------------

#: What an override command may do on a squad whose schema is behind the package's.
_OVERRIDE_GRANT = Grant(Ground.NO_SQUAD_STATE, behind=True, ahead=False)

BOARD_LIST = Operation(
    "board.list", "GET", "/v1/board", BoardListRequest, NoticeList, json_field="items"
)
BOARD_POST = Operation("board.post", "POST", "/v1/board", BoardPostRequest, NoticeWrite)
BOARD_CLEAR = Operation("board.clear", "DELETE", "/v1/board/{n}", BoardClearRequest, NoticeWrite)
MEMORY_LIST = Operation(
    "memory.list", "GET", "/v1/memory/{role}", MemoryListRequest, MemoryList, json_field="items"
)
MEMORY_SEARCH = Operation(
    "memory.search",
    "GET",
    "/v1/memory/{role}/search",
    MemorySearchRequest,
    MemorySearch,
    json_field="items",
)
MEMORY_SHOW = Operation("memory.show", "GET", "/v1/memory/{role}/{slug}", MemoryShowRequest, Memory)
MEMORY_ADD = Operation("memory.add", "POST", "/v1/memory/{role}", MemoryAddRequest, MemoryAdded)
MEMORY_FORGET = Operation(
    "memory.forget", "DELETE", "/v1/memory/{role}/{slug}", MemoryForgetRequest, MemoryForgotten
)
WORKFLOW_SHOW = Operation(
    "workflow.show",
    "GET",
    "/v1/workflow/cheatsheet",
    CheatsheetRequest,
    Cheatsheet,
    mode=Mode.VOCABULARY,
)
WORKFLOW_TYPES = Operation(
    "workflow.types",
    "GET",
    "/v1/workflow/types",
    CatalogRequest,
    TypeCatalog,
    mode=Mode.VOCABULARY,
    json_field="items",
)
WORKFLOW_SUBENTITY_KINDS = Operation(
    "workflow.subentity-kinds",
    "GET",
    "/v1/workflow/subentity-kinds",
    CatalogRequest,
    SubentityKindCatalog,
    mode=Mode.VOCABULARY,
    json_field="items",
)
WORKFLOW_LIFECYCLES = Operation(
    "workflow.lifecycles",
    "GET",
    "/v1/workflow/lifecycles",
    CatalogRequest,
    LifecycleCatalog,
    mode=Mode.VOCABULARY,
    json_field="items",
)
WORKFLOW_COLLECTIONS = Operation(
    "workflow.collections",
    "GET",
    "/v1/workflow/collections",
    CatalogRequest,
    CollectionCatalog,
    mode=Mode.VOCABULARY,
    json_field="items",
)
WORKFLOW_STATUSES = Operation(
    "workflow.statuses",
    "GET",
    "/v1/workflow/statuses",
    CatalogRequest,
    StatusCatalog,
    mode=Mode.VOCABULARY,
    json_field="items",
)
WORKFLOW_ROLES = Operation(
    "workflow.roles",
    "GET",
    "/v1/workflow/roles",
    CatalogRequest,
    StatusRoleCatalog,
    mode=Mode.VOCABULARY,
    json_field="items",
)
WORKFLOW_REF_KINDS = Operation(
    "workflow.ref-kinds",
    "GET",
    "/v1/workflow/ref-kinds",
    CatalogRequest,
    RefKindCatalog,
    mode=Mode.VOCABULARY,
    json_field="items",
)
WORKFLOW_VIEWS = Operation(
    "workflow.views",
    "GET",
    "/v1/workflow/views",
    CatalogRequest,
    ViewCatalog,
    mode=Mode.VOCABULARY,
    json_field="items",
)
WORKFLOW_VIEW = Operation(
    "workflow.view",
    "GET",
    "/v1/workflow/views/{name}/{item}",
    ViewResolveRequest,
    ViewResult,
    json_field="source",
)
WORKFLOW_LINT = Operation(
    "workflow.lint",
    "GET",
    "/v1/workflow/lint",
    LintRequest,
    LintReport,
    mode=Mode.BUNDLED_FALLBACK,
)
OVERRIDES_LIST = Operation(
    "overrides.list",
    "GET",
    "/v1/overrides",
    OverrideListRequest,
    OverrideList,
    mode=Mode.BUNDLED_FALLBACK,
    grant=_OVERRIDE_GRANT,
    json_field="items",
)
OVERRIDES_DIFF = Operation(
    "overrides.diff",
    "GET",
    "/v1/overrides/diff",
    OverrideDiffRequest,
    OverrideDiff,
    mode=Mode.BUNDLED_FALLBACK,
    grant=_OVERRIDE_GRANT,
    json_field="items",
)
OVERRIDES_SCAFFOLD = Operation(
    "overrides.scaffold", "POST", "/v1/overrides", OverrideScaffoldRequest, ScaffoldedOverride
)
OVERRIDES_UPDATE = Operation(
    "overrides.update",
    "POST",
    "/v1/overrides/stamp",
    OverrideUpdateRequest,
    StampedOverrides,
    mode=Mode.BUNDLED_FALLBACK,
    grant=_OVERRIDE_GRANT,
)
REFLOG = Operation("reflog", "GET", "/v1/reflog", ReflogRequest, Reflog, json_field="items")
CHECK = Operation(
    "check", "GET", "/v1/check", CheckRequest, CheckReport, mode=Mode.CHECK, json_field="items"
)
SYNC = Operation("sync", "POST", "/v1/squad/sync", SyncRequest, SyncReport)

# --- corpus-wide --------------------------------------------------------------------------------

#: What the migration may do on a squad whose schema is behind the package's.
_MIGRATION_GRANT = Grant(Ground.MIGRATION, behind=True, ahead=False)

REPAIR = Operation(
    "squad.repair",
    "POST",
    "/v1/squad/repair",
    RepairRequest,
    RepairReport,
    mode=Mode.INDEX_CHECK_SKIPPED,
    timeout=Timeout.LONG,
)
RENUMBER = Operation(
    "squad.renumber",
    "POST",
    "/v1/squad/renumber",
    RenumberRequest,
    RenumberReport,
    timeout=Timeout.LONG,
)
MIGRATE = Operation(
    "squad.migrate",
    "POST",
    "/v1/squad/migrate",
    MigrateRequest,
    MigrationReport,
    mode=Mode.MIGRATE,
    grant=_MIGRATION_GRANT,
    timeout=Timeout.LONG,
)
REPAD = Operation(
    "squad.repad", "POST", "/v1/squad/repad", RepadRequest, RepadReport, timeout=Timeout.LONG
)
RENAME_TYPE = Operation(
    "squad.rename-type",
    "POST",
    "/v1/squad/rename-type",
    RenameTypeRequest,
    RenameTypeReport,
    timeout=Timeout.LONG,
)
RENAME_STATUS = Operation(
    "squad.rename-status",
    "POST",
    "/v1/squad/rename-status",
    RenameStatusRequest,
    RenameStatusReport,
    timeout=Timeout.LONG,
)
RENAME_FIELD = Operation(
    "squad.rename-field",
    "POST",
    "/v1/squad/rename-field",
    RenameFieldRequest,
    RenameFieldReport,
    timeout=Timeout.LONG,
)
RENAME_KIND = Operation(
    "squad.rename-kind",
    "POST",
    "/v1/squad/rename-kind",
    RenameKindRequest,
    RenameKindReport,
    timeout=Timeout.LONG,
)
IMPORT = Operation(
    "squad.import", "POST", "/v1/squad/import", ImportRequest, ImportReport, timeout=Timeout.LONG
)
INIT = Operation("squad.init", "POST", "/v1/squad/init", InitRequest, InitReport, local_only=True)
ADOPT = Operation(
    "squad.adopt", "POST", "/v1/squad/adopt", AdoptRequest, AdoptReport, local_only=True
)


OPERATIONS: tuple[Operation[Any, Any], ...] = (
    # --- items
    ITEMS_LIST,
    # --- item reads
    ITEM_SHOW,
    TREE,
    GRAPH,
    SEARCH,
    INBOX,
    MINE,
    BLOCKED,
    WORKLOAD,
    ITEM_REFS,
    ITEM_COMMENTS,
    ITEM_SUBENTITIES,
    ITEM_SUBENTITY,
    # --- item writes
    ITEM_STATUS,
    ITEMS_CREATE,
    ITEM_UPDATE,
    ITEM_BODY,
    ITEM_RETYPE,
    ITEM_REMOVE,
    ITEM_REF_ADD,
    ITEM_REF_RM,
    ITEM_VIEW_ADD,
    ITEM_VIEW_DISABLE,
    ITEM_COMMENT_ADD,
    ITEM_COMMENT_SHOW,
    ITEM_COMMENT_EDIT,
    ITEM_COMMENT_REMOVAL,
    ITEM_COMMENT_REMOVE,
    SUBENTITY_ADD,
    SUBENTITY_UPDATE,
    SUBENTITY_BODY,
    SUBENTITY_REMOVE,
    SUBENTITY_COMMENT_ADD,
    SUBENTITY_COMMENT_SHOW,
    SUBENTITY_COMMENT_EDIT,
    SUBENTITY_COMMENT_REMOVAL,
    SUBENTITY_COMMENT_REMOVE,
    # --- roster
    ROLES_CATALOG,
    ROLES_LIST,
    ROLES_ACTIVATE,
    ROLES_ADD,
    ROLE_SHOW,
    ROLE_UPDATE,
    ROLE_BODY,
    ROLE_STATUS,
    ROLE_SET_DEFAULT,
    ROLE_REGEN,
    ROLE_REMOVE,
    ROLE_VIEW_ADD,
    ROLE_VIEW_DISABLE,
    DEVELOPERS_LIST,
    SKILLS_ADD,
    SKILL_SHOW,
    SKILL_UPDATE,
    SKILL_BODY,
    SKILL_STATUS,
    SKILL_REGEN,
    SKILL_REMOVE,
    SKILL_REFS,
    SKILL_REF_ADD,
    SKILL_REF_RM,
    SKILL_LINK_ROLE,
    SKILL_UNLINK_ROLE,
    SKILL_VIEW_ADD,
    SKILL_VIEW_DISABLE,
    OPERATORS_LIST,
    OPERATORS_ADD,
    OPERATOR_SHOW,
    OPERATOR_UPDATE,
    OPERATOR_BODY,
    OPERATOR_STATUS,
    OPERATOR_REMOVE,
    ROLE_COMMENTS,
    ROLE_COMMENT_ADD,
    ROLE_COMMENT_SHOW,
    ROLE_COMMENT_EDIT,
    ROLE_COMMENT_REMOVAL,
    ROLE_COMMENT_REMOVE,
    SKILL_COMMENTS,
    SKILL_COMMENT_ADD,
    SKILL_COMMENT_SHOW,
    SKILL_COMMENT_EDIT,
    SKILL_COMMENT_REMOVAL,
    SKILL_COMMENT_REMOVE,
    OPERATOR_COMMENTS,
    OPERATOR_COMMENT_ADD,
    OPERATOR_COMMENT_SHOW,
    OPERATOR_COMMENT_EDIT,
    OPERATOR_COMMENT_REMOVAL,
    OPERATOR_COMMENT_REMOVE,
    # --- squad state
    BOARD_LIST,
    BOARD_POST,
    BOARD_CLEAR,
    MEMORY_LIST,
    MEMORY_SEARCH,
    MEMORY_SHOW,
    MEMORY_ADD,
    MEMORY_FORGET,
    WORKFLOW_SHOW,
    WORKFLOW_TYPES,
    WORKFLOW_SUBENTITY_KINDS,
    WORKFLOW_LIFECYCLES,
    WORKFLOW_COLLECTIONS,
    WORKFLOW_STATUSES,
    WORKFLOW_ROLES,
    WORKFLOW_REF_KINDS,
    WORKFLOW_VIEWS,
    WORKFLOW_VIEW,
    WORKFLOW_LINT,
    OVERRIDES_LIST,
    OVERRIDES_DIFF,
    OVERRIDES_SCAFFOLD,
    OVERRIDES_UPDATE,
    REFLOG,
    CHECK,
    SYNC,
    # --- corpus-wide
    REPAIR,
    RENUMBER,
    MIGRATE,
    REPAD,
    RENAME_TYPE,
    RENAME_STATUS,
    RENAME_FIELD,
    RENAME_KIND,
    IMPORT,
    INIT,
    ADOPT,
)
