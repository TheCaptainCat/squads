"""One thing a partial read left out: the shared shape behind every corpus-walking read's
degraded-read report. It lives in dependency-free ``_models`` because its producers
(``_memory/_store.py``, ``_board/_store.py``) sit below the service layer and must import it without
inverting ``_cli -> _services -> (index store, backends, rendering)``.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Omission:
    """One item or file a partial read could not include. ``source`` is a display token (an item ID
    where known, else a squad-relative path) and must not be parsed. ``message`` is the human
    sentence, the text human-mode output prints for it. ``code`` is the machine class (every
    producer emits ``"unreadable"``); the set is open, and a consumer that does not recognise a code
    must still treat the entry as "part of the result is missing".
    """

    source: str
    message: str
    code: str = "unreadable"
