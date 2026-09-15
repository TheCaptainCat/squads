/**
 * Human-facing summary of a partial result's omissions report (`SqOutcome.omissions`)
 * — shared by the board panel and the Roster memory pools so a degraded listing reads
 * the same way in both rather than each view composing its own wording. `omissions.length === 0`
 * still means "partial" here: the caller decides *whether* to call this from
 * `outcome.omissions !== undefined`, and an empty array only ever means the report itself was
 * missing or malformed on an exit that still says the read was short — "partial, no detail",
 * never silently read as clean.
 */
import type { SqOmission } from '../types';

/** One line stating a listing is partial, with a count when the report named one. Mirrors
 * `sq ui`'s "N ... could not be read — listing partial" phrasing so the two clients agree. */
export function summarizeOmissions(omissions: readonly SqOmission[]): string {
  if (omissions.length === 0) {
    return 'Some entries could not be read — listing partial.';
  }
  const count = omissions.length.toString();
  const noun = omissions.length === 1 ? 'entry' : 'entries';
  return `${count} ${noun} could not be read — listing partial.`;
}
