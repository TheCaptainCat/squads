"""The item_writes operations of the table."""

from squads._api._api import Operation
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
