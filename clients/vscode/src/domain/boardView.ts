/**
 * Pure domain logic for the team bulletin board (`Squads: Open Team Board`,
 * `itemPreviewManager.ts`'s owned board panel — same tier as its workflow-cheatsheet panel).
 * `sq board list --json` needs no CLI change on either client: every notice's full body already
 * comes back inline, so this module only sorts and renders what it's given.
 */
import type { SqOutcome } from '../sqAdapter';
import type { SqBoardNotice } from '../types';
import { renderMarkdownToHtml } from './markdown';
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

function noticeBlock(notice: SqBoardNotice): string {
  const expiry = notice.until !== null ? ` (expires ${notice.until})` : '';
  return `**${notice.author}** — ${notice.posted_at}${expiry}\n\n${notice.body}`;
}

/** One markdown document listing every notice, newest-first, separated by a rule — mirrors
 * `sq ui`'s `_notice_block`/`on_mount` join shape. */
export function buildBoardMarkdown(notices: readonly SqBoardNotice[]): string {
  if (notices.length === 0) {
    return EMPTY_BOARD_MARKDOWN;
  }
  return sortNoticesNewestFirst(notices).map(noticeBlock).join('\n\n---\n\n');
}

/** Renders a `getBoardList` outcome to the board panel's body HTML — same outcome-to-HTML shape
 * as `previewDocument.ts::renderWorkflowHtml`: the failure message becomes the whole document
 * body on anything but success, rather than the panel rendering blank. `renderMarkdownToHtml`
 * is what actually escapes every notice's author/body text — this module never emits HTML of
 * its own.
 *
 * A one-or-more-unreadable-notices read (the partial-result exit code `4`) still comes back
 * `kind: 'success'` (`sqAdapter.ts::classifyNonZeroExit`), with `omissions` populated — so the notices that *were*
 * read render exactly as a clean board's would, with a visible "listing partial" line appended
 * rather than the panel showing nothing (the failure branch below is unreachable for this case). */
export function renderBoardHtml(outcome: SqOutcome<readonly SqBoardNotice[]>): string {
  if (outcome.kind !== 'success') {
    return renderMarkdownToHtml(`# Squads: unable to load the board\n\n${outcome.message}`);
  }
  const markdown = buildBoardMarkdown(outcome.data);
  const partialNote =
    outcome.omissions !== undefined ? `\n\n---\n\n*${summarizeOmissions(outcome.omissions)}*` : '';
  return renderMarkdownToHtml(`${markdown}${partialNote}`);
}
