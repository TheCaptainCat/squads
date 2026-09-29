"""What ``sync`` may do about a managed skill file that lost its frontmatter, decided from the
skill folder alone, and the remedy each outcome carries."""

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

from squads import _sections as sections
from squads._errors import SquadsError
from squads._interactions import bundled_skill_slugs, custom_skill_slugs
from squads._models._item import Item
from squads._models._vocab import prefix_for
from squads._services._duplicate_ids import CarrierLog, file_slug, normalized_id
from squads._workflow import ROSTER_SKILL
from squads._workflow._models import WorkflowSpec

#: What a report line says to do about a managed skill file whose frontmatter is gone or
#: unreadable; `sq sync` rebuilds it from the file name and the skill catalog.
SYNC_RESTORES_SKILL_FRONTMATTER = "run `sq sync` to restore a managed skill's frontmatter"

#: What a report line says about a managed skill file with an unresolved merge conflict.
RESOLVE_CONFLICT_REMEDY = "resolve the merge conflict by hand; `sq sync` does not touch it"

#: What the restamp reports when it declines to write over a duplicate.
RESTAMP_BLOCKED_REMEDY = "remove or rename one of the two files"

_CONFLICT_LINE = re.compile(r"^(<{7}|={7}|>{7})( .*)?$", re.MULTILINE)


def has_conflict_markers(text: str) -> bool:
    """True when *text* carries a line that starts a merge-conflict marker."""
    return _CONFLICT_LINE.search(text) is not None


def stamped_skill_parts(md: Path, spec: WorkflowSpec) -> tuple[int, str] | None:
    """``(number, slug)`` of a ``<PREFIX>-<number>-<slug>.md`` skill file name, else ``None``."""
    prefix = prefix_for(ROSTER_SKILL, spec)
    m = re.fullmatch(rf"{re.escape(prefix)}-(?P<n>\d+)-(?P<slug>.+)", md.stem)
    return (int(m["n"]), m["slug"]) if m else None


def stamped_skill_slug(md: Path, spec: WorkflowSpec) -> str | None:
    """The slug of a ``<PREFIX>-<number>-<slug>.md`` skill file name, else ``None``."""
    parts = stamped_skill_parts(md, spec)
    return parts[1] if parts else None


def managed_skill_slugs(spec: WorkflowSpec) -> frozenset[str]:
    """Every skill slug ``sync`` itself generates (bundled or custom)."""
    return frozenset((*bundled_skill_slugs(), *custom_skill_slugs(spec)))


type VerdictKind = Literal["act", "blocked", "conflict"]


@dataclass(frozen=True)
class Verdict:
    """What the restamp does with one file: ``act`` writes it, ``blocked`` leaves it with a
    reason, ``conflict`` refuses the whole sync."""

    kind: VerdictKind
    reason: str = ""


@dataclass(frozen=True)
class SkillFolder:
    """The skill files by name, with who carries which id and slug, and (once the index has
    been consulted) the skill items it already holds."""

    texts: dict[str, str]
    ids: dict[str, list[str]]
    slugs: dict[str, list[str]]
    pending: dict[str, list[str]]
    managed: frozenset[str]
    known: dict[int, Item] = field(default_factory=dict[int, Item])

    @classmethod
    def build(cls, texts: dict[str, str], spec: WorkflowSpec) -> SkillFolder:
        managed = managed_skill_slugs(spec)
        prefix = prefix_for(ROSTER_SKILL, spec)
        ids: dict[str, list[str]] = {}
        slugs: dict[str, list[str]] = {}
        pending: dict[str, list[str]] = {}
        for name, text in texts.items():
            try:
                fm = sections.split_frontmatter(text)[0]
            except SquadsError:
                fm = {}
            slug = file_slug(Path(name), fm, prefix)
            key = normalized_id(fm.get("id"))
            if key is not None:
                ids.setdefault(key, []).append(name)
                slugs.setdefault(slug, []).append(name)
            elif slug in managed and stamped_skill_parts(Path(name), spec) is not None:
                pending.setdefault(slug, []).append(name)
        return cls(texts, ids, slugs, pending, managed)

    def with_index(self, skills: list[Item]) -> SkillFolder:
        """This folder plus the skill items the index holds, for the blocks that need them."""
        return replace(self, known={it.sequence_id: it for it in skills})

    @property
    def needs_index(self) -> bool:
        """True when some file could be restamped, so the index is worth consulting."""
        return bool(self.pending)

    def verdict(self, name: str, spec: WorkflowSpec) -> Verdict | None:
        """The restamp's decision for *name*, or ``None`` when it has nothing to do (not a
        managed skill file, or it already carries an ``id``)."""
        parts = stamped_skill_parts(Path(name), spec)
        text = self.texts.get(name)
        if parts is None or text is None or parts[1] not in self.managed:
            return None
        try:
            if sections.split_frontmatter(text)[0].get("id"):
                return None
        except SquadsError:
            pass  # unreadable YAML: decided by the conflict check below
        return self._conflict(text) or self._claimed(name, *parts, spec) or Verdict("act")

    @staticmethod
    def _conflict(text: str) -> Verdict | None:
        """A refusal when the file cannot be rebuilt without deciding a merge by hand."""
        try:
            sections.split_frontmatter(text)
            readable = True
        except SquadsError:
            readable = False
        if not readable and sections.frontmatter_block_end(text) is None:
            return Verdict("conflict", "the frontmatter is unreadable and has no block to rebuild")
        if has_conflict_markers(sections.strip_frontmatter(text)):
            return Verdict("conflict", "an unresolved merge conflict reaches past the frontmatter")
        return None

    def _claimed(self, name: str, number: int, slug: str, spec: WorkflowSpec) -> Verdict | None:
        """A block when another file or the index already holds this id or this slug, or when
        several unstamped files claim the slug and nothing decides between them."""
        key = f"{prefix_for(ROSTER_SKILL, spec)}-{number}"
        for other in self.ids.get(normalized_id(key) or key, []):
            if other != name:
                return Verdict("blocked", f"{other} already carries id {key}")
        for other in self.slugs.get(slug, []):
            if other != name:
                return Verdict("blocked", f"{other} already holds skill slug {slug!r}")
        holder = next((n for n, it in self.known.items() if it.extra.get("slug") == slug), None)
        if holder is not None:
            if holder != number:
                return Verdict("blocked", f"the index holds skill slug {slug!r} at number {holder}")
            return None
        rivals = [n for n in self.pending.get(slug, []) if n != name]
        if rivals:
            return Verdict("blocked", f"{rivals[0]} also claims skill slug {slug!r}")
        return None


@dataclass
class SkillScan:
    """What one scan has learned about the skill folder. Made by the call that scans and passed
    down it; never kept on the service."""

    texts: dict[Path, str] | None = None
    items: list[Item] | None = None
    state: SkillFolder | None = None


@dataclass
class ScanContext:
    """Everything one ``check``, ``repair`` or restamp pass shares between its steps."""

    carriers: CarrierLog = field(default_factory=CarrierLog)
    skills: SkillScan = field(default_factory=SkillScan)


def remedy_text(verdict: Verdict | None) -> str:
    """The remedy a `check`/`repair` line gives for a managed skill file with that verdict."""
    if verdict is None or verdict.kind == "act":
        return SYNC_RESTORES_SKILL_FRONTMATTER
    if verdict.kind == "blocked":
        return f"{verdict.reason}; {RESTAMP_BLOCKED_REMEDY}"
    return f"{verdict.reason}; {RESOLVE_CONFLICT_REMEDY}"
