"""``squads._cli._workflow_cmd._playbook_json_payload`` — the ``playbook`` source's ``--json``
shape, the one source kind with no pre-existing serializer elsewhere in the codebase to match.
Two properties, tested directly against the payload builder and the resolver (the same
``PlaybookSource`` shape a real ``sq workflow view --json`` call produces — see
``tests/cli/test_workflow_views_cli.py`` and
``tests/service/test_role_playbook_self_views_end_to_end.py`` for that path end to end):

- every lane the bundled playbook declares round-trips through the builder without a crash;
- a genuinely unlaned type's resolved ``PlaybookSource`` (``lane=None``) serializes as the
  shape's own well-formed empty case, not a raise — reached here directly against the resolver,
  the same setup ``tests/unit/test_playbook_source_resolver.py`` uses.
"""

from pathlib import Path

import pytest

from _helpers import create_item
from squads import __version__
from squads._cli._workflow_cmd import _playbook_json_payload
from squads._interactions import get_playbook_spec
from squads._services._service import Service, resolve_playbook
from squads._views import PlaybookSource, _resolve_playbook_source
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import ViewSource, ViewSpec

pytestmark = pytest.mark.anyio


def test_every_bundled_lane_round_trips_without_a_crash() -> None:
    playbook = get_playbook_spec()
    for item_type, lane in playbook.types.items():
        source = PlaybookSource(item_type=item_type, lane=lane, roster=[], playbook=playbook)
        payload = _playbook_json_payload(source)

        assert payload["type"] == item_type
        lane_payload = payload["lane"]
        assert isinstance(lane_payload, dict)
        assert set(lane_payload) == {"overview", "lifecycle", "commands", "roles"}
        for role_row in lane_payload["roles"]:
            assert set(role_row) == {"slug", "enter", "do", "handoff", "watch", "authors"}


def test_no_kind_carries_the_retired_projection_envelope_keys() -> None:
    playbook = get_playbook_spec()
    item_type, lane = next(iter(playbook.types.items()))
    payload = _playbook_json_payload(
        PlaybookSource(item_type=item_type, lane=lane, roster=[], playbook=playbook)
    )
    lane_payload = payload["lane"]
    assert isinstance(lane_payload, dict)
    for key in ("fields", "group_by", "groups"):
        assert key not in payload
        assert key not in lane_payload


def _write_renamed_guide_override(squad_dir: Path) -> None:
    """Shadows the bundled ``guide`` type with an equally-shaped custom type ``doc`` that
    carries no playbook entry — mirrors the identical fixture in
    ``tests/unit/test_playbook_source_resolver.py`` (coverage is required only for bundled type
    names still active in the spec, so ``doc`` is declared and real but genuinely unlaned)."""
    bundled = load_workflow_spec()
    kept = sorted([t for t in bundled.items if t != "guide"] + ["doc"])
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        f"[selected]\nitems = {kept!r}\n\n"
        "[items.doc]\n"
        'prefix = "$(items.guide.prefix)"\n'
        'folder = "$(items.guide.folder)"\n'
        'lifecycle = "$(items.guide.lifecycle)"\n',
        encoding="utf-8",
    )


async def test_a_declared_but_unlaned_types_json_is_the_no_lane_case_not_a_raise(
    project, svc
) -> None:
    squad_dir = svc.paths.squad_dir
    _write_renamed_guide_override(squad_dir)
    merged_spec = load_workflow_spec(squad_dir=squad_dir)
    merged_playbook = resolve_playbook(merged_spec, squad_dir)
    project_svc = Service(svc.paths, spec=merged_spec, playbook=merged_playbook)
    doc_item = (await create_item(project_svc, "doc", "D")).item

    view = ViewSpec(source=ViewSource(kind="playbook"))
    resolved = _resolve_playbook_source(view, doc_item, merged_playbook, lambda: [], merged_spec)
    assert resolved.lane is None  # the resolver's own well-formed empty case

    payload = _playbook_json_payload(resolved)

    assert payload == {"type": "doc", "lane": None, "roster": []}
