"""The bundled interaction playbook is a tested artifact: it fails closed on an unknown
key (extra="forbid" actually fires, not silently dropped), every declared field is covered
by the pinned golden, the loaded shape is byte-identical to it, and the PLAYBOOK shim
(dataclass form consumed by the renderer) is a lossless conversion of the spec. Packaging
(playbook.toml ships in the wheel) lives in tests/meta/test_bundled_toml_packaging.py.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from squads._interactions import PLAYBOOK, get_playbook_spec, spec_to_item_playbook
from squads._interactions._loader import _build_spec  # pyright: ignore[reportPrivateUsage]
from squads._interactions._models import ItemPlaybookSpec, PlaybookSpec, RoleGuideSpec
from squads._roles._catalog import get_catalog
from squads._workflow import bundled_spec

GOLDEN_PATH = Path(__file__).parents[1] / "goldens" / "playbook_spec.json"


def _golden() -> dict[str, object]:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


class TestFailsClosedOnUnknownKeys:
    def test_unknown_key_in_a_type_entry_raises(self) -> None:
        raw: dict[str, Any] = {
            "types": {
                "task": {
                    "overview": "A unit of work.",
                    "lifecycle": "Draft -> Done",
                    "commandz": ["typo"],  # unknown key
                    "commands": [],
                    "roles": [],
                }
            }
        }
        with pytest.raises(Exception, match=r"(?i)(extra|commandz|invalid|unknown|forbidden)"):
            _build_spec(raw, get_catalog(), bundled_spec())

    def test_unknown_key_in_a_role_guide_entry_raises(self) -> None:
        raw: dict[str, Any] = {
            "types": {
                "task": {
                    "overview": "A unit of work.",
                    "lifecycle": "Draft -> Done",
                    "commands": [],
                    "roles": [
                        {
                            "slug": "tech-lead",
                            "entr": ["typo"],  # unknown key
                            "enter": [],
                            "do": [],
                            "handoff": [],
                            "watch": [],
                        }
                    ],
                }
            }
        }
        with pytest.raises(Exception, match=r"(?i)(extra|entr|invalid|unknown|forbidden)"):
            _build_spec(raw, get_catalog(), bundled_spec())


class TestSpecIsAPinnedArtifact:
    def test_loads_without_error(self) -> None:
        spec = get_playbook_spec()
        assert isinstance(spec, PlaybookSpec)
        assert len(spec.types) == 7

    def test_golden_covers_every_declared_itemplaybookspec_field(self) -> None:
        golden = _golden()
        snapshot_keys = set(golden["types"]["task"].keys())  # type: ignore[index]
        assert snapshot_keys == set(ItemPlaybookSpec.model_fields)

    def test_golden_covers_every_declared_roleguidespec_field(self) -> None:
        golden = _golden()
        first_role: dict[str, object] = golden["types"]["task"]["roles"][0]  # type: ignore[index]
        assert set(first_role.keys()) == set(RoleGuideSpec.model_fields)

    def test_loaded_spec_is_byte_identical_to_the_golden(self) -> None:
        assert get_playbook_spec().model_dump(mode="json") == _golden()


class TestShimIsALosslessConversion:
    def test_playbook_shim_covers_the_same_types_as_the_spec(self) -> None:
        assert set(PLAYBOOK.keys()) == set(get_playbook_spec().types.keys())

    def test_spec_to_item_playbook_drops_no_field(self) -> None:
        for item_type, spec_entry in get_playbook_spec().types.items():
            shim = PLAYBOOK[item_type]
            converted = spec_to_item_playbook(spec_entry)
            assert shim.overview == converted.overview
            assert shim.lifecycle == converted.lifecycle
            assert shim.commands == converted.commands
            assert len(shim.roles) == len(converted.roles)
            for sr, cr in zip(shim.roles, converted.roles, strict=True):
                assert (sr.slug, sr.enter, sr.do, sr.handoff, sr.watch) == (
                    cr.slug,
                    cr.enter,
                    cr.do,
                    cr.handoff,
                    cr.watch,
                )
