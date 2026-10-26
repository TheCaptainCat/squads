"""Helpers for emitting valid Claude Code config."""

#: The model names Claude Code's agent frontmatter accepts, a backend-local set: it is what this
#: host can render, whereas ``_roles._loader.VALID_MODELS`` is what squads will store. Where the
#: two disagree a value survives storage and fails to render, which :func:`model_drop_warning`
#: reports rather than validating twice.
_VALID_MODELS = {"sonnet", "opus", "haiku", "inherit"}


def normalize_model(model: str | None) -> str | None:
    """*model* if this host can express it, else ``None`` (the pointer omits the key).

    Callers that write a pointer must pair this with :func:`model_drop_warning` — dropping to
    ``None`` is a silent downgrade to the session default otherwise.
    """
    if model is None:
        return None
    return model if model in _VALID_MODELS else None


def model_drop_warning(slug: str, model: str | None) -> str | None:
    """The WARN-only report for a role whose declared *model* this backend cannot express.

    ``None`` (the common case) when there is nothing to report. A role's ``model`` comes from its
    item attribute, which several paths fill: a project role override (refused at load outside
    the catalog whitelist), ``sq dev add --model`` (free-form), an imported or hand-migrated
    corpus. Whatever the path, the failure is invisible: the value stays in frontmatter,
    :func:`normalize_model` maps it to ``None``, the template omits ``model:``, and the agent
    runs on the session default while the adopter believes otherwise. This is the write-time
    backstop for that gap, not a second validator: it reports what this backend failed to render
    and refuses nothing.
    """
    if model is None or model in _VALID_MODELS:
        return None
    return (
        f"role {slug!r} declares model {model!r}, which Claude Code's agent frontmatter does "
        f"not accept ({', '.join(sorted(_VALID_MODELS))}) — the generated pointer omits the "
        "model line entirely, so this agent runs on the session default. Set one of the "
        "accepted names, or drop the declaration to make that explicit."
    )


def oneline(text: str) -> str:
    """Collapse to a single line so it is safe inside double-quoted YAML."""
    return " ".join(text.split()).replace('"', "'")
