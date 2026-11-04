"""The source operations: the credential verbs, which fill and empty the per-user store the
serving process owns. No operation here returns, logs or stores a credential value in the squad."""

from squads._api import (
    CredentialFields,
    CredentialFieldsRequest,
    CredentialRemoved,
    CredentialRemoveRequest,
    CredentialSetRequest,
    CredentialWritten,
    Response,
)
from squads._errors import SquadsError
from squads._services._base import ServiceCore
from squads._services._fetch import connector_class
from squads._sources import SourceSpec


class SourceOpsMixin(ServiceCore):
    """The operations on the sources a squad declares that need no tracker data, so they work on a
    disabled source as on an enabled one."""

    def _declared_source(self, name: str) -> SourceSpec:
        return self.sources().source(name)

    async def credential_fields(self, req: CredentialFieldsRequest) -> Response[CredentialFields]:
        """The fields the credential of the source is made of."""
        source = self._declared_source(req.source)
        fields = list(connector_class(source).credential_fields)
        return Response(
            data=CredentialFields(source=source.name, base_url=source.base_url, fields=fields)
        )

    async def set_credential(self, req: CredentialSetRequest) -> Response[CredentialWritten]:
        """Store the credential of the source, one value for each field its connector names."""
        source = self._declared_source(req.source)
        fields = list(connector_class(source).credential_fields)
        if set(req.values) != set(fields) or any(not value for value in req.values.values()):
            raise SquadsError(
                f"the credential of source {source.name!r} takes a non-empty value for each of: "
                f"{', '.join(fields)}"
            )
        path = self.credentials.write_entry(source.base_url, req.values)
        return Response(
            data=CredentialWritten(
                source=source.name, base_url=source.base_url, fields=fields, path=str(path)
            )
        )

    async def remove_credential(self, req: CredentialRemoveRequest) -> Response[CredentialRemoved]:
        """Delete the credential of the source; nothing happens when it has none."""
        source = self._declared_source(req.source)
        removed = self.credentials.remove_entry(source.base_url)
        return Response(
            data=CredentialRemoved(source=source.name, base_url=source.base_url, removed=removed)
        )
