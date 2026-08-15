"""Helpers for emitting valid Claude Code config."""

#: The model names Claude Code's own agent frontmatter accepts. A backend-local set, not a
#: shared one: it describes what *this host tool* can express, so a second backend is free to
#: know a different vocabulary. ``_roles._loader.VALID_MODELS`` (the catalog/override
#: whitelist) happens to carry the same four names today and is a separate question — what
#: squads will *store*, versus what this host can *render*. Keeping them separate is why
#: :func:`model_drop_warning` exists: whenever the two disagree, the value survives storage
#: and then silently fails to render, and that gap is reported rather than validated twice.
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
    """The WARN-only report for a role whose declared *model* this backend cannot express —
    ``None`` (the overwhelmingly common case) when there is nothing to report.

    A role's ``model`` reaches here from the role item's own ``extra``, which several paths
    can fill: a project role override (refused at load when it names a model outside the
    catalog whitelist), ``sq dev add --model`` (free-form), an imported or hand-migrated
    corpus. Whatever the path, the failure mode is identical and invisible: the value is
    durable in frontmatter, :func:`normalize_model` maps it to ``None``, the pointer template
    omits ``model:`` entirely, and the agent runs on the session default while the adopter
    reads their own declaration back from the item and believes otherwise.

    This is the write-time backstop for exactly that gap, not a second validator: it reports
    what this backend just failed to render, and refuses nothing.
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
