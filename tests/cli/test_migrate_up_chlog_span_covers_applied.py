"""``sq migrate up``'s "manual steps remain" line must always name a span that
``sq migrate chlog`` itself resolves to every applied migration's manual text.

Table-driven over the shapes that could break the span: the squad's ``squads_version``
stamp already caught up to the running package before the schema did (the bug's own
reproduction), a ``squads_version`` nowhere near ``__version__``, a multi-migration chain
where only some entries carry manual text, and the edge where the very first migration in
the registry is the one applied (no preceding entry to anchor the lower bound on).

Driven entirely through the CLI (``invoke``): read the span off ``migrate up``'s own
output, feed it straight back into ``migrate chlog``, and check every applied migration
with manual text is reported — the same round trip an operator following the tool's own
instruction performs.
"""

import re

import pytest

from squads import _aio
from squads._migrations._registry import MIGRATIONS, Migration

pytestmark = pytest.mark.anyio

_SPAN_RE = re.compile(r"`sq migrate chlog ([^`]+)`")


async def _downgrade_schema(project, schema: str) -> None:
    cfg_text = await _aio.read_text(project.config_path)
    cfg_text = cfg_text.replace(
        f'schema_version = "{project.config.schema_version}"', f'schema_version = "{schema}"'
    )
    await _aio.write_text(project.config_path, cfg_text)


async def _set_squads_version(project, version: str) -> None:
    cfg_text = await _aio.read_text(project.config_path)
    cfg_text = cfg_text.replace(
        f'squads_version = "{project.config.squads_version}"', f'squads_version = "{version}"'
    )
    await _aio.write_text(project.config_path, cfg_text)


def _applied_from(from_schema: str) -> list[Migration]:
    """The same filter ``run_pending_migrations`` applies, computed test-side to know what
    ``migrate up`` should have applied without re-deriving the fix under test."""
    from squads._models._schema import schema_tuple

    return [m for m in MIGRATIONS if schema_tuple(m.to_schema) > schema_tuple(from_schema)]


@pytest.mark.parametrize(
    "from_schema,squads_version",
    [
        # The bug's own repro: squads_version already at the running package's version
        # while the schema is one migration behind (project's fixture default).
        pytest.param("0.14", None, id="squads_version-already-caught-up"),
        # squads_version nowhere near __version__ — the span must not depend on it either
        # way; this is what proves the fix reads `applied`, not the sync stamp.
        pytest.param("0.14", "0.1.0", id="squads_version-older"),
        # A multi-migration chain where only some applied entries carry manual text
        # (0.11.0 is a schema-stamp-only gate with no manual steps).
        pytest.param("0.10", None, id="multi-migration-chain-partial-manual"),
        # The first migration in the whole registry is the one applied — no preceding
        # registry entry to anchor the span's lower bound on.
        pytest.param("0.1", None, id="first-in-registry"),
    ],
)
async def test_migrate_up_span_reports_every_applied_manual_migration(
    project, invoke, from_schema, squads_version
):
    await _downgrade_schema(project, from_schema)
    if squads_version is not None:
        await _set_squads_version(project, squads_version)

    up = await invoke(["migrate", "up"])
    assert up.exit_code == 0, up.output

    expected_manual = [m for m in _applied_from(from_schema) if m.manual]
    assert expected_manual, "test setup must exercise at least one manual migration"

    match = _SPAN_RE.search(up.output)
    assert match, f"no chlog span printed: {up.output}"
    span = match.group(1)

    chlog = await invoke(["migrate", "chlog", span])
    assert chlog.exit_code == 0, chlog.output
    assert "no manual steps" not in chlog.output, (
        f"span {span!r} reported by `migrate up` contains none: {chlog.output}"
    )
    for m in expected_manual:
        # Rich renders the `##` markdown heading as styled text rather than literal `##` —
        # match on the text content only.
        heading = f"v{m.version} — manual steps (schema v{m.from_schema}→v{m.to_schema})"
        assert heading in chlog.output, f"{heading!r} missing from chlog output for {span!r}"
