"""The hash of the workflow vocabulary a client parsed a command with and a daemon serves.

It is computed over the documents' canonical bytes, not over the parsed spec, so two builds that
hold the same files agree whatever their loader does. Standard library only: the client and the
daemon both call it.
"""

import hashlib
from dataclasses import dataclass

#: The format tag that opens the canonical bytes.
FORMAT_TAG = "squads-vocabulary-1"

#: The documents the vocabulary covers, in the order they are hashed: the package's own workflow
#: spec, then the project's override of it.
BUNDLED_DOCUMENT = "workflow.toml"
OVERRIDE_DOCUMENT = ".overrides/workflow.toml"
DOCUMENTS: tuple[str, ...] = (BUNDLED_DOCUMENT, OVERRIDE_DOCUMENT)

#: What a document that does not exist hashes as.
ABSENT = "absent"


@dataclass(frozen=True)
class VocabularyHash:
    """The vocabulary's hash and one digest per document, as 64 hexadecimal digits each."""

    hash: str
    documents: dict[str, str]


def canonical_text(raw: bytes | str) -> str:
    """A document's text as it is hashed: decoded as UTF-8, a leading byte-order mark removed and
    every line end a line feed."""
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    return text.removeprefix("﻿").replace("\r\n", "\n").replace("\r", "\n")


def _field(value: str) -> bytes:
    """*value* as bytes, preceded by its length, so no two sequences of fields collide."""
    data = value.encode("utf-8")
    return len(data).to_bytes(8, "big") + data


def _document(name: str, text: str | None) -> bytes:
    return _field(name) + _field(ABSENT if text is None else "text") + _field(text or "")


def vocabulary_hash(bundled: bytes | str, override: bytes | str | None) -> VocabularyHash:
    """The hash of the bundled workflow spec and the project's override of it, ``None`` for an
    override that does not exist."""
    parts = {
        BUNDLED_DOCUMENT: _document(BUNDLED_DOCUMENT, canonical_text(bundled)),
        OVERRIDE_DOCUMENT: _document(
            OVERRIDE_DOCUMENT, None if override is None else canonical_text(override)
        ),
    }
    whole = hashlib.sha256(_field(FORMAT_TAG))
    for name in DOCUMENTS:
        whole.update(parts[name])
    return VocabularyHash(
        hash=whole.hexdigest(),
        documents={name: hashlib.sha256(parts[name]).hexdigest() for name in DOCUMENTS},
    )
