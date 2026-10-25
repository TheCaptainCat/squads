"""How a lifecycle reads in order: the happy-path spine, the states in display order and the
transition edges, for the workflow cheatsheet and the lifecycle tables.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from squads._workflow._models import Lifecycle


# Canonical priority order for well-known exception/side states: states appearing together
# in the side-state list sort by this (lower = earlier), regardless of BFS discovery order
# (e.g. Blocked before Cancelled). States absent here keep BFS order via the fallback rank
# (len(_SIDE_PRIORITY)).
_SIDE_PRIORITY: dict[str, int] = {
    "WontFix": 0,
    "Blocked": 1,
    "Cancelled": 2,
    "Rejected": 3,
    "Deprecated": 4,
}


def lifecycle_spine(machine: Lifecycle) -> list[str]:
    """The "happy-path" chain through *machine*: greedy forward walk from ``initial``,
    following the first unvisited outgoing transition at each step, stopping when no new
    state is reachable. E.g. ``["Draft", "Ready", "InProgress", "InReview", "Done"]`` for
    the bundled ``work`` lifecycle — exception/side branches (``Blocked``, ``Cancelled``)
    never appear, by construction (they're only reached as a non-first transition target).

    Shared by :func:`linearize_lifecycle` (renders it as ``"A → B → C"`` plus side states)
    and the "first happy-path status matching some predicate" family
    (:meth:`WorkflowSpec.first_active_status`/:meth:`WorkflowSpec.first_settled_status`) —
    those need the spine specifically, not full BFS reachability order, since a side branch
    like ``Cancelled`` can resolve to a settled role at a shallower BFS depth than the actual
    happy-path terminal and would otherwise be picked first.
    """
    initial = machine.initial
    transitions = machine.transitions
    spine: list[str] = [initial]
    visited: set[str] = {initial}
    current = initial
    while True:
        next_state: str | None = None
        for candidate in transitions.get(current, []):
            if candidate not in visited:
                next_state = candidate
                break
        if next_state is None:
            break
        spine.append(next_state)
        visited.add(next_state)
        current = next_state
    return spine


def linearize_lifecycle(machine: Lifecycle) -> str:
    """Derive a readable lifecycle string from an arbitrary transition graph.

    Algorithm:
    1. Build the **spine** (:func:`lifecycle_spine`) — the "happy-path" chain ``A → B → C``.
    2. Collect **side states** — all states reachable from ``machine.initial`` that
       are not on the spine — in BFS discovery order.
    3. Sort side states into canonical order using :data:`_SIDE_PRIORITY`, so the
       output is independent of TOML transition-list ordering.  States not in the
       priority table retain their relative BFS order (sorted after the known states).
    4. Return ``"A → B → C"`` when there are no side states, or
       ``"A → B → C (+ D, E)"`` otherwise.

    Deterministic: given the same machine the output is always identical.

    Examples::

        linearize_lifecycle(guide_machine)   # "Draft → Published → Deprecated"
        linearize_lifecycle(adr_machine)     # "Proposed → Accepted → Superseded (+ ...)"
    """
    initial = machine.initial
    transitions = machine.transitions
    spine = lifecycle_spine(machine)

    # BFS from initial to collect all reachable states in discovery order.
    bfs_order: list[str] = [initial]
    bfs_visited: set[str] = {initial}
    queue: list[str] = [initial]
    while queue:
        node = queue.pop(0)
        for nxt in transitions.get(node, []):
            if nxt not in bfs_visited:
                bfs_visited.add(nxt)
                bfs_order.append(nxt)
                queue.append(nxt)

    # Side states = reachable but not on the spine, sorted into canonical order.
    # Known states sort by their explicit priority; unknown states sort after them
    # in BFS-discovery order (secondary key = bfs position).
    spine_set: set[str] = set(spine)
    _unknown_rank = len(_SIDE_PRIORITY)
    side: list[str] = sorted(
        (s for s in bfs_order if s not in spine_set),
        key=lambda s: (_SIDE_PRIORITY.get(s, _unknown_rank), bfs_order.index(s)),
    )

    chain = " → ".join(spine)
    if side:
        return f"{chain} (+ {', '.join(side)})"
    return chain


def lifecycle_states_in_order(machine: Lifecycle) -> list[str]:
    """A deterministic listing of every state in ``machine``: BFS discovery order from
    ``initial`` (mirroring :func:`linearize_lifecycle`'s traversal), then any state left
    unreached (shouldn't normally happen) appended in sorted order.

    ``Lifecycle.states`` is a ``frozenset`` — its iteration order is hash-seed-dependent, so
    any caller whose output has to be byte-stable across process runs walks this instead.
    Today that is :meth:`WorkflowSpec.first_dropped_status`, which picks a status out of a
    machine for generated text; a hash-ordered pick would rewrite generated files at random.
    """
    order = [machine.initial]
    seen = {machine.initial}
    queue = [machine.initial]
    while queue:
        node = queue.pop(0)
        for nxt in machine.transitions.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                order.append(nxt)
                queue.append(nxt)
    order.extend(sorted(s for s in machine.states if s not in seen))
    return order


def lifecycle_edges_in_order(machine: Lifecycle) -> list[tuple[str, str]]:
    """Every transition edge in *machine*, as ``(source, target)`` pairs in a deterministic,
    byte-stable order: sources in :func:`lifecycle_states_in_order` order, targets in each
    source's declared ``Lifecycle.transitions`` list order (the TOML declaration order the
    ``list`` values preserve — never ``Lifecycle.states``, a ``frozenset`` with a
    hash-seed-dependent iteration order). A source with no outgoing edges contributes nothing.

    The order is deterministic for the ``sq workflow lifecycles --json`` catalog, which
    publishes each pair as a ``{from, to}`` object.
    """
    return [
        (src, dst)
        for src in lifecycle_states_in_order(machine)
        for dst in machine.transitions.get(src, [])
    ]
