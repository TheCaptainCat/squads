"""``docs/stability.md`` and ``docs/backends.md`` both promise ``AgentBackend`` has *exactly
seven* abstract methods and that the set "does not grow" -- a third-party backend written from
either document's own seven-method list must instantiate.

``managed_entry_paths`` was briefly an eighth ``@abstractmethod`` (added alongside the per-entry
pointer reporting in ``sq check``/``sq sync``), which made a subclass implementing exactly the
documented seven fail with ``TypeError: ... without an implementation for abstract method
'managed_entry_paths'``. The fix keeps the promise literally true: ``managed_entry_paths`` has a
concrete default (an empty list -- "no per-entry pointers declared"), so it opts a backend *out*
of the per-entry reporting rather than being required to opt in.

This pins the contract rather than trusting it: a future change that turns any of the seven back
into (or adds an eighth) abstract method reddens this file, not just the two documentation files
a code change never touches.
"""

from squads._backends._agents_md._backend import AgentsMdBackend
from squads._backends._base import AgentBackend, Artifact, BackendContext
from squads._backends._claude_code._backend import ClaudeCodeBackend

#: The exact seven method names both ``docs/stability.md`` and ``docs/backends.md`` document as
#: the whole ABC -- transcribed from those documents, not derived from the class, so a source
#: change that quietly grows the *documented* set would still be caught by a stale list here.
_DOCUMENTED_SEVEN = frozenset(
    {
        "ensure_scaffold",
        "write_managed",
        "generate_role_entry",
        "generate_skill_entry",
        "remove_artifacts",
        "candidate_orphans",
        "managed_paths",
    }
)


class _SevenMethodBackend(AgentBackend):
    """A minimal backend implementing exactly the seven documented methods -- nothing more."""

    name = "seven-method"

    async def ensure_scaffold(self, ctx: BackendContext) -> list[Artifact]:
        return []

    async def write_managed(self, ctx, roster, operators) -> list[Artifact]:
        return []

    async def generate_role_entry(self, ctx, item, role) -> Artifact:
        return Artifact(path="stub", kind="agent", backend=self.name)

    async def generate_skill_entry(self, ctx, item) -> Artifact:
        return Artifact(path="stub", kind="skill", backend=self.name)

    async def remove_artifacts(self, ctx, item) -> None:
        return None

    async def candidate_orphans(self, ctx, roster, skill_slugs) -> list[str]:
        return []

    def managed_paths(self, ctx: BackendContext) -> list[str]:
        return []


def test_the_documented_seven_methods_are_exactly_the_abcs_abstract_set():
    assert AgentBackend.__abstractmethods__ == _DOCUMENTED_SEVEN


def test_managed_entry_paths_is_not_abstract():
    assert "managed_entry_paths" not in AgentBackend.__abstractmethods__


def test_a_subclass_implementing_only_the_documented_seven_instantiates():
    """The pinned regression: this used to raise ``TypeError`` for the missing
    ``managed_entry_paths``."""
    backend = _SevenMethodBackend()
    assert isinstance(backend, AgentBackend)


def test_the_base_defaults_managed_entry_paths_to_an_empty_list(tmp_path):
    from squads._models._config import SquadsConfig
    from squads._paths import SquadPaths

    backend = _SevenMethodBackend()
    config = SquadsConfig(squad_dir="squads", active_backends=["claude_code"])
    ctx = BackendContext(
        paths=SquadPaths(root=tmp_path, squad_dir=tmp_path / "squads", config=config)
    )
    assert backend.managed_entry_paths(ctx) == []


def test_claude_code_still_overrides_managed_entry_paths():
    """Claude Code keeps declaring its own per-entry pointers rather than falling through to
    the new default -- it still has a real per-role/per-skill file for `sq check`/`sq sync` to
    reconcile against."""
    assert "managed_entry_paths" in vars(ClaudeCodeBackend)


def test_agents_md_falls_through_to_the_default_no_per_entry_pointers():
    """agents_md dropped its override once it stopped staging a per-role/per-skill file (see
    ``AgentsMdBackend``'s module docstring) -- it now falls through to the ABC default (an
    empty list), the same as a third-party backend that never opted in."""
    assert "managed_entry_paths" not in vars(AgentsMdBackend)
