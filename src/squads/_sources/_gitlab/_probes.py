"""The checks of ``sq source check`` for GitLab: whether the host answers, the token works and
reads the scope, whether every value a map names exists, and which tracker values nothing maps."""

import urllib.parse
from collections.abc import Callable, Mapping

from squads._sources._connector import TYPE, Issue
from squads._sources._http import HttpClient, MalformedAnswerError
from squads._sources._probes import Expected
from squads._sources._records import is_object, mapping, records, text
from squads._sources._spec import SourceScope
from squads._sources._tracker_probes import TrackerProbes

#: GitLab v4's ``issue_type`` and issue link ``link_type`` values: tracker API names.
_ISSUE_TYPES = (
    "issue",
    "incident",
    "test_case",
    "requirement",
    "task",
    "objective",
    "key_result",
    "ticket",
)
_LINK_TYPES = ("relates_to", "blocks", "is_blocked_by")


class GitLabProbes(TrackerProbes):
    """The probes of one GitLab source, over the connector's client and its listing."""

    tracker = "GitLab"
    label_scope = "::"

    def __init__(
        self,
        http: HttpClient,
        base: str,
        path: str,
        query: Mapping[str, str],
        scope: SourceScope,
        listing: Callable[[], list[Issue]],
    ) -> None:
        super().__init__(http, base, scope, listing)
        self._path = path
        self._query = dict(query)

    def reach(self) -> None:
        """Ask for the instance's version."""
        self._http.get("/api/v4/version")

    def identify(self) -> str:
        """Ask the instance who the token belongs to."""
        user: object = self._http.get("/api/v4/user")
        if not is_object(user):
            raise MalformedAnswerError("/api/v4/user")
        who = mapping(user)
        return f"authenticated as {who.get('username')} (id {who.get('id')})"

    def read(self) -> bool:
        """Whether the scope holds an issue."""
        page: object = self._http.get(self._path, {**self._query, "per_page": "1", "page": "1"})
        return not (isinstance(page, list) and not page)

    def credential_fix(self, expected: Expected) -> str:
        """Store a valid token."""
        return (
            f"run `sq source credential set {expected.source}` with a valid personal or project "
            "token"
        )

    def read_fix(self, expected: Expected) -> str:
        """Store a token that has the ``read_api`` scope."""
        return (
            f"create a token with the `read_api` scope, then run "
            f"`sq source credential set {expected.source}`"
        )

    def known_values(self, side: str, issues: list[Issue]) -> tuple[frozenset[str], bool]:
        """GitLab's issue types, or the labels of every project that holds an in-scope issue
        (group labels included)."""
        if side == TYPE:
            return frozenset(_ISSUE_TYPES), True
        projects = sorted({dict(i.locator).get("project_id", "") for i in issues} - {""})
        labels: set[str] = set()
        for project in projects:
            path = f"/api/v4/projects/{urllib.parse.quote(project, safe='')}/labels"
            for label in records(list(self._http.pages(path, {"include_ancestor_groups": "true"}))):
                labels.add(text(label, "name"))
        return frozenset(labels), True

    def link_types(self) -> tuple[str, ...]:
        """GitLab's link types."""
        return _LINK_TYPES

    def user_exists(self, user_id: str) -> None:
        """Ask for the user by ID."""
        self._http.get(f"/api/v4/users/{urllib.parse.quote(user_id, safe='')}")
