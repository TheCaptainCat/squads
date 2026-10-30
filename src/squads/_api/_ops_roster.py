"""The roster operations of the table."""

from squads._api._api import Operation
from squads._api._dto._comments import Comments
from squads._api._dto._operators import (
    OperatorAddRequest,
    OperatorList,
    OperatorListRequest,
    OperatorShow,
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
SKILL_COMMENTS = Operation(
    "skills.comments",
    "GET",
    "/v1/skills/{addr}/comments",
    RosterAddress,
    Comments,
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
