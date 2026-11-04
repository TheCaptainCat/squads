"""The checks of ``sq source check`` for GitLab: whether the host answers, the token works and
reads the filter, whether every value a map names exists, and which tracker values nothing maps."""

import urllib.parse
from collections import defaultdict
from collections.abc import Callable, Iterator, Mapping
from typing import Any, cast

from squads._errors import SquadsError
from squads._sources._connector import Issue
from squads._sources._http import HttpClient, NotFoundError, RejectedError
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
_SCOPE = "::"


def _sources_toml(expected: Expected, table: str) -> str:
    return f"[sources.{expected.source}.maps.{table}] in sources.toml"


class GitLabProbes:
    """The probes of one GitLab source, over the connector's client and its listing."""

    def __init__(
        self,
        http: HttpClient,
        base: str,
        query: Mapping[str, str],
        listing: Callable[[], list[Issue]],
    ) -> None:
        self._http = http
        self._base = base
        self._query = dict(query)
        self._listing = listing

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

    def _host_fix(self, expected: Expected) -> str:
        return (
            f"correct `base_url` of source {expected.source!r} in sources.toml, or the host's "
            "network"
        )

    def _host(self, expected: Expected) -> Iterator[ProbeResult]:
        host_fix = self._host_fix(expected)
        try:
            self._http.get("/api/v4/version")
        except (RejectedError, NotFoundError):  # fmt: skip
            pass  # the host answered, even if it refuses this request
        except SquadsError as exc:
            yield ProbeResult(ACCESS, FAIL, str(exc), host_fix)
            return
        yield ProbeResult(ACCESS, PASS, f"{self._base} answers")

    def _who(self, expected: Expected) -> Iterator[ProbeResult]:
        name, host_fix = expected.source, self._host_fix(expected)
        token_fix = f"run `sq source credential set {name}` with a valid personal or project token"
        try:
            user: object = self._http.get("/api/v4/user")
        except RejectedError as exc:
            yield ProbeResult(
                ACCESS, FAIL, f"{self._base} did not accept the token: {exc}", token_fix
            )
            return
        except SquadsError as exc:
            yield ProbeResult(
                ACCESS, FAIL, f"cannot ask {self._base} who the token is: {exc}", host_fix
            )
            return
        if not isinstance(user, Mapping):
            yield ProbeResult(
                ACCESS,
                FAIL,
                f"{self._base}/api/v4/user answered something other than a user",
                host_fix,
            )
            return
        who = cast("Mapping[str, Any]", user)
        yield ProbeResult(
            ACCESS, PASS, f"authenticated as {who.get('username')} (id {who.get('id')})"
        )

    def _read(self, expected: Expected) -> Iterator[ProbeResult]:
        name = expected.source
        try:
            page: object = self._http.get(
                "/api/v4/issues", {**self._query, "per_page": "1", "page": "1"}
            )
        except RejectedError as exc:
            yield ProbeResult(
                ACCESS,
                FAIL,
                f"the token cannot read issues: {exc}",
                f"create a token with the `read_api` scope, then run "
                f"`sq source credential set {name}`",
            )
            return
        except SquadsError as exc:
            yield ProbeResult(
                ACCESS,
                FAIL,
                f"the filter {self._query.get('labels', '')!r} is not accepted: {exc}",
                f"correct `filter` of source {name!r} in sources.toml",
            )
            return
        if isinstance(page, list) and not page:
            yield ProbeResult(
                ACCESS,
                WARN,
                f"the filter {self._query.get('labels', '')!r} selects no issue",
                f"label an issue on the tracker, or correct `filter` of source {name!r} "
                "in sources.toml",
            )
            return
        yield ProbeResult(ACCESS, PASS, "the token reads the issues the filter selects")

    # -------------------------------------------------------------- vocabulary
    def _labels(self, issues: list[Issue]) -> set[str]:
        projects = sorted({dict(i.locator).get("project_id", "") for i in issues} - {""})
        labels: set[str] = set()
        for project in projects:
            path = f"/api/v4/projects/{urllib.parse.quote(project, safe='')}/labels"
            for label in self._http.pages(path, {"include_ancestor_groups": "true"}):
                if isinstance(label, Mapping):
                    labels.add(str(cast("Mapping[str, Any]", label).get("name", "")))
        return labels

    def _vocabulary(self, expected: Expected) -> Iterator[ProbeResult]:
        maps = expected.maps
        wanted_labels = {code: set(table) for code, table in maps.fields.items()}
        try:
            issues = self._listing()
            labels = self._labels(issues)
        except SquadsError as exc:
            yield ProbeResult(VOCABULARY, FAIL, f"cannot read the tracker's labels: {exc}")
            return
        failed = noted = False
        for code, names in sorted(wanted_labels.items() if issues else []):
            for label in sorted(names - labels):
                failed = True
                yield ProbeResult(
                    VOCABULARY,
                    FAIL,
                    f"maps.fields.{code}: label {label!r} does not exist on the tracker",
                    f"create the label, or remove it from "
                    f"{_sources_toml(expected, 'fields.' + code)}",
                )
        for key in sorted(set(maps.types) - set(_ISSUE_TYPES) - labels):
            failed, noted = failed or bool(issues), noted or not issues
            yield ProbeResult(
                VOCABULARY,
                FAIL if issues else WARN,
                f"maps.types: {key!r} is neither a GitLab issue type nor a label on the tracker"
                if issues
                else f"maps.types: {key!r} is no GitLab issue type, and no label can be read "
                "while the filter selects no issue",
                f"correct it in {_sources_toml(expected, 'types')}, or create the label",
            )
        for link in sorted(set(maps.links) - set(_LINK_TYPES)):
            failed = True
            yield ProbeResult(
                VOCABULARY,
                FAIL,
                f"maps.links: {link!r} is not a GitLab link type",
                f"use one of {', '.join(_LINK_TYPES)} in {_sources_toml(expected, 'links')}",
            )
        if not issues and any(wanted_labels.values()):
            yield ProbeResult(
                VOCABULARY,
                WARN,
                "the mapped labels cannot be confirmed while the filter selects no issue",
            )
        elif not (failed or noted):
            yield ProbeResult(VOCABULARY, PASS, "every value the maps name exists on the tracker")

    # ---------------------------------------------------------------- coverage
    def _coverage(self, expected: Expected) -> Iterator[ProbeResult]:
        try:
            issues = self._listing()
        except SquadsError as exc:
            yield ProbeResult(COVERAGE, WARN, f"cannot list the issues: {exc}")
            return
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
            yield ProbeResult(
                COVERAGE, PASS, "every in-filter value, author and identity is accounted for"
            )

    @staticmethod
    def _unmapped_types(expected: Expected, issues: list[Issue]) -> Iterator[ProbeResult]:
        types = expected.maps.types
        unmapped = [
            i
            for i in issues
            if len({types[k] for k in (*i.labels, i.tracker_type) if k in types}) != 1
        ]
        if unmapped:
            keys = ", ".join(i.key for i in unmapped)
            yield ProbeResult(
                COVERAGE,
                WARN,
                f"{len(unmapped)} in-filter issue(s) map to no single type: {keys}",
                f"map their type or a label in {_sources_toml(expected, 'types')}",
            )

    @staticmethod
    def _unmapped_labels(expected: Expected, issues: list[Issue]) -> Iterator[ProbeResult]:
        seen: dict[tuple[str, str], list[str]] = defaultdict(list)
        for code, table in sorted(expected.maps.fields.items()):
            scopes = {label.partition(_SCOPE)[0] for label in table if _SCOPE in label}
            for issue in issues:
                for label in issue.labels:
                    if (
                        label.partition(_SCOPE)[0] in scopes
                        and _SCOPE in label
                        and label not in table
                    ):
                        seen[(code, label)].append(issue.key)
        for (code, label), keys in sorted(seen.items()):
            yield ProbeResult(
                COVERAGE,
                WARN,
                f"label {label!r} on {', '.join(keys)} has no entry in maps.fields.{code}",
                f"add it to {_sources_toml(expected, 'fields.' + code)}",
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
                self._http.get(f"/api/v4/users/{urllib.parse.quote(user_id, safe='')}")
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
