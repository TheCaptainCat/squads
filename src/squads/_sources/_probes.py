"""The probe framework behind ``sq source check``: results a connector yields in three families,
and the runner that orders them. It names no tracker."""

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Literal

from squads._sources._filter import Expression
from squads._sources._spec import SourceMaps

type Family = Literal["access", "vocabulary", "coverage"]
type Verdict = Literal["pass", "fail", "warn"]

ACCESS: Family = "access"
VOCABULARY: Family = "vocabulary"
COVERAGE: Family = "coverage"
#: The families in the order they run.
FAMILIES: tuple[Family, ...] = (ACCESS, VOCABULARY, COVERAGE)

PASS: Verdict = "pass"
FAIL: Verdict = "fail"
WARN: Verdict = "warn"


@dataclass(frozen=True)
class ProbeResult:
    """What one probe found: a pass, a blocking failure or a warning, and for the last two the
    fix, which names what to change on the tracker, in ``sources.toml`` or in the credential
    store."""

    family: Family
    verdict: Verdict
    text: str
    fix: str = ""

    @property
    def blocking(self) -> bool:
        """Whether this result stops a command that needs the tracker."""
        return self.verdict == FAIL

    def message(self) -> str:
        """The result as a command prints it when it stops: the finding, then its fix."""
        return f"{self.text}\n  fix: {self.fix}" if self.fix else self.text


@dataclass(frozen=True)
class Expected:
    """What the squad expects of one source, for the probes to check the tracker against."""

    source: str
    maps: SourceMaps
    #: Tracker side to the expression that side must satisfy; empty selects every issue.
    filter: Mapping[str, Expression]
    #: ``(operator slug, tracker user ID)`` for each identity an operator holds on this source.
    identities: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    #: ``(tracker user ID, handle, where)`` for each comment author already imported, ``where``
    #: naming the item that holds the comment.
    commenters: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)


def missing_credential(source: str) -> ProbeResult:
    """The access failure of a source whose credential is not stored."""
    return ProbeResult(
        ACCESS,
        FAIL,
        f"source {source!r} has no stored credential",
        f"run `sq source credential set {source}`",
    )


def run_probes(
    probes: Callable[[Family], Iterator[ProbeResult]], families: tuple[Family, ...] = FAMILIES
) -> list[ProbeResult]:
    """The results of *families* in order, ending at the first blocking access failure."""
    results: list[ProbeResult] = []
    for family in families:
        for result in probes(family):
            results.append(result)
            if family == ACCESS and result.blocking:
                return results
    return results
