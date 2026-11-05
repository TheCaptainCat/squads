/**
 * Pure domain logic for the team bulletin board (`Squads: Open Team Board`,
 * `itemPreviewManager.ts`'s owned board panel — same tier as its workflow-cheatsheet panel).
 * `sq board list --full --json` returns every notice with its one-line summary and its body, so
 * this module only sorts and renders what it's given: a credits line, the summary, then the body.
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

const EMPTY_BOARD_MARKDOWN = '*(no current notices)*';

/** A summary is plain text, shown as written: escaped, a line break kept as a break. Markdown
 * would fold the lines together. */
function renderSummary(summary: string): string {
  return summary
    .split(/\r\n|\r|\n/)
    .map(escapeHtml)
    .join('<br>');
}

/** The credits line, in the discussion comment's form — `<full name> (<slug>) — <timestamp>`,
 * the expiry after it when the notice has one. An `sq` that predates `author_name` leaves the
 * slug alone. */
function creditsHtml(notice: SqBoardNotice): string {
  const name = notice.author_name;
  const author =
    name === undefined || name === '' || name === notice.author
      ? `<span class="sq-comment-author">${escapeHtml(notice.author)}</span>`
      : `<span class="sq-comment-author">${escapeHtml(name)}</span> ` +
        `<span class="sq-comment-slug">(${escapeHtml(notice.author)})</span>`;
  const expiry =
    notice.until !== null
      ? ` <span class="sq-comment-edited">(expires ${escapeHtml(notice.until)})</span>`
      : '';
  return (
    `<div class="sq-comment-header">${author} — ` +
    `<span class="sq-comment-ts">${escapeHtml(notice.posted_at)}</span>${expiry}</div>`
  );
}

function noticeBlock(notice: SqBoardNotice): string {
  const body =
    notice.body.trim() === ''
      ? ''
      : `<div class="sq-notice-body">${renderMarkdownToHtml(notice.body)}</div>`;
  return (
    `<section class="sq-notice">${creditsHtml(notice)}` +
    `<div class="sq-notice-summary">${renderSummary(notice.summary)}</div>${body}</section>`
  );
}

/** Renders a `getBoardList` outcome to the board panel's body HTML — same outcome-to-HTML shape
 * as `previewDocument.ts::renderWorkflowHtml`: the failure message becomes the whole document
 * body on anything but success, rather than the panel rendering blank. Every piece of notice
 * text goes through `renderMarkdownToHtml` or `escapeHtml`, so none reaches the page unescaped.
 *
 * A one-or-more-unreadable-notices read (the partial-result exit code `4`) still comes back
 * `kind: 'success'` (`sqAdapter.ts::classifyNonZeroExit`), with `omissions` populated — so the
 * notices that *were* read render exactly as a clean board's would, with a visible "listing
 * partial" line appended rather than the panel showing nothing (the failure branch below is
 * unreachable for this case). */
export function renderBoardHtml(outcome: SqOutcome<readonly SqBoardNotice[]>): string {
  if (outcome.kind !== 'success') {
    return renderMarkdownToHtml(`# Squads: unable to load the board\n\n${outcome.message}`);
  }
  const list =
    outcome.data.length === 0
      ? renderMarkdownToHtml(EMPTY_BOARD_MARKDOWN)
      : sortNoticesNewestFirst(outcome.data).map(noticeBlock).join('');
  const partialNote =
    outcome.omissions !== undefined
      ? renderMarkdownToHtml(`---\n\n*${summarizeOmissions(outcome.omissions)}*`)
      : '';
  return `${list}${partialNote}`;
}
