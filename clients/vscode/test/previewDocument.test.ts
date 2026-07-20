import { describe, expect, it } from 'vitest';

import {
  buildArticleHtml,
  buildDiscussionHtml,
  buildGraphsHtml,
  buildHistoryToolbarHtml,
  buildPreviewHtml,
  buildSubEntitiesHtml,
  type DiscussionOutcome,
  type GraphOutcome,
  renderOutcomeHtml,
  renderWorkflowHtml,
  splitDossierMarkdown,
} from '../src/domain/previewDocument';
import {
  NAVIGATE_HISTORY_COMMAND,
  OPEN_ITEM_COMMAND,
  UPDATE_CONTENT_COMMAND,
} from '../src/domain/previewMessages';
import { buildRoleDirectory } from '../src/domain/roleDirectory';
import type { SqListItem, SqSubEntity } from '../src/types';

function makeRole(overrides: Partial<SqListItem> = {}): SqListItem {
  return {
    id: 'ROLE-1',
    sequence_id: 1,
    type: 'role',
    title: 'Catherine Manager',
    slug: 'manager',
    status: 'Active',
    description: 'Runs the work loop.',
    parent: null,
    author: 'manager',
    assignee: null,
    priority: null,
    severity: null,
    labels: [],
    refs: [],
    path: 'agents/roles/ROLE-000001-manager.md',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    is_open: true,
    ...overrides,
  };
}

const MERMAID_URI = 'vscode-webview://abc/media/mermaid.min.js';
const NO_TOOLBAR = buildHistoryToolbarHtml('TASK-452 — Title', false, false);
const NO_GRAPHS = buildGraphsHtml(
  { mermaidSource: null, message: 'none' },
  { mermaidSource: null, message: 'none' },
);
const NO_SUBENTITIES = buildSubEntitiesHtml({ entities: [] });
const NO_DISCUSSION = buildDiscussionHtml({ entries: [] });

describe('splitDossierMarkdown', () => {
  const dossier =
    '# TASK-452 — Title\n\n- **status:** Ready\n- **priority:** high\n\nBody paragraph one.\n\n- a body bullet, not metadata';

  it('splits the title + metadata bullets from the body prose', () => {
    const { header, body } = splitDossierMarkdown(dossier);
    expect(header).toBe('# TASK-452 — Title\n\n- **status:** Ready\n- **priority:** high');
    expect(body).toBe('Body paragraph one.\n\n- a body bullet, not metadata');
  });

  it('falls back to an empty header when the text has no H1 (e.g. a failure message)', () => {
    const { header, body } = splitDossierMarkdown('Squads: unable to load TASK-452');
    expect(header).toBe('');
    expect(body).toBe('Squads: unable to load TASK-452');
  });

  it('falls back to an empty header when the H1 has no metadata bullets right after it', () => {
    const { header, body } = splitDossierMarkdown('# Squads: unable to load TASK-452\n\nDetails.');
    expect(header).toBe('');
    expect(body).toBe('# Squads: unable to load TASK-452\n\nDetails.');
  });
});

describe('renderOutcomeHtml', () => {
  it('splits the dossier into a plain-text title copy, a full header (heading + bullets), and a body on success', () => {
    const { titleText, headerHtml, bodyHtml } = renderOutcomeHtml('TASK-452', {
      kind: 'success',
      data: '# TASK-452 — Title\n\n- **status:** Ready\n\nBody.',
    });
    expect(titleText).toBe('TASK-452 — Title');
    // The heading is never removed from the body's own header fragment — titleText is a copy
    // for the toolbar's compact label, not a move (a truncated toolbar label must never be the
    // reader's only complete view of the title).
    expect(headerHtml).toContain('<h1>');
    expect(headerHtml).toContain('status');
    expect(headerHtml).not.toContain('Body.');
    expect(bodyHtml).toContain('Body.');
    expect(bodyHtml).not.toContain('<h1>');
  });

  it('falls back to the item id as the title when the dossier has no detectable heading', () => {
    const { titleText, headerHtml } = renderOutcomeHtml('TASK-452', {
      kind: 'success',
      data: 'Just some text with no H1 at all.',
    });
    expect(titleText).toBe('TASK-452');
    expect(headerHtml).toBe('');
  });

  it('falls back to the item id as the title, with an empty header, on failure', () => {
    const { titleText, headerHtml, bodyHtml } = renderOutcomeHtml('TASK-452', {
      kind: 'runtime-error',
      message: 'Schema mismatch: run `sq migrate up`.',
      exitCode: 1,
    });
    expect(titleText).toBe('TASK-452');
    expect(headerHtml).toBe('');
    expect(bodyHtml).toContain('Squads: unable to load TASK-452');
    expect(bodyHtml).toContain('Schema mismatch');
  });

  it('links a @slug role mention found in the dossier body when roles resolves it', () => {
    const roles = buildRoleDirectory([makeRole()]);
    const { bodyHtml } = renderOutcomeHtml(
      'TASK-452',
      { kind: 'success', data: '# TASK-452 — Title\n\n- **status:** Ready\n\nAssigned: @manager.' },
      roles,
    );
    expect(bodyHtml).toContain('data-item-id="ROLE-1"');
  });
});

describe('renderWorkflowHtml', () => {
  it('renders the raw sq workflow --raw text as HTML on success', () => {
    const html = renderWorkflowHtml({
      kind: 'success',
      data: '## Team workflow\n\nSome prose.',
    });
    expect(html).toContain('<h2>');
    expect(html).toContain('Some prose.');
  });

  it('renders a fenced mermaid diagram live, not as plain code (unlike the item dossier path)', () => {
    const html = renderWorkflowHtml({
      kind: 'success',
      data: '```mermaid\nflowchart TD\n  A --> B\n```',
    });
    expect(html).toContain('class="sq-graph-source"');
    expect(html).not.toContain('language-mermaid');
  });

  it('renders an actionable message on failure instead of blank/stale content', () => {
    const html = renderWorkflowHtml({
      kind: 'runtime-error',
      message: 'Schema mismatch: run `sq migrate up`.',
      exitCode: 1,
    });
    expect(html).toContain('Squads: unable to load the workflow cheatsheet');
    expect(html).toContain('Schema mismatch');
  });
});

describe('buildPreviewHtml', () => {
  const html = buildPreviewHtml({
    title: 'TASK-452',
    toolbarHtml: NO_TOOLBAR,
    headerHtml: '<h1>hi</h1>',
    bodyHtml: '<p>hello</p>',
    graphsHtml: NO_GRAPHS,
    subEntitiesHtml: NO_SUBENTITIES,
    discussionHtml: NO_DISCUSSION,
    mermaidScriptUri: MERMAID_URI,
    nonce: 'abc123',
  });

  it('locks the CSP down to the render nonce, no remote content, no unsafe-inline', () => {
    expect(html).toContain(
      "Content-Security-Policy\" content=\"default-src 'none'; style-src 'nonce-abc123'; script-src 'nonce-abc123'\"",
    );
    expect(html).not.toContain('unsafe-inline');
    expect(html).not.toContain('unsafe-eval');
    expect(html).not.toContain('http://');
    expect(html).not.toContain('https://');
  });

  it('stamps the same nonce on the style tag and both script tags', () => {
    expect(html).toContain('<style nonce="abc123">');
    expect(html.match(/<script nonce="abc123"/g)).toHaveLength(2);
  });

  it('loads the bundled mermaid renderer via a nonce-carrying script src (no CDN)', () => {
    expect(html).toContain(`<script nonce="abc123" src="${MERMAID_URI}"></script>`);
  });

  it('embeds the rendered body once', () => {
    expect(html.match(/<p>hello<\/p>/g)).toHaveLength(1);
  });

  it('embeds the graph sections between the header and the body, both inside <article> (F23)', () => {
    const headerIndex = html.indexOf('<h1>hi</h1>');
    const graphsIndex = html.indexOf('class="sq-graph"');
    const bodyIndex = html.indexOf('<p>hello</p>');
    const articleEnd = html.indexOf('</article>');
    expect(headerIndex).toBeGreaterThan(-1);
    expect(graphsIndex).toBeGreaterThan(headerIndex);
    expect(bodyIndex).toBeGreaterThan(graphsIndex);
    expect(articleEnd).toBeGreaterThan(bodyIndex);
  });

  it('embeds the sub-entities section, then the discussion section, after </article>', () => {
    const withSections = buildPreviewHtml({
      title: 'TASK-452',
      toolbarHtml: NO_TOOLBAR,
      headerHtml: '<h1>hi</h1>',
      bodyHtml: '<p>hello</p>',
      graphsHtml: NO_GRAPHS,
      subEntitiesHtml: buildSubEntitiesHtml({
        entities: [
          {
            local_id: 'F1',
            title: 'A finding',
            status: 'Open',
            assignee: null,
            severity: 'high',
            story: null,
            body: '',
          },
        ],
      }),
      discussionHtml: buildDiscussionHtml({
        entries: [{ author: 'Ada Typescript', ts: '2026-07-17T00:00:00Z', body: 'A comment.' }],
      }),
      mermaidScriptUri: MERMAID_URI,
      nonce: 'abc123',
    });
    const articleEnd = withSections.indexOf('</article>');
    const subEntitiesIndex = withSections.indexOf('Sub-entities');
    const discussionIndex = withSections.indexOf('A comment.');
    expect(articleEnd).toBeGreaterThan(-1);
    expect(subEntitiesIndex).toBeGreaterThan(articleEnd);
    expect(discussionIndex).toBeGreaterThan(subEntitiesIndex);
  });

  it('renders no graph sections at all when headerHtml is empty (a failure/no-detectable-header dossier)', () => {
    const withoutHeader = buildPreviewHtml({
      title: 'TASK-452',
      toolbarHtml: NO_TOOLBAR,
      headerHtml: '',
      bodyHtml: '<p>hello</p>',
      graphsHtml: NO_GRAPHS,
      subEntitiesHtml: '',
      discussionHtml: '',
      mermaidScriptUri: MERMAID_URI,
      nonce: 'abc123',
    });
    const graphsIndex = withoutHeader.indexOf('class="sq-graph"');
    const bodyIndex = withoutHeader.indexOf('<p>hello</p>');
    expect(graphsIndex).toBeGreaterThan(-1);
    expect(bodyIndex).toBeGreaterThan(graphsIndex);
  });

  it('escapes the title', () => {
    const withUnsafeTitle = buildPreviewHtml({
      title: '<x>',
      toolbarHtml: '',
      headerHtml: '',
      bodyHtml: '',
      graphsHtml: '',
      subEntitiesHtml: '',
      discussionHtml: '',
      mermaidScriptUri: MERMAID_URI,
      nonce: 'n',
    });
    expect(withUnsafeTitle).toContain('<title>&lt;x&gt;</title>');
  });

  it('posts the same command constant the host-side parser accepts', () => {
    expect(html).toContain(`command: '${OPEN_ITEM_COMMAND}'`);
  });

  it('embeds the history toolbar inside <article>, before the header', () => {
    const withHistory = buildPreviewHtml({
      title: 'TASK-452',
      toolbarHtml: buildHistoryToolbarHtml('TASK-452 — Title', true, false),
      headerHtml: '<h1>hi</h1>',
      bodyHtml: '<p>hello</p>',
      graphsHtml: NO_GRAPHS,
      subEntitiesHtml: NO_SUBENTITIES,
      discussionHtml: NO_DISCUSSION,
      mermaidScriptUri: MERMAID_URI,
      nonce: 'abc123',
    });
    const articleStart = withHistory.indexOf('<article id="sq-article">');
    const toolbarIndex = withHistory.indexOf('data-sq-nav="back"');
    const headerIndex = withHistory.indexOf('<h1>hi</h1>');
    expect(articleStart).toBeGreaterThan(-1);
    expect(toolbarIndex).toBeGreaterThan(articleStart);
    expect(headerIndex).toBeGreaterThan(toolbarIndex);
  });

  it('posts a navigateHistory message when a toolbar nav button is clicked', () => {
    expect(html).toContain(`command: '${NAVIGATE_HISTORY_COMMAND}'`);
    expect(html).toContain("closest('[data-sq-nav]')");
    expect(html).toContain("direction: navTarget.getAttribute('data-sq-nav')");
  });

  it('intercepts a plain click and a middle-click distinctly (newTab true/false)', () => {
    expect(html).toContain('post(event, event.ctrlKey || event.metaKey)');
    expect(html).toContain('post(event, true)');
    expect(html).toContain("addEventListener('click'");
    expect(html).toContain("addEventListener('auxclick'");
  });

  it('routes both item links and graph nodes through the same click delegation (F25)', () => {
    expect(html).toContain("closest('a.sq-item-link, g.node[data-item-id]')");
  });

  it('stamps the mermaid render nonce onto every style tag found in a rendered svg', () => {
    expect(html).toContain("styles[i].setAttribute('nonce', nonce)");
    expect(html).toContain('mermaid.initialize');
  });

  it('configures flowchart wrappingWidth so long node labels wrap instead of clipping (F24)', () => {
    expect(html).toContain('wrappingWidth: 200');
  });

  it('stamps a rendered node with data-item-id, recovered from its mermaid node id (F25)', () => {
    expect(html).toContain('nodeIdPattern');
    expect(html).toContain("nodes[j].setAttribute('data-item-id', match[1].replace(/_/g, '-'))");
  });

  it('renders every .sq-graph-source generically (data-output-id lookup), not a fixed pair', () => {
    // Regression guard: the render script must scan by class/attribute, not a hardcoded
    // two-section list, so it also covers however many inline mermaid fences a document's own
    // markdown carries (e.g. the workflow cheatsheet).
    expect(html).toContain("querySelectorAll('.sq-graph-source')");
    expect(html).toContain("getAttribute('data-output-id')");
  });

  it('gives the article + sub-entities + discussion sections stable mount ids', () => {
    // These are exactly what an `UpdateContentMessage` patches on a same-item refresh — a
    // fresh load and a patch must target the same ids.
    expect(html).toContain('<article id="sq-article">');
    expect(html).toContain('<div id="sq-subentities">');
    expect(html).toContain('<div id="sq-discussion">');
  });

  it('listens for the host update-content message and patches the three mount points', () => {
    expect(html).toContain(`message.command !== '${UPDATE_CONTENT_COMMAND}'`);
    expect(html).toContain("getElementById('sq-article').innerHTML = message.articleHtml");
    expect(html).toContain("getElementById('sq-subentities').innerHTML = message.subEntitiesHtml");
    expect(html).toContain("getElementById('sq-discussion').innerHTML = message.discussionHtml");
  });

  it('re-runs the mermaid render pass after a patch, via a re-callable global', () => {
    expect(html).toContain('window.__sqRenderMermaid');
    expect(html).toContain('window.__sqRenderMermaid();');
  });

  it('explicitly scrolls to the top on a fresh load — a genuine navigation resets, never inherits scroll', () => {
    expect(html).toContain('window.scrollTo(0, 0);');
  });
});

describe('buildArticleHtml', () => {
  it('joins toolbar, header, graphs, and body in the same order/shape buildPreviewHtml embeds them in', () => {
    const articleHtml = buildArticleHtml(NO_TOOLBAR, '<h1>hi</h1>', NO_GRAPHS, '<p>hello</p>');
    const full = buildPreviewHtml({
      title: 'TASK-452',
      toolbarHtml: NO_TOOLBAR,
      headerHtml: '<h1>hi</h1>',
      bodyHtml: '<p>hello</p>',
      graphsHtml: NO_GRAPHS,
      subEntitiesHtml: NO_SUBENTITIES,
      discussionHtml: NO_DISCUSSION,
      mermaidScriptUri: MERMAID_URI,
      nonce: 'abc123',
    });
    expect(full).toContain(`<article id="sq-article">${articleHtml}</article>`);
  });
});

describe('buildHistoryToolbarHtml', () => {
  it('renders both buttons enabled when both directions are available', () => {
    const html = buildHistoryToolbarHtml('TASK-452 — Title', true, true);
    expect(html).toContain('data-sq-nav="back"');
    expect(html).toContain('data-sq-nav="forward"');
    expect(html).not.toContain('disabled');
  });

  it('disables the back button at the oldest point in history', () => {
    const html = buildHistoryToolbarHtml('TASK-452 — Title', false, true);
    expect(html).toMatch(/data-sq-nav="back"\s+disabled/);
    expect(html).not.toMatch(/data-sq-nav="forward"\s+disabled/);
  });

  it('disables the forward button at the newest point in history', () => {
    const html = buildHistoryToolbarHtml('TASK-452 — Title', true, false);
    expect(html).not.toMatch(/data-sq-nav="back"\s+disabled/);
    expect(html).toMatch(/data-sq-nav="forward"\s+disabled/);
  });

  it('disables both buttons on a freshly opened panel with no navigation yet', () => {
    const html = buildHistoryToolbarHtml('TASK-452 — Title', false, false);
    expect(html).toMatch(/data-sq-nav="back"\s+disabled/);
    expect(html).toMatch(/data-sq-nav="forward"\s+disabled/);
  });

  it('renders the title on the left, before the nav buttons on the right', () => {
    const html = buildHistoryToolbarHtml('TASK-452 — Title', true, true);
    const titleIndex = html.indexOf('sq-nav-title');
    const buttonsIndex = html.indexOf('sq-nav-buttons');
    expect(html).toContain(
      '<span class="sq-nav-title" title="TASK-452 — Title">TASK-452 — Title</span>',
    );
    expect(titleIndex).toBeGreaterThan(-1);
    expect(buttonsIndex).toBeGreaterThan(titleIndex);
  });

  it('carries the full title as a hover tooltip on the compact label, for when it ellipsis-truncates', () => {
    const longTitle = 'TASK-452 — A title so long the toolbar label will truncate it visually';
    const html = buildHistoryToolbarHtml(longTitle, true, true);
    expect(html).toContain(`title="${longTitle}"`);
  });

  it('escapes the title', () => {
    const html = buildHistoryToolbarHtml('<script>', true, true);
    expect(html).toContain('&lt;script&gt;');
    expect(html).not.toContain('<script>');
  });

  it('renders arrow-glyph buttons, not text labels, but keeps title/aria-label for discoverability', () => {
    const html = buildHistoryToolbarHtml('TASK-452 — Title', true, true);
    expect(html).not.toContain('>Back<');
    expect(html).not.toContain('>Forward<');
    expect(html).toContain('title="Back" aria-label="Back"');
    expect(html).toContain('title="Forward" aria-label="Forward"');
  });
});

describe('buildGraphsHtml', () => {
  const withSource: GraphOutcome = { mermaidSource: 'flowchart TD\n  A["a"]' };
  const withoutSource: GraphOutcome = { mermaidSource: null, message: 'sq graph failed: boom' };

  it('renders each graph as its own independently-foldable <details> section, collapsed by default (F23)', () => {
    const html = buildGraphsHtml(withSource, withSource);
    expect(html.match(/<details class="sq-graph">/g)).toHaveLength(2);
    expect(html).not.toContain('<details class="sq-graph" open>');
    expect(html).toContain('Children / Subtree');
    expect(html).toContain('Ref Graph');
  });

  it('hides the mermaid source in the DOM (client script reads it, user never sees raw text)', () => {
    const html = buildGraphsHtml(withSource, withSource);
    expect(html).toContain('class="sq-graph-source"');
    expect(html).toContain('hidden>flowchart TD');
  });

  it('gives each source element a data-output-id pointing at its own output element', () => {
    const html = buildGraphsHtml(withSource, withSource);
    expect(html.match(/data-output-id="sq-children-graph"/g)).toHaveLength(1);
    expect(html.match(/data-output-id="sq-refs-graph"/g)).toHaveLength(1);
  });

  it('escapes the embedded mermaid source', () => {
    const html = buildGraphsHtml({ mermaidSource: 'A["<script>"]' }, withSource);
    expect(html).toContain('A[&quot;&lt;script&gt;&quot;]');
    expect(html).not.toContain('<script>"');
  });

  it('shows the failure message in place of a diagram, section still present', () => {
    const html = buildGraphsHtml(withoutSource, withoutSource);
    expect(html).toContain('sq graph failed: boom');
    expect(html).not.toContain('class="sq-graph-source"');
    expect(html.match(/<details class="sq-graph">/g)).toHaveLength(2);
  });
});

describe('buildDiscussionHtml', () => {
  const twoComments: DiscussionOutcome = {
    entries: [
      { author: 'Elias Python', ts: '2026-07-16T18:14:07Z', body: '- First comment.' },
      { author: 'Ada Typescript', ts: '2026-07-16T18:19:50Z', body: '- Second **comment**.' },
    ],
  };

  it('renders no section at all when there is no discussion yet (graceful)', () => {
    expect(buildDiscussionHtml({ entries: [] })).toBe('');
  });

  it('renders one collapsible <details> section holding every comment', () => {
    const html = buildDiscussionHtml(twoComments);
    expect(html.match(/<details class="sq-graph" open>/g)).toHaveLength(1);
    expect(html).toContain('Discussion (2)');
  });

  it('renders each comment as an author + ISO-timestamp header, then its markdown body', () => {
    const html = buildDiscussionHtml(twoComments);
    expect(html).toContain('Elias Python');
    expect(html).toContain('2026-07-16T18:14:07Z');
    expect(html).toContain('Ada Typescript');
    expect(html).toContain('2026-07-16T18:19:50Z');
    // Bodies render through the same markdown renderer the dossier body uses.
    expect(html).toContain('<li>First comment.</li>');
    expect(html).toContain('<li>Second <strong>comment</strong>.</li>');
  });

  it('preserves discussion order (oldest first, as sq show --json emits it)', () => {
    const html = buildDiscussionHtml(twoComments);
    expect(html.indexOf('Elias Python')).toBeLessThan(html.indexOf('Ada Typescript'));
  });

  it('escapes the author and timestamp', () => {
    const html = buildDiscussionHtml({
      entries: [{ author: '<script>', ts: '2026-01-01T00:00:00Z', body: 'hi' }],
    });
    expect(html).toContain('&lt;script&gt;');
    expect(html).not.toContain('<script>');
  });

  it('suppresses a self-link when a comment mentions the current item id', () => {
    const html = buildDiscussionHtml(
      { entries: [{ author: 'a', ts: '2026-01-01T00:00:00Z', body: 'see TASK-452' }] },
      'TASK-452',
    );
    expect(html).toContain('TASK-452');
    expect(html).not.toContain('data-item-id="TASK-452"');
  });

  it('links a different item id mentioned in a comment', () => {
    const html = buildDiscussionHtml(
      { entries: [{ author: 'a', ts: '2026-01-01T00:00:00Z', body: 'see TASK-100' }] },
      'TASK-452',
    );
    expect(html).toContain('data-item-id="TASK-100"');
  });

  it('links a @slug role mention in a comment to its role item, with a hover title', () => {
    const roles = buildRoleDirectory([makeRole()]);
    const html = buildDiscussionHtml(
      { entries: [{ author: 'a', ts: '2026-01-01T00:00:00Z', body: '@manager please look' }] },
      'TASK-452',
      roles,
    );
    expect(html).toContain('data-item-id="ROLE-1"');
    expect(html).toContain('title="Catherine Manager (manager) — Runs the work loop."');
  });

  it('leaves a @slug mention in a comment as plain text when roles is omitted', () => {
    const html = buildDiscussionHtml({
      entries: [{ author: 'a', ts: '2026-01-01T00:00:00Z', body: '@manager please look' }],
    });
    expect(html).toContain('@manager');
    expect(html).not.toContain('data-item-id="ROLE-1"');
  });

  it('shows a failure message in place of the section on a failed fetch (never silently blank)', () => {
    const html = buildDiscussionHtml({ entries: null, message: 'sq show --json failed: boom' });
    expect(html).toContain('sq show --json failed: boom');
    expect(html).toContain('<details class="sq-graph" open><summary>Discussion</summary>');
  });
});

describe('buildSubEntitiesHtml', () => {
  const finding: SqSubEntity = {
    local_id: 'F15',
    title: 'Preview omits the item’s sub-entities',
    status: 'Open',
    assignee: null,
    severity: 'high',
    story: null,
    body: 'Add a section listing sub-entities.',
  };
  const story: SqSubEntity = {
    local_id: 'US1',
    title: 'Render sub-entities',
    status: 'InProgress',
    assignee: 'typescript-dev',
    severity: null,
    story: null,
    body: '',
  };

  it('renders no section at all when there are no sub-entities yet (graceful)', () => {
    expect(buildSubEntitiesHtml({ entities: [] })).toBe('');
  });

  it('renders one collapsible <details> section holding every sub-entity, in array order', () => {
    const html = buildSubEntitiesHtml({ entities: [finding, story] });
    expect(html.match(/<details class="sq-graph" open>/g)).toHaveLength(1);
    expect(html).toContain('Sub-entities (2)');
    expect(html.indexOf('F15')).toBeLessThan(html.indexOf('US1'));
  });

  it('renders the head badge line with status/severity/assignee/story, omitting absent fields', () => {
    const html = buildSubEntitiesHtml({ entities: [finding] });
    expect(html).toContain('Status: Open');
    expect(html).toContain('Severity: high');
    expect(html).not.toContain('Assignee:');
    expect(html).not.toContain('Story:');
  });

  it('renders assignee and story on the head line when present', () => {
    const html = buildSubEntitiesHtml({ entities: [story] });
    expect(html).toContain('Status: InProgress');
    expect(html).toContain('Assignee: typescript-dev');
    expect(html).not.toContain('Severity:');
  });

  it('renders a non-blank body as collapsible prose through the markdown renderer', () => {
    const html = buildSubEntitiesHtml({ entities: [finding] });
    expect(html).toContain('<details class="sq-subentity-body">');
    expect(html).toContain('<p>Add a section listing sub-entities.</p>');
  });

  it('renders no body <details> when the sub-entity has no body', () => {
    const html = buildSubEntitiesHtml({ entities: [story] });
    expect(html).not.toContain('sq-subentity-body');
  });

  it('escapes the local id and title', () => {
    const html = buildSubEntitiesHtml({
      entities: [{ ...story, local_id: '<script>', title: '<b>x</b>' }],
    });
    expect(html).toContain('&lt;script&gt;');
    expect(html).not.toContain('<script>');
    expect(html).toContain('&lt;b&gt;x&lt;/b&gt;');
  });

  it('suppresses a self-link when a sub-entity body mentions the current item id', () => {
    const html = buildSubEntitiesHtml(
      { entities: [{ ...finding, body: 'see TASK-452' }] },
      'TASK-452',
    );
    expect(html).toContain('TASK-452');
    expect(html).not.toContain('data-item-id="TASK-452"');
  });

  it('links a @slug role mention in a sub-entity body to its role item', () => {
    const roles = buildRoleDirectory([makeRole()]);
    const html = buildSubEntitiesHtml(
      { entities: [{ ...finding, body: 'assign to @manager' }] },
      'TASK-452',
      roles,
    );
    expect(html).toContain('data-item-id="ROLE-1"');
  });

  it('shows a failure message in place of the section on a failed fetch (never silently blank)', () => {
    const html = buildSubEntitiesHtml({ entities: null, message: 'sq show --json failed: boom' });
    expect(html).toContain('sq show --json failed: boom');
    expect(html).toContain('<details class="sq-graph" open><summary>Sub-entities</summary>');
  });
});
