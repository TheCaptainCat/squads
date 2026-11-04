"""The checks of ``sq source check`` that every tracker shares: whether the host answers, the
credential works and reads the scope, whether every value a map names exists, and which tracker
values nothing maps. A tracker names its endpoints and what it can enumerate."""

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable, Iterator

from squads._errors import SquadsError
from squads._sources._connector import LABELS, TYPE, Issue
from squads._sources._filter import words
from squads._sources._http import (
    HttpClient,
    MalformedAnswerError,
    NotFoundError,
    RateLimitedError,
    RejectedError,
    StatusError,
)
from squads._sources._maps import mapped_types
from squads._sources._probes import (
    ACCESS,
    COVERAGE,
    FAIL,
    PASS,
    VOCABULARY,
    WARN,
    Expected,
    Family,
    ProbeResult,
)
from squads._sources._spec import SourceScope

_SERVER_ERROR = 500


def sources_toml(expected: Expected, table: str) -> str:
    """Where *table* of *expected*'s source is edited, for a fix line."""
    return f"[sources.{expected.source}.maps.{table}] in sources.toml"


def filter_toml(expected: Expected) -> str:
    """Where the filter of *expected*'s source is edited, for a fix line."""
    return f"[sources.{expected.source}.filter] in sources.toml"


class TrackerProbes(ABC):
    """The probes of one source, over its connector's client and listing."""

    #: The tracker's name in messages.
    tracker: str
    #: The separator of a scoped label (``scope::value``), or empty when the tracker has none.
    label_scope: str = ""

    def __init__(
        self, http: HttpClient, base: str, scope: SourceScope, listing: Callable[[], list[Issue]]
    ) -> None:
        self._http = http
        self._base = base
        self._scope = scope
        self._listing = listing

    @abstractmethod
    def reach(self) -> None:
        """Ask the host something it answers without a credential."""

    @abstractmethod
    def identify(self) -> str:
        """Who the token is, as a sentence. Raises ``MalformedAnswerError`` naming the path
        when the tracker answers something that is not a user."""

    @abstractmethod
    def read(self) -> bool:
        """Whether the scope holds at least one issue; raises when the tracker refuses it."""

    @abstractmethod
    def credential_fix(self, expected: Expected) -> str:
        """The fix for a rejected token."""

    @abstractmethod
    def read_fix(self, expected: Expected) -> str:
        """The fix for a token that cannot read issues."""

    @abstractmethod
    def known_values(self, side: str, issues: list[Issue]) -> tuple[frozenset[str], bool]:
        """The values the tracker has on *side* of an issue, and whether that list is complete.
        An incomplete one holds only what the in-scope *issues* carry."""

    @abstractmethod
    def link_types(self) -> tuple[str, ...]:
        """The link types the tracker has, as an issue's links name them."""

    @abstractmethod
    def user_exists(self, user_id: str) -> None:
        """Ask for user *user_id*; raises ``NotFoundError`` when the tracker has none."""

    def run(self, family: Family, expected: Expected) -> Iterator[ProbeResult]:
        """The results of one family."""
        if family == ACCESS:
            yield from self._access(expected)
        elif family == VOCABULARY:
            yield from self._vocabulary(expected)
        elif family == COVERAGE:
            yield from self._coverage(expected)

    # ------------------------------------------------------------------ access
    def _access(self, expected: Expected) -> Iterator[ProbeResult]:
        for step in (self._host, self._who, self._read):
            results = list(step(expected))
            yield from results
            if any(r.blocking for r in results):
                return

    def scope_text(self) -> str:
        """The source's scope as a message quotes it."""
        return f"{self._scope.key} {self._scope.value!r}"

    def _host_fix(self, expected: Expected) -> str:
        return (
            f"correct `base_url` of source {expected.source!r} in sources.toml, or the host's "
            "network"
        )

    def _host(self, expected: Expected) -> Iterator[ProbeResult]:
        try:
            self.reach()
        except (RejectedError, NotFoundError):  # fmt: skip
            pass  # the host answered, even if it refuses this request
        except RateLimitedError as exc:
            yield self._limited(exc)
            return
        except SquadsError as exc:
            yield ProbeResult(ACCESS, FAIL, str(exc), self._host_fix(expected))
            return
        yield ProbeResult(ACCESS, PASS, f"{self._base} answers")

    def _who(self, expected: Expected) -> Iterator[ProbeResult]:
        host_fix = self._host_fix(expected)
        try:
            who = self.identify()
        except RejectedError as exc:
            yield ProbeResult(
                ACCESS,
                FAIL,
                f"{self._base} did not accept the token: {exc}",
                self.credential_fix(expected),
            )
            return
        except MalformedAnswerError as exc:
            yield ProbeResult(
                ACCESS, FAIL, f"{self._base}{exc} answered something other than a user", host_fix
            )
            return
        except RateLimitedError as exc:
            yield self._limited(exc)
            return
        except SquadsError as exc:
            yield ProbeResult(
                ACCESS, FAIL, f"cannot ask {self._base} who the token is: {exc}", host_fix
            )
            return
        yield ProbeResult(ACCESS, PASS, who)

    @staticmethod
    def _limited(exc: RateLimitedError) -> ProbeResult:
        return ProbeResult(
            ACCESS, FAIL, str(exc), "wait until the tracker's limit resets, then run it again"
        )

    def _read_failure(self, exc: SquadsError, expected: Expected) -> ProbeResult:
        """Why the scope could not be read, and the fix that fits the cause."""
        if isinstance(exc, RateLimitedError):
            return self._limited(exc)
        if isinstance(exc, RejectedError):
            return ProbeResult(
                ACCESS, FAIL, f"the token cannot read issues: {exc}", self.read_fix(expected)
            )
        if isinstance(exc, StatusError) and exc.status < _SERVER_ERROR:
            return ProbeResult(
                ACCESS,
                FAIL,
                f"the scope {self.scope_text()} is not accepted: {exc}",
                f"correct `{self._scope.key}` of source {expected.source!r} in sources.toml",
            )
        if isinstance(exc, NotFoundError):
            return ProbeResult(
                ACCESS,
                FAIL,
                f"the scope {self.scope_text()} does not exist or is not visible to the token",
                f"correct `{self._scope.key}` of source {expected.source!r} in sources.toml",
            )
        return ProbeResult(ACCESS, FAIL, str(exc), self._host_fix(expected))

    def _read(self, expected: Expected) -> Iterator[ProbeResult]:
        name = expected.source
        try:
            selects = self.read()
        except MalformedAnswerError as exc:
            yield ProbeResult(
                ACCESS,
                FAIL,
                f"{self._base}{exc} answered something other than a list of issues",
                self._host_fix(expected),
            )
            return
        except SquadsError as exc:
            yield self._read_failure(exc, expected)
            return
        if not selects:
            yield ProbeResult(
                ACCESS,
                WARN,
                f"the scope {self.scope_text()} holds no issue",
                f"create an issue in the scope, or correct `{self._scope.key}` of source "
                f"{name!r} in sources.toml",
            )
            return
        yield ProbeResult(ACCESS, PASS, "the token reads the issues of the scope")

    # -------------------------------------------------------------- vocabulary
    def _vocabulary(self, expected: Expected) -> Iterator[ProbeResult]:
        maps = expected.maps
        tables = (
            [
                (f"maps.types.{side}", sources_toml(expected, f"types.{side}"), side, table)
                for side, table in sorted(maps.types.items())
            ]
            + [
                (
                    f"maps.fields.{code}.{side}",
                    sources_toml(expected, f"fields.{code}.{side}"),
                    side,
                    table,
                )
                for code, sides in sorted(maps.fields.items())
                for side, table in sorted(sides.items())
            ]
            + [
                (f"filter.{side}", filter_toml(expected), side, dict.fromkeys(words(expression)))
                for side, expression in sorted(expected.filter.items())
            ]
        )
        try:
            issues = self._listing()
            links = self.link_types()
            known = {side: self.known_values(side, issues) for _, _, side, _ in tables}
        except SquadsError as exc:
            yield ProbeResult(VOCABULARY, FAIL, f"cannot read the tracker's vocabulary: {exc}")
            return
        clean = True
        for label, where, side, table in tables:
            values, complete = known[side]
            for key in sorted(set(table) - values):
                clean = False
                yield self._missing(label, where, side, key, complete and bool(issues))
        if issues and expected.filter and not any(self._accepts(expected, i) for i in issues):
            clean = False
            yield ProbeResult(
                VOCABULARY,
                WARN,
                f"the filter accepts none of the {len(issues)} issue(s) of the scope",
                f"correct it in {filter_toml(expected)}",
            )
        for link in sorted(set(maps.links) - set(links)):
            clean = False
            yield ProbeResult(
                VOCABULARY,
                FAIL,
                f"maps.links: {link!r} is not a {self.tracker} link type",
                f"use one of {', '.join(links)} in {sources_toml(expected, 'links')}",
            )
        if clean:
            names = "maps and the filter" if expected.filter else "maps"
            yield ProbeResult(
                VOCABULARY, PASS, f"every value the {names} name exists on the tracker"
            )

    @staticmethod
    def _accepts(expected: Expected, issue: Issue) -> bool:
        return all(expr.matches(issue.values(side)) for side, expr in expected.filter.items())

    @staticmethod
    def _missing(label: str, where: str, side: str, key: str, certain: bool) -> ProbeResult:
        """The result for a map or filter *key* that *side* of the tracker was not found to hold:
        a failure when the list of values is complete, else a warning."""
        noun = {LABELS: "labels", TYPE: "issue types"}.get(side, f"{side} values")
        fix = f"correct it in {where}"
        if certain:
            return ProbeResult(
                VOCABULARY,
                FAIL,
                f"{label}: {key!r} is not among the tracker's {noun}",
                f"{fix}, or create it on the tracker",
            )
        return ProbeResult(
            VOCABULARY,
            WARN,
            f"{label}: {key!r} is carried by no issue in the scope, so it cannot be confirmed "
            f"among the tracker's {noun}",
            fix,
        )

    # ---------------------------------------------------------------- coverage
    def _coverage(self, expected: Expected) -> Iterator[ProbeResult]:
        try:
            issues = [i for i in self._listing() if self._accepts(expected, i)]
        except SquadsError as exc:
            yield ProbeResult(COVERAGE, WARN, f"cannot list the issues: {exc}")
            return
        unmapped = sum(1 for i in issues if not mapped_types(expected.maps, i))
        note = f"{unmapped} selected issue(s) map to no type and are skipped by the pull"
        warned = False
        for result in (
            *self._unmapped_types(expected, issues),
            *self._unmapped_labels(expected, issues),
            *self._unknown_authors(expected, issues),
            *self._stale_identities(expected),
        ):
            warned = True
            yield result
        if not warned:
            counted = f"; {note}" if unmapped else ""
            yield ProbeResult(
                COVERAGE,
                PASS,
                f"every in-scope value, author and identity is accounted for{counted}",
            )
        elif unmapped:
            yield ProbeResult(COVERAGE, PASS, note)

    @staticmethod
    def _unmapped_types(expected: Expected, issues: list[Issue]) -> Iterator[ProbeResult]:
        for issue in issues:
            if len(types := mapped_types(expected.maps, issue)) > 1:
                yield ProbeResult(
                    COVERAGE,
                    WARN,
                    f"{issue.key} maps to several types: {', '.join(sorted(types))}",
                    f"make the maps in {sources_toml(expected, 'types')} choose one",
                )

    def _unmapped_labels(self, expected: Expected, issues: list[Issue]) -> Iterator[ProbeResult]:
        scope = self.label_scope
        if not scope:
            return
        seen: dict[tuple[str, str], list[str]] = defaultdict(list)
        for code, sides in sorted(expected.maps.fields.items()):
            table = sides.get(LABELS, {})
            scopes = {label.partition(scope)[0] for label in table if scope in label}
            for issue in issues:
                for label in issue.labels:
                    if (
                        label.partition(scope)[0] in scopes
                        and scope in label
                        and label not in table
                    ):
                        seen[(code, label)].append(issue.key)
        for (code, label), keys in sorted(seen.items()):
            yield ProbeResult(
                COVERAGE,
                WARN,
                f"label {label!r} on {', '.join(keys)} has no entry in maps.fields.{code}.{LABELS}",
                f"add it to {sources_toml(expected, f'fields.{code}.{LABELS}')}",
            )

    @staticmethod
    def _unknown_authors(expected: Expected, issues: list[Issue]) -> Iterator[ProbeResult]:
        known = {user_id for _, user_id in expected.identities}
        authors: dict[tuple[str, str], list[str]] = defaultdict(list)
        for issue in issues:
            if issue.author_id not in known:
                authors[(issue.author_id, issue.author_handle)].append(issue.key)
        for user_id, handle, where in expected.commenters:
            if user_id not in known:
                authors[(user_id, handle)].append(where)
        for (user_id, handle), keys in sorted(authors.items()):
            yield ProbeResult(
                COVERAGE,
                WARN,
                f"author {handle} (id {user_id}) of {', '.join(keys)} is in no operator's "
                "identities",
                f"run `sq operator <slug> update --identities {expected.source}={user_id}`",
            )

    def _stale_identities(self, expected: Expected) -> Iterator[ProbeResult]:
        for slug, user_id in expected.identities:
            try:
                self.user_exists(user_id)
            except NotFoundError:
                yield ProbeResult(
                    COVERAGE,
                    WARN,
                    f"{slug} holds user id {user_id} of source {expected.source!r}, "
                    "which the tracker no longer resolves",
                    f"run `sq operator {slug} update --identities {expected.source}=<handle>`",
                )
            except SquadsError as exc:
                yield ProbeResult(
                    COVERAGE, WARN, f"cannot resolve user id {user_id} of {slug}: {exc}"
                )
