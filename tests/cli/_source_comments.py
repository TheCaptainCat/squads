"""Arrangements the comments cases of several `tests/cli` modules share."""

from tests import _tracker_harness as harness

SECRET = "glpat-not-a-real-token"


STRANGER = {"author_id": "999", "author_handle": "visitor", "author_name": "Vera Visitor"}


HEAD = '[sources.platform]\nconnector = "gitlab"\nproject = "platform/api"\n'


def types(profile) -> str:
    return f'\n[sources.platform.maps.types.type]\nissue = "{profile.ref}"\n'


def declare(project, profile, base_url: str, extra: str = "") -> None:
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'{HEAD}base_url = "{base_url}"\n{extra}{types(profile)}', encoding="utf-8")


def note(number: int, text: str, user: dict[str, str]) -> dict[str, object]:
    return {
        "id": 400 + number,
        "body": text,
        "system": False,
        "created_at": "2026-11-02T09:14:00Z",
        "updated_at": "2026-11-02T09:20:31Z",
        "author": {
            "id": int(user["author_id"]),
            "username": user["author_handle"],
            "name": user["author_name"],
        },
    }


async def arrange(
    invoke, project, profile, tracker: harness.Tracker, *comments: tuple[str, dict[str, str]]
) -> None:
    """Pull `platform/api#12` into the third item from *tracker*, with one note for each of
    *comments* (text and author)."""
    assert (await invoke(["operator", "add", "Alice Tester"])).exit_code == 0
    assert (
        await invoke(["operator", "op-alice", "update", "--identities", "platform=4567"])
    ).exit_code == 0
    route = next(r for r in tracker.routes if r["path"].endswith("/issues/12/notes"))
    route["body"] = [note(n, text, user) for n, (text, user) in enumerate(comments, 1)]
    declare(project, profile, tracker.base_url)
    stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
    assert stored.exit_code == 0, stored.output
    pulled = await invoke(["source", "pull", "platform"])
    assert pulled.exit_code == 0, pulled.output


async def host(invoke, project, profile, *comments: tuple[str, dict[str, str]]) -> str:
    """The address of the tracker that served the third item, pulled with *comments*."""
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await arrange(invoke, project, profile, tracker, *comments)
        return tracker.base_url
