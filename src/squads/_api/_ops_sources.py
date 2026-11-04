"""The source operations of the table. None has a route: they run in the process that serves the
squad, reached through its command endpoint or in process, so no resource route or OpenAPI entry
can read or write a credential."""

from squads._api._api import Operation, Timeout
from squads._api._dto import (
    CredentialFields,
    CredentialFieldsRequest,
    CredentialRemoved,
    CredentialRemoveRequest,
    CredentialSetRequest,
    CredentialWritten,
    SourceChecked,
    SourceCheckRequest,
    SourceListed,
    SourceListRequest,
    SourcePulled,
    SourcePullRequest,
    SourceRefreshed,
    SourceRefreshRequest,
    SourceRelinked,
    SourceRelinkRequest,
    SourceUnlinked,
    SourceUnlinkRequest,
)

SOURCE_CREDENTIAL_FIELDS = Operation(
    "sources.credential_fields",
    None,
    None,
    CredentialFieldsRequest,
    CredentialFields,
    private=True,
    read_only=True,
)
SOURCE_CREDENTIAL_SET = Operation(
    "sources.credential_set", None, None, CredentialSetRequest, CredentialWritten, private=True
)
SOURCE_CREDENTIAL_REMOVE = Operation(
    "sources.credential_remove",
    None,
    None,
    CredentialRemoveRequest,
    CredentialRemoved,
    private=True,
)
SOURCE_PULL = Operation(
    "sources.pull",
    None,
    None,
    SourcePullRequest,
    SourcePulled,
    private=True,
    timeout=Timeout.LONG,
)
SOURCE_CHECK = Operation(
    "sources.check",
    None,
    None,
    SourceCheckRequest,
    SourceChecked,
    private=True,
    read_only=True,
    timeout=Timeout.LONG,
)
SOURCE_LIST = Operation(
    "sources.list", None, None, SourceListRequest, SourceListed, private=True, read_only=True
)
SOURCE_REFRESH = Operation(
    "sources.refresh", None, None, SourceRefreshRequest, SourceRefreshed, private=True
)
SOURCE_UNLINK = Operation(
    "sources.unlink", None, None, SourceUnlinkRequest, SourceUnlinked, private=True
)
SOURCE_RELINK = Operation(
    "sources.relink", None, None, SourceRelinkRequest, SourceRelinked, private=True
)
