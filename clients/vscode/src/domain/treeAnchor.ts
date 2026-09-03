/**
 * The client's wording for a tree root `sq` invented rather than found.
 *
 * Without a root argument, `sq tree` roots at every parentless item — except that an item on a
 * parent cycle has a parent, so a cyclic component would never be rooted at all and would vanish
 * from the hierarchy while `sq list` still returned it. The bare tree therefore picks one member
 * of each such component and roots there. Every member is an equally good choice, which makes
 * that pick a tiebreak rather than a fact: the root is a fabrication, and it is only acceptable
 * because it is disclosed. A surface that renders the flag-carrying node like any other root
 * asserts a hierarchy nobody wrote, and also hides that the drawing had to drop the edge closing
 * the loop back to the anchor — so the tree under-reports the very relation it draws.
 *
 * Every string a reader might meet the fabrication through lives here, so the two surfaces that
 * disclose it — the sidebar row and the mermaid subtree label — cannot drift into two different
 * claims. The wording deliberately mirrors the terminal renderer's own marker (the core's
 * `TREE_ANCHOR_MARKER`); the two cannot share a constant across the language boundary, so
 * agreeing is a choice that has to be re-made whenever either side is reworded.
 */

/** The row description's tag, kept to two words: it sits in a cramped, grey secondary line
 * alongside status/assignee, and the tooltip carries the full sentence. */
export const CYCLE_ANCHOR_DESCRIPTION_TAG = 'cycle anchor';

/** The full disclosure, bracketed exactly as the terminal renderer prints it — used where a
 * whole sentence fits and there is no tooltip to fall back to (the mermaid label). */
export const CYCLE_ANCHOR_MARKER = '[cycle anchor — not a real root; see sq check]';

/** The tooltip's own line, shaped like every other `Key: value` line `buildTooltip` emits. */
export const CYCLE_ANCHOR_TOOLTIP_LINE = 'Cycle anchor: not a real root; see sq check';
