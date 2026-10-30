"""`POST /v1/commands`: a command line run in the daemon's process, answered with ordered output
chunks and an exit code, or with a prompt it stopped at."""

import base64
import json
from dataclasses import replace
from pathlib import Path

import pytest
import typer
import typer.main
from typer._click import Command
from typer.testing import CliRunner

from squads._api import _ops as ops
from squads._api._dto._check import SyncRequest
from squads._cli import _calls as calls
from squads._cli import _common as common
from squads._cli import app, main_callback
from squads._context import ServedCommand, bind_context, get_context
from squads._daemon._commands import INTERNAL_ERROR
from squads._paths import SquadPaths
from tests._endpoint_client import command_body, post_commands

DIGEST = "x" * 32


def _cli(runner: CliRunner, *args: str) -> str:
    """What a command run in this process prints; it must succeed."""
    result = runner.invoke(app, list(args))
    assert result.exit_code == 0, result.output
    return result.output


def _attached(text: str) -> str:
    return base64.b64encode(text.encode()).decode("ascii")


COMPLETIONS = {
    "bash": {"COMP_WORDS": "sq ta", "COMP_CWORD": "1"},
    "zsh": {"_TYPER_COMPLETE_ARGS": "sq ta"},
    "fish": {"_TYPER_COMPLETE_ARGS": "sq ta", "_TYPER_COMPLETE_FISH_ACTION": "get-args"},
}


@pytest.mark.parametrize("shell", sorted(COMPLETIONS))
def test_completion_answers_the_candidates_local_mode_does(
    shell: str, project: SquadPaths, serve, runner: CliRunner
) -> None:
    env = {"_SQ_COMPLETE": f"complete_{shell}", **COMPLETIONS[shell]}
    local = runner.invoke(app, [], env=env)
    assert local.exit_code == 0
    assert "task" in local.output

    reply = post_commands(serve(project), command_body([], env=env))

    assert (reply.status, reply.json()) == (
        200,
        {"kind": "done", "output": [["stdout", local.output]], "exit_code": 0},
    )


def test_output_comes_back_in_the_order_the_command_wrote_it(
    project: SquadPaths, serve, runner: CliRunner
) -> None:
    broken = project.squad_dir / ".overrides" / "templates" / "items" / "feature.md.j2"
    broken.parent.mkdir(parents=True)
    broken.write_text("no markers here", encoding="utf-8")

    reply = post_commands(serve(project), command_body(["override", "diff", "--json"]))

    assert (reply.status, reply.json()) == (
        200,
        {
            "kind": "done",
            "output": [
                ["stdout", "[]\n"],
                [
                    "stderr",
                    "error: items/feature.md.j2 is broken (a required sq region is missing); "
                    "run `sq override list` for the state of every override\n",
                ],
            ],
            "exit_code": 1,
        },
    )


def test_a_file_the_request_does_not_carry_is_an_internal_error(
    project: SquadPaths, serve, runner: CliRunner
) -> None:
    _cli(runner, "create", "task", "Commented", "--author", "manager")
    argv = ["task", "2", "comment", "--file", "note.md", "--as", "manager"]

    reply = post_commands(serve(project), command_body(argv))

    assert (reply.status, reply.json()) == (
        200,
        {"kind": "done", "output": [["stderr", INTERNAL_ERROR]], "exit_code": 1},
    )
    assert json.loads(_cli(runner, "task", "2", "comments", "--json")) == []


def test_an_attachment_that_is_not_utf8_is_refused_as_local_mode_refuses_it(
    project: SquadPaths, serve, runner: CliRunner
) -> None:
    _cli(runner, "create", "task", "Commented", "--author", "manager")
    argv = ["task", "2", "comment", "--file", "note.md", "--as", "manager"]
    body = command_body(argv, attachments={"note.md": base64.b64encode(b"\xff").decode("ascii")})

    reply = post_commands(serve(project), body)

    assert (reply.status, reply.json()) == (
        200,
        {
            "kind": "done",
            "output": [
                [
                    "stderr",
                    "error: cannot read file 'note.md': "
                    "not valid utf-8 (invalid start byte at byte 0)\n",
                ]
            ],
            "exit_code": 1,
        },
    )


def test_a_served_command_cannot_select_an_api_of_its_own() -> None:
    served = ServedCommand({}, "utf-8", None, None, None, lambda: None)
    bind_context(replace(get_context(), served=served))

    with pytest.raises(RuntimeError, match="the daemon's own API"):
        calls.select_api()


def test_stdin_attached_under_a_dash_is_the_text_the_command_reads(
    project: SquadPaths, serve, runner: CliRunner
) -> None:
    _cli(runner, "create", "task", "Commented", "--author", "manager")
    argv = ["task", "2", "comment", "--file", "-", "--as", "manager"]

    reply = post_commands(
        serve(project), command_body(argv, attachments={"-": _attached("Piped in\n")})
    )

    posted = json.loads(_cli(runner, "task", "2", "comments", "--json"))
    assert [c["body"] for c in posted] == ["- Piped in"]
    assert (reply.status, reply.json()) == (
        200,
        {
            "kind": "done",
            "output": [["stdout", "commented on TASK-2 as manager\n"]],
            "exit_code": 0,
        },
    )


def _doomed(runner: CliRunner) -> str:
    """A task with one comment, and the short hash of that comment."""
    _cli(runner, "create", "task", "Prompted", "--author", "manager")
    _cli(runner, "task", "2", "comment", "-m", "Doomed", "--as", "manager")
    return json.loads(_cli(runner, "task", "2", "comments", "--json"))[0]["short_hash"]


def _removal(short: str) -> list[str]:
    return ["task", "2", "comment", short, "remove", "--as", "manager"]


def _asked(short: str) -> dict[str, object]:
    return {
        "kind": "prompt",
        "output": [["stdout", "2026-06-07T10:00:00Z manager: - Doomed\n"]],
        "text": "Remove this comment? [y/N]: ",
        "stream": "stdout",
        "digest": DIGEST,
    }


def test_a_prompt_stops_the_command_and_its_answer_finishes_it(
    project: SquadPaths, serve, runner: CliRunner
) -> None:
    short = _doomed(runner)
    daemon = serve(project)

    asked = post_commands(daemon, command_body(_removal(short))).json()

    assert {**asked, "digest": DIGEST} == _asked(short)
    assert len(asked["digest"]) == 32
    assert len(json.loads(_cli(runner, "task", "2", "comments", "--json"))) == 1

    answers = [{"digest": asked["digest"], "line": "y"}]
    done = post_commands(daemon, command_body(_removal(short), answers=answers))

    assert (done.status, done.json()) == (
        200,
        {
            "kind": "done",
            "output": [["stdout", f"removed {short} from TASK-2\n"]],
            "exit_code": 0,
        },
    )
    assert json.loads(_cli(runner, "task", "2", "comments", "--json")) == []


def test_a_refusal_aborts_the_command_and_removes_nothing(
    project: SquadPaths, serve, runner: CliRunner
) -> None:
    short = _doomed(runner)
    daemon = serve(project)
    asked = post_commands(daemon, command_body(_removal(short))).json()

    answers = [{"digest": asked["digest"], "line": "n"}]
    refused = post_commands(daemon, command_body(_removal(short), answers=answers))

    assert (refused.status, refused.json()) == (
        200,
        {"kind": "done", "output": [["stderr", "Aborted.\n"]], "exit_code": 1},
    )
    assert len(json.loads(_cli(runner, "task", "2", "comments", "--json"))) == 1


def test_a_line_that_is_not_an_answer_asks_again_with_the_error(
    project: SquadPaths, serve, runner: CliRunner
) -> None:
    short = _doomed(runner)
    daemon = serve(project)
    asked = post_commands(daemon, command_body(_removal(short))).json()

    answers = [{"digest": asked["digest"], "line": "perhaps"}]
    again = post_commands(daemon, command_body(_removal(short), answers=answers)).json()

    assert {**again, "digest": DIGEST} == {
        "kind": "prompt",
        "output": [],
        "text": "Error: invalid input\nRemove this comment? [y/N]: ",
        "stream": "stdout",
        "digest": DIGEST,
    }
    assert again["digest"] != asked["digest"]
    assert len(json.loads(_cli(runner, "task", "2", "comments", "--json"))) == 1


def test_an_answer_is_not_fed_to_a_screen_the_user_did_not_see(
    project: SquadPaths, serve, runner: CliRunner
) -> None:
    short = _doomed(runner)
    daemon = serve(project)
    asked = post_commands(daemon, command_body(_removal(short))).json()

    # The same comment under --json is shown on stderr: another screen than the one answered.
    answers = [{"digest": asked["digest"], "line": "y"}]
    argv = [*_removal(short), "--json"]
    changed = post_commands(daemon, command_body(argv, answers=answers)).json()

    assert {**changed, "digest": DIGEST} == {
        "kind": "prompt",
        "output": [["stderr", "2026-06-07T10:00:00Z manager: - Doomed\n"]],
        "text": "Remove this comment? [y/N]: ",
        "stream": "stderr",
        "digest": DIGEST,
    }
    assert changed["digest"] != asked["digest"]
    assert len(json.loads(_cli(runner, "task", "2", "comments", "--json"))) == 1


def _writing_then_asking() -> Command:
    """A command tree with one command that writes, then asks: no command of the CLI does."""
    host = typer.Typer(name="sq")
    host.callback()(main_callback)

    @host.command("write-then-ask")
    def write_then_ask() -> None:  # pyright: ignore[reportUnusedFunction]
        calls.call(ops.SYNC, SyncRequest())
        common.confirm("Go on?", json_out=False)

    return typer.main.get_command(host)


def test_a_prompt_reached_after_a_write_is_an_internal_error(project: SquadPaths, serve) -> None:
    daemon = serve(project, command=_writing_then_asking())

    reply = post_commands(daemon, command_body(["write-then-ask"]))

    assert (reply.status, reply.json()) == (
        200,
        {"kind": "done", "output": [["stderr", INTERNAL_ERROR]], "exit_code": 1},
    )


def test_the_command_endpoint_is_the_only_route_the_clients_files_travel_on(
    project: SquadPaths, serve
) -> None:
    daemon = serve(project)

    reply = daemon.request("GET", "/v1/commands")
    document = daemon.get("/v1/openapi.json").json()

    assert (reply.status, reply.headers["allow"]) == (405, "POST")
    assert "/v1/commands" not in document["paths"]


def test_a_request_that_is_not_a_command_is_refused_as_invalid(project: SquadPaths, serve) -> None:
    daemon = serve(project)

    reply = daemon.request("POST", "/v1/commands", {"argv": "task"})

    assert reply.status == 400
    assert reply.json()["error"]["type"] == "invalid"


def test_the_answer_carries_the_daemons_handler_time(project: SquadPaths, serve) -> None:
    reply = post_commands(serve(project), command_body(["--help"]))

    assert reply.status == 200
    assert reply.headers["server-timing"].startswith("handler;dur=")


def test_a_directory_the_client_names_with_c_is_never_read(
    project: SquadPaths, serve, tmp_path: Path
) -> None:
    missing = str(tmp_path / "not-there")
    body = command_body(["-C", missing, "list", "--type", "task", "--json"], client_dir=missing)

    reply = post_commands(serve(project), body)

    assert (reply.status, reply.json()) == (
        200,
        {"kind": "done", "output": [["stdout", "[]\n"]], "exit_code": 0},
    )


def test_an_argument_that_is_not_text_reaches_the_command_as_a_lone_surrogate(
    project: SquadPaths, serve
) -> None:
    reply = post_commands(serve(project), command_body(["\udcff"]))

    assert (reply.status, reply.json()["exit_code"]) == (200, 2)
    assert "No such command '\\udcff'." in reply.json()["output"][0][1]
