"""The Jira Cloud connector, on REST API v3 with an account's email and API token."""

import base64
import json
import re
import urllib.parse
from collections.abc import Iterator, Mapping
from email.message import Message
from typing import Any

from squads._errors import SquadsError
from squads._sources._http import Advance, NotFoundError, UnexpectedAnswerError, member_items
from squads._sources._jira._connector import JiraConnector, offset_advance
from squads._sources._records import mapping, names, records, text

#: The most labels one page of the label list returns.
_LABEL_PAGE = "1000"
#: An Atlassian account ID: the legacy 24-character form or the ``<n>:<uuid>`` form.
_ACCOUNT_ID_RE = re.compile(r"\d+:[0-9a-f-]{36}|[0-9a-f]{24}")


def _next_token(
    document: Any, headers: Message, params: Mapping[str, str]
) -> dict[str, str] | None:
    """The next query of a search that names the following page in ``nextPageToken``."""
    page = mapping(document)
    token = text(page, "nextPageToken")
    if token and page.get("isLast") is not True:
        return {**params, "nextPageToken": token}
    if not token and page.get("isLast") is False:
        raise UnexpectedAnswerError("a search page that is not the last names no next page")
    return None


_ADVANCE: Advance = _next_token


class JiraCloudConnector(JiraConnector):
    """Reads issues, comments, links and users of one Jira Cloud site; text is Atlassian Document
    Format."""

    credential_fields = ("user", "token")
    api = "/rest/api/3"
    _labels_complete = True

    def _headers(self, credential: Mapping[str, str]) -> dict[str, str]:
        pair = f"{credential.get('user', '')}:{credential.get('token', '')}".encode()
        return {
            "Authorization": f"Basic {base64.b64encode(pair).decode('ascii')}",
            "Accept": "application/json",
        }

    def _search(self, jql: str, fields: str, size: str) -> Iterator[Any]:
        return self._http.paged(
            f"{self.api}/search/jql",
            {"jql": jql, "fields": fields, "maxResults": size},
            _ADVANCE,
            member_items("issues"),
        )

    def _text(self, value: object) -> str:
        if isinstance(value, Mapping):
            return json.dumps(value, ensure_ascii=False)
        return value if isinstance(value, str) else ""

    def _comment_query(self) -> dict[str, str]:
        return {}

    def _agents_only(self, comment: Mapping[str, Any]) -> bool:
        return comment.get("jsdPublic") is False

    def _person(self, record: object) -> tuple[str, str, str]:
        user = mapping(record)
        account = text(user, "accountId")
        return account, account, text(user, "displayName")

    def user_url(self, handle: str) -> str:
        """The profile address of the account *handle*."""
        return f"{self._base}/jira/people/{urllib.parse.quote(handle.removeprefix('@'), safe='')}"

    def resolve_handle(self, handle: str) -> str | None:
        """The account ID of *handle*: an account ID itself, or the one user whose display name
        or email is *handle* exactly. A search that finds no exact match is refused, listing what
        it found; ``None`` when nothing was found."""
        wanted = handle.removeprefix("@")
        if _ACCOUNT_ID_RE.fullmatch(wanted):
            try:
                user = self._http.get(f"{self.api}/user", {"accountId": wanted})
            except NotFoundError:
                return None
            return text(mapping(user), "accountId") or None
        found = list(records(self._http.get(f"{self.api}/user/search", {"query": wanted})))
        exact = [
            u
            for u in found
            if wanted.lower() in (text(u, "displayName").lower(), text(u, "emailAddress").lower())
        ]
        if len(exact) == 1:
            return text(exact[0], "accountId") or None
        if not found:
            return None
        candidates = ", ".join(
            f"{text(u, 'displayName')} ({text(u, 'accountId')})" for u in (exact or found)[:5]
        )
        raise SquadsError(
            f"no one user has the display name or email {wanted!r} exactly; Jira found "
            f"{candidates}. Name the account as @<accountId>"
        )

    def _user_exists(self, user_id: str) -> None:
        self._http.get(f"{self.api}/user", {"accountId": user_id})

    def _describe(self, who: Mapping[str, object]) -> str:
        return f"authenticated as {text(who, 'displayName')} (id {text(who, 'accountId')})"

    def _extra_labels(self) -> set[str]:
        pages = self._http.paged(
            f"{self.api}/label",
            {"startAt": "0", "maxResults": _LABEL_PAGE},
            offset_advance("values"),
            member_items("values", objects=False),
        )
        return set(names(list(pages)))
