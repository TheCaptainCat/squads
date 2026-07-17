/**
 * Pure logic behind the `squads:` read-only preview: building/parsing the virtual-document
 * URI and turning an `sq show <id> --raw` outcome into the text VS Code's markdown preview
 * renders. Kept `vscode`-free (no `vscode.Uri`) so it's unit-testable with no host; the thin
 * `showDocumentProvider.ts` wrapper is what touches the real `vscode.Uri`/`TextDocumentContentProvider` API.
 */
import type { SqOutcome } from '../sqAdapter';

export const SQUADS_SCHEME = 'squads';

/** `squads:/<id>` — parseable by `vscode.Uri.parse`, whose `.path` then round-trips via
 * `extractIdFromUriPath`. */
export function buildShowUriString(id: string): string {
  return `${SQUADS_SCHEME}:/${id}`;
}

/** Inverse of `buildShowUriString`, given the `.path` of the parsed `vscode.Uri` (which keeps
 * the leading slash). */
export function extractIdFromUriPath(uriPath: string): string {
  return uriPath.startsWith('/') ? uriPath.slice(1) : uriPath;
}

/** Renders an `sq show <id> --raw` outcome to markdown text for the preview. On failure this
 * returns an actionable markdown message rather than blank/stale content — the caller is still
 * responsible for firing the accompanying VS Code notification. */
export function renderShowOutcome(id: string, outcome: SqOutcome<string>): string {
  if (outcome.kind === 'success') {
    return outcome.data;
  }
  return `# Squads: unable to load ${id}\n\n${outcome.message}`;
}
