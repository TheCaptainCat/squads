"""One thing a partial read left out — the shared shape behind every corpus-walking read
surface's degraded-read report.

Lives in ``_models`` (dependency-free) rather than ``_services`` because the producers that
build it — ``_memory/_store.py`` and ``_board/_store.py`` — sit *below* the service layer in
this project's layering (``_cli -> _services -> (index store, backends, rendering)``); a plain,
internal-dependency-free dataclass here is importable from all of them without inverting that
direction.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Omission:
    """One item/file a partial read could not include in its answer.

    ``source`` is the display token identifying what could not be read — an item ID where one
    is known, a squad-relative path otherwise. It is for display only; a consumer must not
    parse it.

    ``message`` is the human sentence — the same text human-mode output has always printed for
    this omission, byte-for-byte.

    ``code`` is the machine class of the omission. Every producer in this codebase emits
    ``"unreadable"`` today; the set is open, and the rule that keeps it growable is that a
    consumer which does not recognise a code still treats the entry as "part of the result is
    missing" (nothing branches on the value to decide *whether* the result is partial).
    """

    source: str
    message: str
    code: str = "unreadable"
