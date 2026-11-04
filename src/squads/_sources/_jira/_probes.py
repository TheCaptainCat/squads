"""The checks of ``sq source check`` for Jira, shared by the cloud and the Data Center versions:
whether the host answers, the credential works and the JQL scope reads, whether every value a map
names exists, and which tracker values nothing maps."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from squads._sources._connector import LABELS, TYPE, Issue
from squads._sources._http import HttpClient, MalformedAnswerError
from squads._sources._probes import Expected
from squads._sources._records import is_object, mapping, names, records, text
from squads._sources._tracker_probes import TrackerProbes

#: The REST resources that list the issue types and the priorities: tracker API names.
_LISTS = ("issuetype", "priority")


@dataclass(frozen=True)
class JiraHooks:
    """What differs between the Jira versions: how the scope is read, how the account and a user
    are asked for, and which labels exist beyond those on the in-filter issues."""

    select: Callable[[], bool]
    describe: Callable[[Mapping[str, object]], str]
    user_exists: Callable[[str], None]
    extra_labels: Callable[[], set[str]]
    labels_complete: bool


class JiraProbes(TrackerProbes):
    """The probes of one Jira source."""

    tracker = "Jira"

    def __init__(
        self,
        http: HttpClient,
        base: str,
        api: str,
        jql: str,
        listing: Callable[[], list[Issue]],
        hooks: JiraHooks,
    ) -> None:
        super().__init__(http, base, listing)
        self._api = api
        self._jql = jql
        self._hooks = hooks

    def reach(self) -> None:
        """Ask for the instance's server information."""
        self._http.get(f"{self._api}/serverInfo")

    def identify(self) -> str:
        """Ask the instance who the credential belongs to."""
        path = f"{self._api}/myself"
        user: object = self._http.get(path)
        if not is_object(user):
            raise MalformedAnswerError(path)
        return self._hooks.describe(mapping(user))

    def read(self) -> bool:
        """Whether the JQL scope returns an issue."""
        return self._hooks.select()

    def scope_text(self) -> str:
        """The JQL scope, as a message quotes it."""
        return f"jql {self._jql!r}"

    def credential_fix(self, expected: Expected) -> str:
        """Store a valid credential."""
        return f"run `sq source credential set {expected.source}` with a valid credential"

    def read_fix(self, expected: Expected) -> str:
        """Store a credential whose account can browse the projects."""
        return (
            "use an account with the Browse Projects permission on the scope's projects, then "
            f"run `sq source credential set {expected.source}`"
        )

    def known_values(self, side: str, issues: list[Issue]) -> tuple[frozenset[str], bool]:
        """The issue types, priorities or labels the instance has. Its labels are the ones on
        the in-filter issues and every label the version lists."""
        if side == LABELS:
            seen = {label for issue in issues for label in issue.labels}
            return frozenset(seen | self._hooks.extra_labels()), self._hooks.labels_complete
        listed = _LISTS[0] if side == TYPE else _LISTS[1]
        return frozenset(names(self._http.get(f"{self._api}/{listed}"))), True

    def link_types(self) -> tuple[str, ...]:
        """The directional phrases of the instance's link types (``blocks``, ``is blocked by``)."""
        types = mapping(self._http.get(f"{self._api}/issueLinkType")).get("issueLinkTypes")
        phrases = {text(t, key) for t in records(types) for key in ("outward", "inward")}
        return tuple(sorted(phrases - {""}))

    def user_exists(self, user_id: str) -> None:
        """Ask for the user by ID."""
        self._hooks.user_exists(user_id)
