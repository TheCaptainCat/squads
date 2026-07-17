/**
 * A small, self-contained markdown -> HTML renderer for the item-preview webview.
 *
 * Deliberately "lightweight": it covers the subset `sq show --raw` dossiers actually use
 * (H1-H6 headings, bullet/numbered lists, fenced code blocks, inline code, bold/italic,
 * blockquotes, GFM-ish pipe tables, links, paragraphs) rather than full CommonMark. No nested
 * lists — a continuation/indented line under a list item is folded into that item's text as a
 * plain run, which is enough for the flat bullet lists item bodies actually contain.
 *
 * Kept `vscode`-free/pure so it's unit-testable with no host. Fenced code blocks (including
 * ```mermaid```) render as plain `<pre><code>` — diagram rendering is a separate, later task.
 *
 * Item-ID references (e.g. a task or decision id) found in any plain-text run are turned into
 * `<a class="sq-item-link" data-item-id="...">` anchors the webview's script intercepts — see
 * `previewDocument.ts`. `currentId`, when given, is left as plain text (no self-link).
 */

/** Matches a formatted item id: an uppercase-letter-led prefix, a dash, then a run of digits.
 * Deliberately generic/spec-agnostic (no hardcoded type-prefix list, matching every other
 * spec-driven surface this client reads) — a bare sub-entity local id (no dash) doesn't
 * match, only a real item id does. */
export const ITEM_ID_PATTERN = /\b[A-Z][A-Z0-9]*-\d+\b/g;

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** Escapes `text` then wraps every item-id token in a navigable-link anchor, save for
 * `currentId` (the item already open in this panel), which is left as plain escaped text. */
export function linkifyPlainText(text: string, currentId?: string): string {
  const escaped = escapeHtml(text);
  return escaped.replace(ITEM_ID_PATTERN, (id) =>
    id === currentId ? id : `<a class="sq-item-link" href="#" data-item-id="${id}">${id}</a>`,
  );
}

const INLINE_TOKEN =
  /`([^`]+)`|\*\*([^*\n]+)\*\*|__([^_\n]+)__|\*([^*\n]+)\*|_([^_\n]+)_|\[([^\]]+)\]\(([^)\s]+)\)/g;

/** Renders one matched inline token (code/bold/italic/link) to HTML. Split out of
 * `renderInline` to keep that function's cyclomatic complexity low. */
function renderInlineToken(match: RegExpExecArray, currentId: string | undefined): string {
  const [, code, boldStar, boldUnderscore, emStar, emUnderscore, linkText, linkUrl] = match;
  if (code !== undefined) {
    return `<code>${escapeHtml(code)}</code>`;
  }
  const bold = boldStar ?? boldUnderscore;
  if (bold !== undefined) {
    return `<strong>${linkifyPlainText(bold, currentId)}</strong>`;
  }
  const italic = emStar ?? emUnderscore;
  if (italic !== undefined) {
    return `<em>${linkifyPlainText(italic, currentId)}</em>`;
  }
  if (linkText !== undefined && linkUrl !== undefined) {
    return `<a href="${escapeHtml(linkUrl)}">${escapeHtml(linkText)}</a>`;
  }
  return '';
}

/** Renders one line/run of inline markdown (bold/italic/code/links) to HTML, linkifying item
 * ids in every plain-text segment along the way. */
export function renderInline(raw: string, currentId?: string): string {
  const regex = new RegExp(INLINE_TOKEN.source, 'g');
  let result = '';
  let lastIndex = 0;
  let match = regex.exec(raw);
  while (match !== null) {
    result += linkifyPlainText(raw.slice(lastIndex, match.index), currentId);
    result += renderInlineToken(match, currentId);
    lastIndex = regex.lastIndex;
    match = regex.exec(raw);
  }
  result += linkifyPlainText(raw.slice(lastIndex), currentId);
  return result;
}

const FENCE_START = /^```(\w*)\s*$/;
const FENCE_END = /^```\s*$/;
const HEADING = /^(#{1,6})\s+(.*)$/;
const HR = /^ {0,3}([-*_])(?: *\1){2,} *$/;
const BLOCKQUOTE = /^ {0,3}>/;
const LIST_MARKER = /^\s*([-*+]|\d+\.)\s+(.*)$/;
const SEPARATOR_ROW = /^\s*\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$/;

/** `noUncheckedIndexedAccess` makes every `lines[i]` a `string | undefined` — every call site
 * below only ever indexes within a bound already checked against `lines.length`, so this is a
 * defensive fallback (never actually hit), not a semantic default. */
function lineAt(lines: readonly string[], i: number): string {
  return lines[i] ?? '';
}

function startsNewBlock(line: string): boolean {
  return (
    FENCE_START.test(line) ||
    HEADING.test(line) ||
    HR.test(line) ||
    BLOCKQUOTE.test(line) ||
    LIST_MARKER.test(line) ||
    line.includes('|')
  );
}

function splitTableRow(line: string): string[] {
  let trimmed = line.trim();
  if (trimmed.startsWith('|')) {
    trimmed = trimmed.slice(1);
  }
  if (trimmed.endsWith('|')) {
    trimmed = trimmed.slice(0, -1);
  }
  return trimmed.split('|').map((cell) => cell.trim());
}

function isTableStart(lines: readonly string[], i: number): boolean {
  const next = lines[i + 1];
  return lineAt(lines, i).includes('|') && next !== undefined && SEPARATOR_ROW.test(next);
}

function renderTable(
  lines: readonly string[],
  start: number,
  currentId: string | undefined,
): { html: string; next: number } {
  const header = splitTableRow(lineAt(lines, start));
  const rows: string[][] = [];
  let i = start + 2;
  while (i < lines.length && lineAt(lines, i).trim() !== '' && lineAt(lines, i).includes('|')) {
    rows.push(splitTableRow(lineAt(lines, i)));
    i++;
  }
  const thead = `<thead><tr>${header.map((cell) => `<th>${renderInline(cell, currentId)}</th>`).join('')}</tr></thead>`;
  const tbody = `<tbody>${rows
    .map(
      (row) =>
        `<tr>${row.map((cell) => `<td>${renderInline(cell, currentId)}</td>`).join('')}</tr>`,
    )
    .join('')}</tbody>`;
  return { html: `<table>${thead}${tbody}</table>`, next: i };
}

interface ListScan {
  readonly items: readonly (readonly string[])[];
  readonly next: number;
}

/** Consumes the list-item lines (and their indented continuations) starting at `start`.
 * Split out of `renderList` to keep that function's cyclomatic complexity low. */
function scanListLines(lines: readonly string[], start: number): ListScan {
  const items: string[][] = [];
  let i = start;

  while (i < lines.length) {
    const line = lineAt(lines, i);
    const marker = LIST_MARKER.exec(line);
    if (marker !== null) {
      items.push([marker[2] ?? '']);
      i++;
      continue;
    }
    if (line.trim() === '') {
      const next = lines[i + 1];
      if (next !== undefined && (LIST_MARKER.test(next) || /^\s+\S/.test(next))) {
        i++;
        continue;
      }
      break;
    }
    if (/^\s+\S/.test(line) && items.length > 0) {
      items.at(-1)?.push(line.trim());
      i++;
      continue;
    }
    break;
  }

  return { items, next: i };
}

function renderList(
  lines: readonly string[],
  start: number,
  currentId: string | undefined,
): { html: string; next: number } {
  const firstMatch = LIST_MARKER.exec(lineAt(lines, start));
  const ordered = firstMatch !== null && /^\d+\.$/.test(firstMatch[1] ?? '');
  const { items, next } = scanListLines(lines, start);

  const tag = ordered ? 'ol' : 'ul';
  const itemsHtml = items
    .map((raw) => `<li>${renderInline(raw.join(' '), currentId)}</li>`)
    .join('');
  return { html: `<${tag}>${itemsHtml}</${tag}>`, next };
}

interface BlockResult {
  readonly html: string;
  readonly next: number;
}

function renderFence(lines: readonly string[], start: number): BlockResult {
  const lang = FENCE_START.exec(lineAt(lines, start))?.[1] ?? '';
  const codeLines: string[] = [];
  let i = start + 1;
  while (i < lines.length && !FENCE_END.test(lineAt(lines, i))) {
    codeLines.push(lineAt(lines, i));
    i++;
  }
  i++; // skip the closing fence, or fall off the end if it was never closed
  const classAttr = lang === '' ? '' : ` class="language-${escapeHtml(lang)}"`;
  return {
    html: `<pre><code${classAttr}>${escapeHtml(codeLines.join('\n'))}</code></pre>`,
    next: i,
  };
}

function renderHeading(
  lines: readonly string[],
  start: number,
  currentId: string | undefined,
): BlockResult {
  const match = HEADING.exec(lineAt(lines, start));
  const level = String(match?.[1]?.length ?? 1);
  const text = match?.[2] ?? '';
  return { html: `<h${level}>${renderInline(text, currentId)}</h${level}>`, next: start + 1 };
}

function renderBlockquote(
  lines: readonly string[],
  start: number,
  currentId: string | undefined,
): BlockResult {
  const quoteLines: string[] = [];
  let i = start;
  while (i < lines.length && BLOCKQUOTE.test(lineAt(lines, i))) {
    quoteLines.push(lineAt(lines, i).replace(/^ {0,3}> ?/, ''));
    i++;
  }
  return {
    html: `<blockquote>${renderMarkdownToHtml(quoteLines.join('\n'), currentId)}</blockquote>`,
    next: i,
  };
}

function renderParagraph(
  lines: readonly string[],
  start: number,
  currentId: string | undefined,
): BlockResult {
  // The first line is consumed unconditionally (guaranteeing progress even when it matches
  // the `|`-based approximation `startsNewBlock` uses for tables but isn't a real table
  // start) before using `startsNewBlock` to decide whether to keep accumulating.
  const paraLines: string[] = [lineAt(lines, start).trim()];
  let i = start + 1;
  while (i < lines.length && lineAt(lines, i).trim() !== '' && !startsNewBlock(lineAt(lines, i))) {
    paraLines.push(lineAt(lines, i).trim());
    i++;
  }
  return { html: `<p>${renderInline(paraLines.join(' '), currentId)}</p>`, next: i };
}

function renderBlock(
  lines: readonly string[],
  i: number,
  currentId: string | undefined,
): BlockResult {
  const line = lineAt(lines, i);
  if (FENCE_START.test(line)) {
    return renderFence(lines, i);
  }
  if (HEADING.test(line)) {
    return renderHeading(lines, i, currentId);
  }
  if (HR.test(line)) {
    return { html: '<hr>', next: i + 1 };
  }
  if (BLOCKQUOTE.test(line)) {
    return renderBlockquote(lines, i, currentId);
  }
  if (isTableStart(lines, i)) {
    return renderTable(lines, i, currentId);
  }
  if (LIST_MARKER.test(line)) {
    return renderList(lines, i, currentId);
  }
  return renderParagraph(lines, i, currentId);
}

/** Renders a markdown document to a fragment of HTML (no `<html>`/`<body>` wrapper — see
 * `previewDocument.ts` for that). `currentId`, when given, is the id of the item being
 * displayed and is left as plain text rather than a self-link when found in the body. */
export function renderMarkdownToHtml(markdown: string, currentId?: string): string {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n');
  const out: string[] = [];
  let i = 0;

  while (i < lines.length) {
    if (lineAt(lines, i).trim() === '') {
      i++;
      continue;
    }
    const block = renderBlock(lines, i, currentId);
    out.push(block.html);
    i = block.next;
  }

  return out.join('\n');
}
