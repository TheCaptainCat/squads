"""The workflow operations of the table."""

from squads._api._api import Grant, Ground, Mode, Operation
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

#: What an override command may do on a squad whose schema is behind the package's.
_OVERRIDE_GRANT = Grant(Ground.NO_SQUAD_STATE, behind=True, ahead=False)

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
