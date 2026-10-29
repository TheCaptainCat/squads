"""The base every DTO derives from."""

from pydantic import BaseModel, ConfigDict


class DTO(BaseModel):
    """A frozen model of JSON-native fields, whose schema is built on first use."""

    model_config = ConfigDict(frozen=True, defer_build=True)
