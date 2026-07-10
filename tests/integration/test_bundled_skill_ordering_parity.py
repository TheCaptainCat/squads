"""Bundled skills end up in the same lexical order whether seeded fresh at `sq init` or
stamped later by the 0.4->0.5 migration on a pre-seeding squad — the ordering primitive
(bundled_skill_slugs) is the single source both paths must agree with.

Deferred from the migration chunk: this is an agent-artifact ordering fact, not a
migration-correctness one (the migration mechanics themselves are covered at
tests/integration/test_skill_migration.py).
"""

import pytest

from squads._interactions import bundled_skill_slugs
from squads._migrations._v0_4_to_v0_5 import migrate as migrate_v0_4_to_v0_5
from squads._services import _service as service

pytestmark = pytest.mark.anyio


async def test_init_seeded_order_and_post_migration_order_both_match_the_canonical_order(
    tmp_path, monkeypatch, frozen_time
) -> None:
    expected_slugs = bundled_skill_slugs()

    # Squad A: seeded via a normal sq init.
    dir_a = tmp_path / "a"
    dir_a.mkdir()
    monkeypatch.chdir(dir_a)
    result_a = await service.init(root=dir_a, roles_spec="minimal")
    svc_a = service.Service(result_a.paths)
    init_skills = sorted(await svc_a.list_items(item_type="skill"), key=lambda s: s.sequence_id)
    init_bundled = [sk.slug for sk in init_skills if sk.slug in set(expected_slugs)]

    # Squad B: init without seeding, then migrated.
    dir_b = tmp_path / "b"
    dir_b.mkdir()
    monkeypatch.chdir(dir_b)
    result_b = await service.init(root=dir_b, roles_spec="minimal", _skip_skill_seed=True)
    await migrate_v0_4_to_v0_5(result_b.paths)
    svc_b = service.Service(result_b.paths)
    await svc_b.repair()
    migrated_skills = sorted(await svc_b.list_items(item_type="skill"), key=lambda s: s.sequence_id)
    migrated_bundled = [sk.slug for sk in migrated_skills if sk.slug in set(expected_slugs)]

    # Ordinal position must match on both paths — identical numeric IDs are not required.
    assert init_bundled == expected_slugs
    assert migrated_bundled == expected_slugs
