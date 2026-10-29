"""The pieces every roster resource shares: the address, the requests of the verbs one
registration mounts on roles, skills and operators, and a name as shown."""

from squads._api._dto._base import DTO


class RosterAddress(DTO):
    """A role, skill or operator as a client names it: a slug, an id or a number, resolved by the
    operation within its own roster kind."""

    addr: str


class RosterBodyRequest(RosterAddress):
    """Set the entry's body to *text*, or append it; *force* replaces prose someone wrote."""

    text: str
    append: bool = False
    force: bool = False


class RosterStatusRequest(RosterAddress):
    """Move the entry to *status*; *unlink* removes the links a retirement refusal names."""

    status: str
    force: bool = False
    unlink: bool = False


class RosterRemoveRequest(RosterAddress):
    """Delete the entry; refused without *purge*."""

    purge: bool = False


class ViewRequest(RosterAddress):
    """Place, re-enable or disable the view tag *name* in the entry's body."""

    name: str


class SeveredRef(DTO):
    """A ref a retirement removed: the item that held it, its target and its kind."""

    referrer: str
    target: str
    kind: str


class NameDisplay(DTO):
    """A person's or an agent's name as shown: *name* with the pronouns applied when the squad
    shows them, and those pronouns, ``None`` when none are shown."""

    name: str
    pronouns: str | None
