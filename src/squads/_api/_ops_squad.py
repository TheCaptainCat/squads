"""The squad operations of the table."""

from squads._api._api import Grant, Ground, Mode, Operation, Timeout
from squads._api._dto._check import CheckReport, CheckRequest, SyncReport, SyncRequest
from squads._api._dto._reflog import Reflog, ReflogRequest
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

#: What the migration may do on a squad whose schema is behind the package's.
_MIGRATION_GRANT = Grant(Ground.MIGRATION, behind=True, ahead=False)

REFLOG = Operation("reflog", "GET", "/v1/reflog", ReflogRequest, Reflog, json_field="items")
CHECK = Operation(
    "check", "GET", "/v1/check", CheckRequest, CheckReport, mode=Mode.CHECK, json_field="items"
)
SYNC = Operation("sync", "POST", "/v1/squad/sync", SyncRequest, SyncReport)
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
INIT = Operation("squad.init", None, None, InitRequest, InitReport, local_only=True)
ADOPT = Operation("squad.adopt", None, None, AdoptRequest, AdoptReport, local_only=True)
