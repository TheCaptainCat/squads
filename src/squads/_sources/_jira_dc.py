"""The Jira Data Center connector, on REST API v2 with a personal access token."""

import urllib.parse
from collections.abc import Iterator, Mapping
from typing import Any

from squads._sources._http import NotFoundError, member_items
from squads._sources._jira import JiraConnector, offset_advance
from squads._sources._records import mapping, records, text

#: The comment property through which Jira Service Management marks an agent-only comment.
_INTERNAL_PROPERTY = "sd.public.comment"


class JiraDcConnector(JiraConnector):
    """Reads issues, comments, links and users of one Jira Data Center instance; text is Jira
    wiki markup."""

    credential_fields = ("token",)
    api = "/rest/api/2"
    _labels_complete = False

    def _headers(self, credential: Mapping[str, str]) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {credential.get('token', '')}",
            "Accept": "application/json",
        }

    def _search(self, jql: str, fields: str, size: str) -> Iterator[Any]:
        return self._http.paged(
            f"{self.api}/search",
            {"jql": jql, "fields": fields, "maxResults": size, "startAt": "0"},
            offset_advance("issues"),
            member_items("issues"),
        )

    def _text(self, value: object) -> str:
        return value if isinstance(value, str) else ""

    def _comment_query(self) -> dict[str, str]:
        return {"expand": "properties"}

    def _agents_only(self, comment: Mapping[str, Any]) -> bool:
        return any(
            text(prop, "key") == _INTERNAL_PROPERTY
            and mapping(prop.get("value")).get("internal") is True
            for prop in records(comment.get("properties"))
        )

    def _person(self, record: object) -> tuple[str, str, str]:
        user = mapping(record)
        handle = text(user, "name")
        return text(user, "key") or handle, handle, text(user, "displayName")

    def user_url(self, handle: str) -> str:
        """The profile address of the user named *handle*."""
        name = urllib.parse.quote(handle.removeprefix("@"), safe="")
        return f"{self._base}/secure/ViewProfile.jspa?name={name}"

    def resolve_handle(self, handle: str) -> str | None:
        """The user key behind the username *handle*, or ``None`` when there is no such user."""
        try:
            user = mapping(
                self._http.get(f"{self.api}/user", {"username": handle.removeprefix("@")})
            )
        except NotFoundError:
            return None
        return text(user, "key") or text(user, "name") or None

    def _user_exists(self, user_id: str) -> None:
        self._http.get(f"{self.api}/user", {"key": user_id})

    def _describe(self, who: Mapping[str, object]) -> str:
        return f"authenticated as {text(who, 'name')} (id {text(who, 'key') or text(who, 'name')})"

    def _extra_labels(self) -> set[str]:
        return set()
