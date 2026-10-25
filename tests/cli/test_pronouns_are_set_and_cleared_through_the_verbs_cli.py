"""Pronouns are set at creation (``role activate``, ``dev add``, ``operator add``) and set,
changed or cleared afterwards (role and operator ``update``). One table crosses each verb with
the value shapes: the exit code, the message, what the frontmatter holds afterwards, and that a
refusal leaves the file and the roster untouched."""

from pathlib import Path
from typing import Any

import pytest

from _helpers import catalog_of
from squads import __version__
from squads._errors import SquadsError
from squads._models._attributes import AttributeKey
from squads._pronouns import pronouns_problem
from squads._rendering._engine import invalidate_squad_dir
from squads._roles._loader import load_role_catalog
from squads._roles._resolver import resolve_role
from squads._sections import split_frontmatter
from squads._services._service import Service

pytestmark = pytest.mark.anyio

# (id, raw argument, stored value when accepted)
SHAPES: list[tuple[str, str, str]] = [
    ("slash-pair", "they/them", "they/them"),
    ("one-character", "x", "x"),
    ("forty-characters", "a" * 40, "a" * 40),
    ("forty-one-characters", "a" * 41, ""),
    ("surrounding-whitespace", "  they/them\t", "they/them"),
    ("empty", "", ""),
    ("whitespace-only", "   ", ""),
    ("embedded-newline", "they/\nthem", ""),
    ("embedded-tab", "they/\tthem", ""),
    ("other-control-character", "they\x07them", ""),
    ("bidi-override", f"they{chr(0x202E)}them", ""),
    ("zero-width-space", f"they{chr(0x200B)}them", ""),
    ("forty-one-decomposed-accents", "e\u0301" * 41, ""),
    ("forty-decomposed-accents", "e\u0301" * 40, "e\u0301" * 40),
    ("marker-tag", "<!-- sq:body -->", ""),
    ("square-brackets", "[x]", "[x]"),
    ("non-ascii", "elle/iel", "elle/iel"),
]
_IDS = [s[0] for s in SHAPES]


def _blank(raw: str) -> bool:
    return not raw.strip()


def _accepted(raw: str) -> bool:
    return _blank(raw) or pronouns_problem(raw) is None


def _stored(svc: Service, item: Any) -> Any:
    data, _ = split_frontmatter(svc.paths.abspath(item.path).read_text(encoding="utf-8"))
    return data.get(AttributeKey.PRONOUNS)


# (verb id, creation args before --pronouns, slug of the entry created)
CREATE_VERBS: list[tuple[str, list[str], str]] = [
    ("role-activate", ["role", "activate", "architect"], "architect"),
    ("dev-add", ["dev", "add", "--tech", "python"], "python-dev"),
    ("operator-add", ["operator", "add", "Alex Rivera"], "op-alex"),
]


@pytest.mark.parametrize(("verb", "args", "slug"), CREATE_VERBS, ids=[v[0] for v in CREATE_VERBS])
@pytest.mark.parametrize(("shape", "raw", "expected"), SHAPES, ids=_IDS)
async def test_a_creation_verb_stores_the_trimmed_value_or_refuses_and_creates_nothing(
    svc: Service,
    invoke: Any,
    verb: str,
    args: list[str],
    slug: str,
    shape: str,
    raw: str,
    expected: str,
) -> None:
    result = await invoke([*args, "--pronouns", raw])

    kind = "operator" if slug.startswith("op-") else "role"
    created = await svc.roster_item(kind, slug)
    if _accepted(raw):
        assert result.exit_code == 0, result.output
        assert created is not None
        assert _stored(svc, created) == (expected or None)
    else:
        assert result.exit_code == 1
        assert "error: pronouns " in result.output
        assert created is None


UPDATE_VERBS: list[tuple[str, str]] = [("role", "architect"), ("operator", "op-alex")]


async def _entry_with_old_pronouns(svc: Service, invoke: Any, kind: str) -> Any:
    if kind == "role":
        item = await svc.activate_role("architect", pronouns="old/old")
    else:
        item = await svc.add_operator("Alex Rivera", pronouns="old/old")
    assert _stored(svc, item) == "old/old"
    return item


@pytest.mark.parametrize(("kind", "slug"), UPDATE_VERBS, ids=[v[0] for v in UPDATE_VERBS])
@pytest.mark.parametrize(("shape", "raw", "expected"), SHAPES, ids=_IDS)
async def test_update_replaces_clears_or_refuses_and_a_refusal_leaves_the_file_untouched(
    svc: Service, invoke: Any, kind: str, slug: str, shape: str, raw: str, expected: str
) -> None:
    item = await _entry_with_old_pronouns(svc, invoke, kind)
    path = svc.paths.abspath(item.path)
    before = path.read_bytes()

    result = await invoke([kind, slug, "update", "--pronouns", raw])

    if _blank(raw):
        assert result.exit_code == 0, result.output
        assert _stored(svc, item) is None
        assert AttributeKey.PRONOUNS not in (await svc.get(item.id)).attributes
    elif _accepted(raw):
        assert result.exit_code == 0, result.output
        assert _stored(svc, item) == expected
    else:
        assert result.exit_code == 1
        assert "error: pronouns " in result.output
        assert path.read_bytes() == before
        assert _stored(svc, item) == "old/old"


@pytest.mark.parametrize(("kind", "slug"), UPDATE_VERBS, ids=[v[0] for v in UPDATE_VERBS])
async def test_update_with_no_field_still_says_what_it_takes(
    svc: Service, invoke: Any, kind: str, slug: str
) -> None:
    await _entry_with_old_pronouns(svc, invoke, kind)

    result = await invoke([kind, slug, "update"])

    assert result.exit_code == 1
    assert "--pronouns" in result.output


async def test_pronouns_are_settable_on_a_bundled_role_while_its_content_stays_refused(
    svc: Service, invoke: Any
) -> None:
    await svc.activate_role("architect")

    allowed = await invoke(["role", "architect", "update", "--pronouns", "she/her"])
    role = await svc.roster_item("role", "architect")
    assert role is not None
    with pytest.raises(SquadsError, match="An update is refused"):
        await svc.update(role.id, description="Rewritten mission")

    assert allowed.exit_code == 0, allowed.output
    assert _stored(svc, role) == "she/her"
    assert (await svc.get(role.id)).description != "Rewritten mission"


async def test_activating_a_live_role_with_pronouns_is_refused_and_names_the_verb(
    svc: Service, invoke: Any
) -> None:
    await svc.activate_role("architect")

    result = await invoke(["role", "activate", "architect", "--pronouns", "she/her"])
    plain = await invoke(["role", "activate", "architect"])

    assert result.exit_code == 1
    assert "sq role architect update --pronouns" in result.output
    assert plain.exit_code == 0


@pytest.mark.parametrize(("kind", "slug"), UPDATE_VERBS, ids=[v[0] for v in UPDATE_VERBS])
async def test_a_sync_leaves_a_stored_value_whatever_its_shape(
    svc: Service, invoke: Any, kind: str, slug: str
) -> None:
    item = await _entry_with_old_pronouns(svc, invoke, kind)
    path = svc.paths.abspath(item.path)
    valid = path.read_bytes()
    text = path.read_text(encoding="utf-8")
    broken = text.replace("old/old", "a" * 41)
    path.write_text(broken, encoding="utf-8", newline="")
    await svc.repair()

    synced_broken = await invoke(["sync"])
    after_broken = path.read_bytes()
    path.write_bytes(valid)
    await svc.repair()
    synced_valid = await invoke(["sync"])

    assert synced_broken.exit_code == 0, synced_broken.output
    assert synced_valid.exit_code == 0, synced_valid.output
    assert after_broken == broken.encode()
    assert _stored(svc, item) == "old/old"


def _override(project: Any, name: str, body: str) -> Path:
    target = project.squad_dir / ".overrides" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"# squads:override-base:{__version__}\n{body}", encoding="utf-8")
    invalidate_squad_dir(project.squad_dir)
    return target


@pytest.mark.parametrize(
    ("document", "body"),
    [
        ("roles.toml", '[[roles]]\nslug = "architect"\npronouns = "she/her"\n'),
        ("roles/architect.toml", 'pronouns = "she/her"\n'),
        (
            "roles.toml",
            '[[roles]]\nslug = "chef"\nfull_name = "C"\ntitle = "t"\ndescription = "d"\n'
            'mission = "m"\npronouns = "she/her"\n',
        ),
    ],
    ids=["bundled-entry-in-catalog", "per-slug-file", "new-entry-in-catalog"],
)
async def test_a_role_document_with_a_pronouns_key_is_refused_and_names_the_verb(
    project: Any, document: str, body: str
) -> None:
    _override(project, document, body)

    with pytest.raises(SquadsError, match=r"update --pronouns"):
        if document.startswith("roles/"):
            resolve_role("architect", project.squad_dir, catalog=catalog_of(project.squad_dir))
        else:
            load_role_catalog(project.squad_dir)


async def test_a_role_catalog_without_a_pronouns_key_loads_as_before(project: Any) -> None:
    _override(project, "roles.toml", '[[roles]]\nslug = "architect"\ntitle = "Chief"\n')

    assert load_role_catalog(project.squad_dir).roles


@pytest.mark.parametrize(
    ("data", "verb"),
    [
        ({"slug": "chef", "pronouns": "x"}, "sq role chef update --pronouns"),
        ({"pronouns": "x"}, "sq role <addr> update --pronouns"),
    ],
    ids=["with-slug", "without-slug"],
)
def test_the_refusal_always_names_a_runnable_verb(data: dict[str, str], verb: str) -> None:
    from squads._roles._loader import refuse_pronouns_key

    with pytest.raises(SquadsError, match=verb.replace("<", r"\<")):
        refuse_pronouns_key(data, "where")
