"""The envelope every operation answers with."""

from pydantic import BaseModel

from squads._models._omission import Omission


class Response[T](BaseModel, frozen=True, defer_build=True):
    """An operation's answer: its payload, what a partial read left out, and the notices the
    caller prints beside it."""

    data: T
    omitted: list[Omission] = []
    warnings: list[str] = []
