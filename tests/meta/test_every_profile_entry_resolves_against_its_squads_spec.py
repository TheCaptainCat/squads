"""Repo gate: each name in a squad's test profile resolves against that squad's spec, so no CLI case
skips for want of a host and none names a thing the squad does not declare."""

import shutil
from pathlib import Path

import pytest

from squads._models._vocab import label_for
from squads._workflow import bundled_spec
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import WorkflowSpec
from tests._override_populated import OVERRIDE as OVERRIDE_DOCUMENTS
from tests._profile import BUNDLED, OVERRIDE, Profile


def _spec_of(profile: Profile, tmp_path: Path) -> WorkflowSpec:
    if profile.squad == BUNDLED.squad:
        return bundled_spec()
    overrides = tmp_path / "squads" / ".overrides"
    overrides.mkdir(parents=True)
    for document in OVERRIDE_DOCUMENTS.glob("*.toml"):
        shutil.copy(document, overrides / document.name)
        text = (overrides / document.name).read_text(encoding="utf-8")
        (overrides / document.name).write_text("# squads:override-base:0.19.0\n" + text)
    return load_workflow_spec(tmp_path / "squads")


def _problems(profile: Profile, spec: WorkflowSpec) -> list[str]:
    p = profile
    checks: list[tuple[str, bool]] = [
        ("host prefix", spec.items[p.host].prefix == p.host_prefix),
        ("host alias", spec.alias_to_type.get(p.host_alias) == p.host),
        ("host hosts the target kind", spec.item_subentity_kind(p.host) == p.target_kind),
        ("ref prefix", spec.items[p.ref].prefix == p.ref_prefix),
        ("ref folder", spec.items[p.ref].folder == p.ref_folder),
        ("ref label", label_for(p.ref, "singular", spec).title() == p.ref_label),
        ("ref hosts the kind", spec.item_subentity_kind(p.ref) == p.kind),
        ("kind maps to the target kind", spec.mapping_target_kind(p.kind) == p.target_kind),
        ("kind prefix", spec.subentity_kinds[p.kind].local_prefix == p.kind_prefix),
        ("kind plural", spec.subentity_kinds[p.kind].plural == p.kind_plural),
        ("target prefix", spec.subentity_kinds[p.target_kind].local_prefix == p.target_prefix),
        ("target plural", spec.subentity_kinds[p.target_kind].plural == p.target_plural),
        ("third prefix", spec.items[p.third].prefix == p.third_prefix),
        ("third folder", spec.items[p.third].folder == p.third_folder),
        ("third hosts its kind", spec.item_subentity_kind(p.third) == p.third_kind),
        (
            "third kind prefix",
            spec.subentity_kinds[p.third_kind].local_prefix == p.third_kind_prefix,
        ),
        ("third kind plural", spec.subentity_kinds[p.third_kind].plural == p.third_kind_plural),
        ("initial status", spec.initial_status(p.ref) == p.initial),
        ("moved status", spec.can_transition(p.ref, p.initial, p.moved)),
        ("kind initial status", spec.subentity_initial(p.kind) == p.kind_initial),
        ("kind moved status", spec.subentity_can_transition(p.kind, p.kind_initial, p.kind_moved)),
        ("ref kind one", p.ref_kind_one in spec.ref_kinds),
        ("ref kind one label", spec.ref_kinds[p.ref_kind_one].label == p.ref_kind_one_label),
        ("ref kind two", p.ref_kind_two in spec.ref_kinds),
        ("ref kind two label", spec.ref_kinds[p.ref_kind_two].label == p.ref_kind_two_label),
    ]
    badge = next((f for f in spec.fields_for(p.ref) if f.code == p.badge), None)
    checks.append(("ref badge field", badge is not None))
    if badge is not None:
        codes = [b.code for b in spec.collections[badge.collection].badges]
        checks += [
            ("badge codes text", ", ".join(codes) == p.badge_codes),
            ("badge flag", p.badge_flag == "--" + p.badge.replace("_", "-")),
            ("no-badge flag", p.no_badge_flag == "--no-" + p.badge.replace("_", "-")),
            ("badge value", p.badge_value in codes),
            ("badge other value", p.badge_other_value in codes),
        ]
    third_field = next((f for f in spec.fields_for(p.third_kind) if f.code == p.third_field), None)
    checks.append(("third kind field", third_field is not None))
    if third_field is not None:
        codes = {b.code.lower() for b in spec.collections[third_field.collection].badges}
        checks += [
            ("third value", p.third_value.lower() in codes),
            ("third other value", p.third_other_value.lower() in codes),
        ]
    return [name for name, ok in checks if not ok]


@pytest.mark.parametrize("profile", [BUNDLED, OVERRIDE], ids=lambda p: p.squad)
def test_every_profile_entry_resolves_against_its_squads_spec(
    profile: Profile, tmp_path: Path
) -> None:
    spec = _spec_of(profile, tmp_path)

    assert _problems(profile, spec) == []
