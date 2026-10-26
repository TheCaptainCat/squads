"""How a lifecycle reads in order: the happy-path spine, the states in display order and the
transition edges, for the workflow cheatsheet and the lifecycle tables.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from squads._workflow._models import Lifecycle


# Canonical priority for well-known side states: those in the side-state list sort by this (lower is
# earlier, Blocked before Cancelled) regardless of BFS discovery; absent states keep BFS order via
# the fallback rank ``len(_SIDE_PRIORITY)``.
_SIDE_PRIORITY: dict[str, int] = {
    "WontFix": 0,
    "Blocked": 1,
    "Cancelled": 2,
    "Rejected": 3,
    "Deprecated": 4,
}


def lifecycle_spine(machine: Lifecycle) -> list[str]:
    """The "happy-path" chain through *machine*: a greedy forward walk from ``initial`` following
    the first unvisited outgoing transition until nothing new is reachable, e.g. ``["Draft",
    "Ready", "InProgress", "InReview", "Done"]``; side branches (``Blocked``, ``Cancelled``) are
    only non-first targets and never appear. Shared by :func:`linearize_lifecycle` and
    :meth:`WorkflowSpec.first_active_status`/:meth:`WorkflowSpec.first_settled_status`, which need
    the spine, not BFS order, since a side branch like ``Cancelled`` can resolve settled at a
    shallower depth than the real terminal.
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
    """Derive a readable lifecycle string from a transition graph, deterministically: the spine
    (:func:`lifecycle_spine`) as ``A → B → C``, then the side states (reachable from
    ``machine.initial`` but off the spine) sorted by :data:`_SIDE_PRIORITY` so TOML transition order
    does not matter, unknown ones keeping BFS order after, as ``A → B → C (+ D, E)``, or without the
    suffix when there are none. E.g. ``"Draft → Published → Deprecated"``.
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
    """Every state in *machine* in a deterministic order: BFS discovery from ``initial`` (as
    :func:`linearize_lifecycle` traverses), then any unreached state sorted. ``Lifecycle.states`` is
    a ``frozenset`` with hash-seed-dependent order, so a caller needing byte-stable output walks
    this instead; :meth:`WorkflowSpec.first_dropped_status` does, as a hash-ordered pick would
    rewrite generated files at random.
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
    """Every transition edge in *machine* as ``(source, target)`` pairs in a byte-stable order:
    sources in :func:`lifecycle_states_in_order` order, targets in each source's declared
    ``Lifecycle.transitions`` list order (never the hash-ordered ``frozenset``); a source with no
    edges contributes nothing. It gives the ``sq workflow lifecycles --json`` catalog its ``{from,
    to}`` objects a deterministic order.
    """
    return [
        (src, dst)
        for src in lifecycle_states_in_order(machine)
        for dst in machine.transitions.get(src, [])
    ]
