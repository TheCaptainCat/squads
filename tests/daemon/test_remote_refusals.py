"""What the CLI prints when the daemon refuses a client for its schema or its vocabulary: whole
stderr and exit code, nothing run and no fall back to local mode."""

import functools
import http.client
from dataclasses import replace
from typing import NoReturn

import pytest

from squads import _aio
from squads._api import _client
from squads._api._client import HttpApi
from squads._api._vocabulary import VocabularyHash
from squads._cli import app
from squads._cli._remote import context_headers
from squads._context import bind_context, get_context
from squads._models._schema import SCHEMA_VERSION
from squads._paths import SquadPaths
from tests._daemon_harness import Served

pytestmark = pytest.mark.anyio


def no_local_run() -> NoReturn:
    """The local API of a client that must not fall back: asking for it fails the case."""
    pytest.fail("the client fell back to local mode")


def client_of(daemon: Served, vocabulary: VocabularyHash) -> HttpApi:
    return HttpApi(
        connect=lambda timeout: http.client.HTTPConnection(
            daemon.host, daemon.port, timeout=timeout
        ),
        endpoint=f"{daemon.host}:{daemon.port}",
        headers=context_headers,
        vocabulary=lambda: vocabulary,
        package_version="1.2.3",
        local=no_local_run,
    )


async def run_list(runner, daemon: Served, vocabulary: VocabularyHash):
    bind_context(replace(get_context(), api=client_of(daemon, vocabulary)))
    return await _aio.to_thread(functools.partial(runner.invoke, app, ["list"]))


def served_vocabulary(daemon: Served) -> VocabularyHash:
    identity = daemon.get("/v1/daemon").json()["vocabulary"]
    return VocabularyHash(hash=identity["hash"], documents=identity["documents"])


async def test_a_client_behind_the_squad_is_told_to_install_a_release(
    project: SquadPaths, serve, runner, monkeypatch
) -> None:
    daemon = serve(project)
    monkeypatch.setattr(_client, "SCHEMA_VERSION", "0.1")
    result = await run_list(runner, daemon, served_vocabulary(daemon))
    assert (result.exit_code, result.stdout, result.stderr) == (
        1,
        "",
        "error: squads 1.2.3 speaks schema v0.1, and the squad served at "
        f"{daemon.host}:{daemon.port} runs schema v{SCHEMA_VERSION}. Install a squads release at "
        f"schema v{SCHEMA_VERSION}, then re-run.\n",
    )


async def test_a_client_ahead_of_the_squad_is_told_to_upgrade_the_server(
    project: SquadPaths, serve, runner, monkeypatch
) -> None:
    daemon = serve(project)
    monkeypatch.setattr(_client, "SCHEMA_VERSION", "9.9")
    result = await run_list(runner, daemon, served_vocabulary(daemon))
    assert (result.exit_code, result.stdout, result.stderr) == (
        1,
        "",
        "error: squads 1.2.3 speaks schema v9.9, and the squad served at "
        f"{daemon.host}:{daemon.port} runs schema v{SCHEMA_VERSION}. The squad's server must be "
        "upgraded and the squad migrated (sq migrate up) before this client can use it.\n",
    )


async def test_a_vocabulary_that_differs_names_the_document(
    project: SquadPaths, serve, runner
) -> None:
    daemon = serve(project)
    ours = served_vocabulary(daemon)
    changed = VocabularyHash(
        hash="1" * 64, documents={**ours.documents, ".overrides/workflow.toml": "2" * 64}
    )
    result = await run_list(runner, daemon, changed)
    assert (result.exit_code, result.stdout, result.stderr) == (
        1,
        "",
        "error: this checkout's workflow vocabulary differs from the squad served at "
        f"{daemon.host}:{daemon.port} (.overrides/workflow.toml differs). Bring this checkout in "
        "line with the squad, by pulling its configuration or installing the squads version it "
        "runs, then re-run.\n",
    )
