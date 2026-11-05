/**
 * Pure domain logic for the team bulletin board (`Squads: Open Team Board`,
 * `itemPreviewManager.ts`'s owned board panel — same tier as its workflow-cheatsheet panel).
 * `sq board list --json` returns each notice's one-line summary and no body; this module sorts
 * and renders those rows, and renders the body of a notice the reader opened (fetched on demand
 * by `sq board show <n> --json`) under its entry.
 */
import type { SqOutcome } from '../sqAdapter';
import type { SqBoardNotice } from '../types';
import { escapeHtml, renderMarkdownToHtml } from './markdown';
import { summarizeOmissions } from './omissions';

/** Newest-posted notice first, the notice's own `id` as the tiebreak — mirrors `sq ui`'s
 * `BoardScreen` (`sorted(notices, key=lambda n: (n.posted_at, n.id), reverse=True)`), so both
 * clients read a board the same way. */
export function sortNoticesNewestFirst(notices: readonly SqBoardNotice[]): SqBoardNotice[] {
  return [...notices].sort(
    (a, b) => b.posted_at.localeCompare(a.posted_at) || b.id.localeCompare(a.id),
  );
}

/** What an opened notice shows under its entry: the body `board show` returned, or why it could
 * not be loaded. */
export type NoticeBody =
  | { readonly kind: 'body'; readonly body: string }
  | { readonly kind: 'failure'; readonly message: string };

export interface BoardRenderOptions {
  /** Opened notices, keyed by the notice's `id` (never its `n`: a position shifts when the board
   * changes). */
  readonly opened?: ReadonlyMap<string, NoticeBody>;
  /** A one-line note shown above the list, e.g. that the board changed under the reader. */
  readonly note?: string | undefined;
}

/** Said when a notice has no body to show. */
export const EMPTY_NOTICE_BODY_LINE = 'This notice has no body.';

/** Said above the re-listed board when `board show <n>` answered with another notice than the
 * clicked row's (`n` is a position, so the board changed since the listing). */
export const BOARD_CHANGED_NOTE =
  'The board changed since it was listed; here is the current list.';

const EMPTY_BOARD_MARKDOWN = '*(no current notices)*';

/** A summary is plain text, shown as written: escaped, a line break kept as a break. Markdown
 * would fold the lines together and turn an item id into a link the board panel cannot follow. */
function renderSummary(summary: string): string {
  return summary
    .split(/\r\n|\r|\n/)
    .map(escapeHtml)
    .join('<br>');
}

function renderBody(state: NoticeBody): string {
  if (state.kind === 'failure') {
    return renderMarkdownToHtml(`*Unable to load this notice: ${state.message}*`);
  }
  return state.body.trim() === ''
    ? `<p class="sq-notice-empty"><em>${escapeHtml(EMPTY_NOTICE_BODY_LINE)}</em></p>`
    : renderMarkdownToHtml(state.body);
}

function noticeBlock(notice: SqBoardNotice, opened: NoticeBody | undefined): string {
  const expiry = notice.until !== null ? ` (expires ${notice.until})` : '';
  const meta = `${notice.author} — ${notice.posted_at}${expiry}`;
  const body =
    opened === undefined ? '' : `<div class="sq-notice-body">${renderBody(opened)}</div>`;
  return (
    `<section class="sq-notice">` +
    `<div class="sq-notice-head" ` +
    `data-sq-notice-n="${String(notice.n)}" data-sq-notice-id="${escapeHtml(notice.id)}">` +
    `<div class="sq-notice-summary">${renderSummary(notice.summary)}</div>` +
    `<div class="sq-notice-meta">${escapeHtml(meta)}</div></div>${body}</section>`
  );
}

/** Renders a `getBoardList` outcome to the board panel's body HTML — same outcome-to-HTML shape
 * as `previewDocument.ts::renderWorkflowHtml`: the failure message becomes the whole document
 * body on anything but success, rather than the panel rendering blank. Every piece of notice
 * text (summary, author, body) goes through `renderMarkdownToHtml` or `escapeHtml`, so none
 * reaches the page unescaped.
 *
 * A one-or-more-unreadable-notices read (the partial-result exit code `4`) still comes back
 * `kind: 'success'` (`sqAdapter.ts::classifyNonZeroExit`), with `omissions` populated — so the
 * notices that *were* read render exactly as a clean board's would, with a visible "listing
 * partial" line appended rather than the panel showing nothing (the failure branch below is
 * unreachable for this case). */
export function renderBoardHtml(
  outcome: SqOutcome<readonly SqBoardNotice[]>,
  options: BoardRenderOptions = {},
): string {
  if (outcome.kind !== 'success') {
    return renderMarkdownToHtml(`# Squads: unable to load the board\n\n${outcome.message}`);
  }
  const note =
    options.note === undefined
      ? ''
      : `<p class="sq-notice-note"><em>${escapeHtml(options.note)}</em></p>`;
  const list =
    outcome.data.length === 0
      ? renderMarkdownToHtml(EMPTY_BOARD_MARKDOWN)
      : sortNoticesNewestFirst(outcome.data)
          .map((notice) => noticeBlock(notice, options.opened?.get(notice.id)))
          .join('');
  const partialNote =
    outcome.omissions !== undefined
      ? renderMarkdownToHtml(`---\n\n*${summarizeOmissions(outcome.omissions)}*`)
      : '';
  return `${note}${list}${partialNote}`;
}
