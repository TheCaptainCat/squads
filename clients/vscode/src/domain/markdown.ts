/**
 * A small, self-contained markdown -> HTML renderer for the item-preview webview.
 *
 * Deliberately "lightweight": it covers the subset `sq show --raw` dossiers actually use
 * (H1-H6 headings, bullet/numbered lists, fenced code blocks, inline code, bold/italic,
 * blockquotes, GFM-ish pipe tables, links, paragraphs) rather than full CommonMark. No nested
 * lists — a continuation/indented line under a list item is folded into that item's text as a
 * plain run, which is enough for the flat bullet lists item bodies actually contain.
 *
 * Kept `vscode`-free/pure so it's unit-testable with no host. By default a fenced code block
 * (including a ```mermaid``` one) renders as plain `<pre><code>` — the item preview's two
 * *structured* diagrams (children/subtree, ref graph) are a separate mechanism built from
 * `sq tree`/`sq graph --json`, not this markdown path (see `domain/graphDiagrams.ts`). Passing
 * `renderMermaidFences: true` opts a render into treating a ```mermaid``` fence as a live
 * diagram instead — markup compatible with the same client-side renderer those structured
 * graphs use (see `domain/previewDocument.ts`) — for a document whose own markdown source
 * carries its diagrams inline (e.g. the workflow cheatsheet) rather than a separate JSON fetch.
 *
 * Item-ID references (e.g. a task or decision id) found in any plain-text run are turned into
 * `<a class="sq-item-link" data-item-id="...">` anchors the webview's script intercepts — see
 * `previewDocument.ts`. `currentId`, when given, is left as plain text (no self-link).
 *
 * A `@<slug>` role mention (e.g. `@manager`, `@tech-lead`) gets the same anchor treatment when
 * `roles` (a `RoleDirectory`, threaded alongside `currentId` through every render function below)
 * resolves it to a known role — the anchor's `data-item-id` carries the role item's id (so the
 * existing click->navigate path opens the role's sheet with no new message type needed) and its
 * `title` attribute carries the hover text. A slug that doesn't resolve (no `roles` given, or not
 * found in it) is left as plain text — never a dead/broken link.
 */
import type { RoleDirectory } from './roleDirectory';

/** Matches a formatted item id: an uppercase-letter-led prefix, a dash, then a run of digits.
 * Deliberately generic/spec-agnostic (no hardcoded type-prefix list, matching every other
 * spec-driven surface this client reads) — a bare sub-entity local id (no dash) doesn't
 * match, only a real item id does. */
export const ITEM_ID_PATTERN = /\b[A-Z][A-Z0-9]*-\d+\b/g;

/** Anchored (whole-string) counterpart of `ITEM_ID_PATTERN`, for deciding whether a markdown
 * link's *url* (not a substring found in prose) is itself a bare item id. */
const FULL_ITEM_ID_PATTERN = /^[A-Z][A-Z0-9]*-\d+$/;

/** Matches a `@<slug>` role mention: `@` then a lowercase-letter-led run of lowercase
 * letters/digits/hyphens (a role slug's actual shape, e.g. `manager`, `tech-lead`). Generic/
 * spec-agnostic like `ITEM_ID_PATTERN` — no hardcoded role list here; whether a given match
 * resolves to a real role is `roles` (a `RoleDirectory`)'s job, at replace time. */
export const MENTION_PATTERN = /@([a-z][a-z0-9-]*)\b/g;

/** Schemes a rendered `[text](url)` link's `href` is allowed to carry. Defense-in-depth
 * alongside the webview's CSP: a `javascript:`/`data:`/`vbscript:`/etc. url is dropped rather
 * than escaped-and-emitted, so the renderer is safe on its own even if the CSP were ever
 * loosened. */
const SAFE_LINK_SCHEME = /^(https?|mailto):/i;

/** True when `url` is safe to emit verbatim as an `<a href>` — http(s) or mailto only. A link
 * whose url is itself a bare item id (e.g. `[see it](WIDGET-42)`) is handled separately,
 * through the same internal item-link routing every plain-text id reference gets (see
 * `renderLink`). */
export function isSafeLinkUrl(url: string): boolean {
  return SAFE_LINK_SCHEME.test(url.trim());
}

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** Escapes `text`, wraps every item-id token in a navigable-link anchor (save for `currentId`,
 * the item already open in this panel, left as plain escaped text), then — when `roles` is
 * given — does the same for every `@<slug>` role mention that resolves in it (an unresolved
 * slug is left as plain escaped text, same as any other prose). */
export function linkifyPlainText(text: string, currentId?: string, roles?: RoleDirectory): string {
  const escaped = escapeHtml(text);
  const withItemLinks = escaped.replace(ITEM_ID_PATTERN, (id) =>
    id === currentId ? id : `<a class="sq-item-link" href="#" data-item-id="${id}">${id}</a>`,
  );
  if (roles === undefined || roles.size === 0) {
    return withItemLinks;
  }
  return withItemLinks.replace(MENTION_PATTERN, (full: string, slug: string) => {
    const mention = roles.get(slug);
    if (mention === undefined) {
      return full;
    }
    const title = escapeHtml(mention.hoverText);
    return `<a class="sq-item-link" href="#" data-item-id="${mention.id}" title="${title}">@${slug}</a>`;
  });
}

const INLINE_TOKEN =
  /`([^`]+)`|\*\*([^*\n]+)\*\*|__([^_\n]+)__|\*([^*\n]+)\*|_([^_\n]+)_|\[([^\]]+)\]\(([^)\s]+)\)/g;

/** Renders one matched inline token (code/bold/italic/link) to HTML. Split out of
 * `renderInline` to keep that function's cyclomatic complexity low. */
function renderInlineToken(
  match: RegExpExecArray,
  currentId: string | undefined,
  roles: RoleDirectory | undefined,
): string {
  const [, code, boldStar, boldUnderscore, emStar, emUnderscore, linkText, linkUrl] = match;
  if (code !== undefined) {
    return `<code>${escapeHtml(code)}</code>`;
  }
  const bold = boldStar ?? boldUnderscore;
  if (bold !== undefined) {
    return `<strong>${linkifyPlainText(bold, currentId, roles)}</strong>`;
  }
  const italic = emStar ?? emUnderscore;
  if (italic !== undefined) {
    return `<em>${linkifyPlainText(italic, currentId, roles)}</em>`;
  }
  if (linkText !== undefined && linkUrl !== undefined) {
    return renderLink(linkText, linkUrl, currentId);
  }
  return '';
}

/** Renders a markdown `[text](url)` link. A url that is itself a bare item id routes through
 * the same internal `a.sq-item-link` mechanism plain-text id references get (self-links to
 * `currentId` suppressed the same way); a url on the safe-scheme allowlist becomes a normal
 * `<a href>`; anything else (an unsafe scheme, a relative path, a protocol-relative url) is
 * dropped, keeping only the escaped visible text — see `isSafeLinkUrl`. */
function renderLink(text: string, url: string, currentId: string | undefined): string {
  const trimmedUrl = url.trim();
  const escapedText = escapeHtml(text);
  if (FULL_ITEM_ID_PATTERN.test(trimmedUrl)) {
    return trimmedUrl === currentId
      ? escapedText
      : `<a class="sq-item-link" href="#" data-item-id="${trimmedUrl}">${escapedText}</a>`;
  }
  if (isSafeLinkUrl(trimmedUrl)) {
    return `<a href="${escapeHtml(trimmedUrl)}">${escapedText}</a>`;
  }
  return escapedText;
}

/** Renders one line/run of inline markdown (bold/italic/code/links) to HTML, linkifying item
 * ids (and, when `roles` resolves them, `@<slug>` role mentions) in every plain-text segment
 * along the way. */
export function renderInline(raw: string, currentId?: string, roles?: RoleDirectory): string {
  const regex = new RegExp(INLINE_TOKEN.source, 'g');
  let result = '';
  let lastIndex = 0;
  let match = regex.exec(raw);
  while (match !== null) {
    result += linkifyPlainText(raw.slice(lastIndex, match.index), currentId, roles);
    result += renderInlineToken(match, currentId, roles);
    lastIndex = regex.lastIndex;
    match = regex.exec(raw);
  }
  result += linkifyPlainText(raw.slice(lastIndex), currentId, roles);
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
  roles: RoleDirectory | undefined,
): { html: string; next: number } {
  const header = splitTableRow(lineAt(lines, start));
  const rows: string[][] = [];
  let i = start + 2;
  while (i < lines.length && lineAt(lines, i).trim() !== '' && lineAt(lines, i).includes('|')) {
    rows.push(splitTableRow(lineAt(lines, i)));
    i++;
  }
  const thead = `<thead><tr>${header.map((cell) => `<th>${renderInline(cell, currentId, roles)}</th>`).join('')}</tr></thead>`;
  const tbody = `<tbody>${rows
    .map(
      (row) =>
        `<tr>${row.map((cell) => `<td>${renderInline(cell, currentId, roles)}</td>`).join('')}</tr>`,
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
  roles: RoleDirectory | undefined,
): { html: string; next: number } {
  const firstMatch = LIST_MARKER.exec(lineAt(lines, start));
  const ordered = firstMatch !== null && /^\d+\.$/.test(firstMatch[1] ?? '');
  const { items, next } = scanListLines(lines, start);

  const tag = ordered ? 'ol' : 'ul';
  const itemsHtml = items
    .map((raw) => `<li>${renderInline(raw.join(' '), currentId, roles)}</li>`)
    .join('');
  return { html: `<${tag}>${itemsHtml}</${tag}>`, next };
}

interface BlockResult {
  readonly html: string;
  readonly next: number;
}

/** A live-mermaid fence's source/output ids: derived from its start line so they're unique
 * within one render pass with no shared/mutable counter state. */
function mermaidFenceIds(start: number): { sourceId: string; outputId: string } {
  const line = String(start);
  return {
    sourceId: `sq-mermaid-fence-${line}-source`,
    outputId: `sq-mermaid-fence-${line}-output`,
  };
}

function renderFence(
  lines: readonly string[],
  start: number,
  renderMermaidFences: boolean,
): BlockResult {
  const lang = FENCE_START.exec(lineAt(lines, start))?.[1] ?? '';
  const codeLines: string[] = [];
  let i = start + 1;
  while (i < lines.length && !FENCE_END.test(lineAt(lines, i))) {
    codeLines.push(lineAt(lines, i));
    i++;
  }
  i++; // skip the closing fence, or fall off the end if it was never closed
  const source = codeLines.join('\n');
  if (renderMermaidFences && lang.toLowerCase() === 'mermaid') {
    const { sourceId, outputId } = mermaidFenceIds(start);
    return {
      html:
        `<div class="sq-mermaid-block"><pre class="sq-graph-source" id="${sourceId}" ` +
        `data-output-id="${outputId}" hidden>${escapeHtml(source)}</pre>` +
        `<div class="sq-graph-output" id="${outputId}">Rendering…</div></div>`,
      next: i,
    };
  }
  const classAttr = lang === '' ? '' : ` class="language-${escapeHtml(lang)}"`;
  return {
    html: `<pre><code${classAttr}>${escapeHtml(source)}</code></pre>`,
    next: i,
  };
}

function renderHeading(
  lines: readonly string[],
  start: number,
  currentId: string | undefined,
  roles: RoleDirectory | undefined,
): BlockResult {
  const match = HEADING.exec(lineAt(lines, start));
  const level = String(match?.[1]?.length ?? 1);
  const text = match?.[2] ?? '';
  return {
    html: `<h${level}>${renderInline(text, currentId, roles)}</h${level}>`,
    next: start + 1,
  };
}

function renderBlockquote(
  lines: readonly string[],
  start: number,
  currentId: string | undefined,
  renderMermaidFences: boolean,
  roles: RoleDirectory | undefined,
): BlockResult {
  const quoteLines: string[] = [];
  let i = start;
  while (i < lines.length && BLOCKQUOTE.test(lineAt(lines, i))) {
    quoteLines.push(lineAt(lines, i).replace(/^ {0,3}> ?/, ''));
    i++;
  }
  return {
    html: `<blockquote>${renderMarkdownToHtml(quoteLines.join('\n'), currentId, renderMermaidFences, roles)}</blockquote>`,
    next: i,
  };
}

function renderParagraph(
  lines: readonly string[],
  start: number,
  currentId: string | undefined,
  roles: RoleDirectory | undefined,
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
  return { html: `<p>${renderInline(paraLines.join(' '), currentId, roles)}</p>`, next: i };
}

function renderBlock(
  lines: readonly string[],
  i: number,
  currentId: string | undefined,
  renderMermaidFences: boolean,
  roles: RoleDirectory | undefined,
): BlockResult {
  const line = lineAt(lines, i);
  if (FENCE_START.test(line)) {
    return renderFence(lines, i, renderMermaidFences);
  }
  if (HEADING.test(line)) {
    return renderHeading(lines, i, currentId, roles);
  }
  if (HR.test(line)) {
    return { html: '<hr>', next: i + 1 };
  }
  if (BLOCKQUOTE.test(line)) {
    return renderBlockquote(lines, i, currentId, renderMermaidFences, roles);
  }
  if (isTableStart(lines, i)) {
    return renderTable(lines, i, currentId, roles);
  }
  if (LIST_MARKER.test(line)) {
    return renderList(lines, i, currentId, roles);
  }
  return renderParagraph(lines, i, currentId, roles);
}

/** Renders a markdown document to a fragment of HTML (no `<html>`/`<body>` wrapper — see
 * `previewDocument.ts` for that). `currentId`, when given, is the id of the item being
 * displayed and is left as plain text rather than a self-link when found in the body.
 * `renderMermaidFences` (default `false`) opts a ```mermaid``` fence into rendering as a live
 * diagram instead of plain code — see the module doc comment. `roles`, when given, resolves
 * `@<slug>` role mentions to their role item's link + hover text (see the module doc comment
 * and `domain/roleDirectory.ts`); omitted, every `@slug` is left as plain text. */
export function renderMarkdownToHtml(
  markdown: string,
  currentId?: string,
  renderMermaidFences = false,
  roles?: RoleDirectory,
): string {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n');
  const out: string[] = [];
  let i = 0;

  while (i < lines.length) {
    if (lineAt(lines, i).trim() === '') {
      i++;
      continue;
    }
    const block = renderBlock(lines, i, currentId, renderMermaidFences, roles);
    out.push(block.html);
    i = block.next;
  }

  return out.join('\n');
}
