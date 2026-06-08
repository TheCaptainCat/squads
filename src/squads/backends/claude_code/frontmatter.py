"""Helpers for emitting valid Claude Code config."""

_VALID_MODELS = {"sonnet", "opus", "haiku", "inherit"}


def normalize_model(model: str | None) -> str | None:
    if model is None:
        return None
    return model if model in _VALID_MODELS else None


def oneline(text: str) -> str:
    """Collapse to a single line so it is safe inside double-quoted YAML."""
    return " ".join(text.split()).replace('"', "'")
