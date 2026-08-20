import { describe, expect, it } from 'vitest';

import { buildSubEntityFieldBindings } from '../src/domain/badgeCatalog';
import { MERMAID_NODE_ID_ESCAPE_SOURCE, mermaidNodeId } from '../src/domain/graphDiagrams';
import { buildItemDirectory } from '../src/domain/itemDirectory';
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
  type SubEntityFieldContext,
} from '../src/domain/previewDocument';
import {
  NAVIGATE_HISTORY_COMMAND,
  OPEN_ITEM_COMMAND,
  REFRESH_COMMAND,
  TOGGLE_FOLD_COMMAND,
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
            story: null,
            body: '',
            badges: { severity: 'high' },
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

  it('posts a refresh message when the toolbar refresh button is clicked', () => {
    expect(html).toContain(`command: '${REFRESH_COMMAND}'`);
    expect(html).toContain("closest('[data-sq-refresh]')");
  });

  it('checks the refresh button before falling through to link/graph-node click handling', () => {
    // A structural guard, not a behavioral one: the refresh check must come before the shared
    // `post(...)` fallthrough so a click on the button never also gets misread as a link click.
    const refreshBranch = html.indexOf('data-sq-refresh');
    const postCall = html.indexOf('post(event, event.ctrlKey');
    expect(refreshBranch).toBeGreaterThan(-1);
    expect(postCall).toBeGreaterThan(refreshBranch);
  });

  it('reports a fold toggle via a capture-phase listener (native toggle does not bubble)', () => {
    expect(html).toContain(`command: '${TOGGLE_FOLD_COMMAND}'`);
    expect(html).toContain("addEventListener('toggle'");
    expect(html).toContain("matches('[data-sq-fold-id]')");
    expect(html).toContain('open: target.open');
    // The trailing `true` is the capture flag — a plain bubbling listener would miss a `toggle`
    // event, which does not bubble.
    expect(html).toMatch(/addEventListener\('toggle', function \(event\) \{[\s\S]*?\}, true\);/);
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

  it('stamps a rendered node with data-item-id, decoded from its mermaid node id (F25)', () => {
    expect(html).toContain('nodeIdPattern');
    expect(html).toContain("nodes[j].setAttribute('data-item-id', decodeNodeId(match[1]))");
  });

  it('decodes with the encoder’s own escape pattern rather than a second copy of it', () => {
    // Drift guard: the webview decoder is inlined script text and cannot import, so the one
    // thing it must share with `graphDiagrams.ts` is this pattern.
    expect(html).toContain(`var escapePattern = /${MERMAID_NODE_ID_ESCAPE_SOURCE}/g;`);
  });

  it('no longer folds every underscore to a hyphen, which mangled an underscored prefix', () => {
    expect(html).not.toContain("replace(/_/g, '-')");
  });

  /**
   * The decoder that actually ships is script *text*, so it is lifted straight out of the
   * emitted page and executed here — asserting on the string alone would prove only that the
   * characters are present, not that they invert the encoder.
   */
  describe('the emitted decoder, executed', () => {
    function shippedDecoder(): (encoded: string) => string {
      const source = /var escapePattern[\s\S]*?var decodeNodeId = function[\s\S]*?\n {4}};/.exec(
        html,
      )?.[0];
      if (source === undefined) {
        throw new Error('could not lift the decoder out of the emitted script');
      }
      // eslint-disable-next-line @typescript-eslint/no-implied-eval
      const build = new Function(`${source} return decodeNodeId;`) as () => (
        encoded: string,
      ) => string;
      return build();
    }

    const ids = [
      'TASK-452',
      'MY-WIDGET-19',
      'MY_WIDGET-19',
      'MY_WIDGET_EXTRA-19',
      'W-1',
      'widget-19',
      'C++-19',
    ];

    for (const id of ids) {
      it(`round-trips ${id} through the shipped decoder`, () => {
        expect(shippedDecoder()(mermaidNodeId(id))).toBe(id);
      });
    }

    it('leaves a hand-authored fence’s own node id alone (no escape to undo)', () => {
      expect(shippedDecoder()('InProgress')).toBe('InProgress');
    });
  });

  /**
   * Which diagrams may have their nodes stamped as navigable items. The preview renders two
   * kinds of mermaid into the same page — the structured item graphs, whose node ids ARE item
   * ids, and whatever a ```mermaid``` fence carries, whose node ids are the author's own — and
   * the post-render pass has to tell them apart or it offers clicks that open nothing.
   */
  describe('the emitted item-node gate, executed', () => {
    function shippedGate(): (sourceEl: { hasAttribute: (name: string) => boolean }) => boolean {
      const source = /var stampsItemNodes = function[\s\S]*?\n {4}};/.exec(html)?.[0];
      if (source === undefined) {
        throw new Error('could not lift the item-node gate out of the emitted script');
      }
      // eslint-disable-next-line @typescript-eslint/no-implied-eval
      const build = new Function(`${source} return stampsItemNodes;`) as () => (sourceEl: {
        hasAttribute: (name: string) => boolean;
      }) => boolean;
      return build();
    }

    function sourceElement(attributes: readonly string[]) {
      return { hasAttribute: (name: string) => attributes.includes(name) };
    }

    it('admits a source that declares its nodes are items', () => {
      expect(shippedGate()(sourceElement(['data-sq-item-nodes']))).toBe(true);
    });

    it('refuses a source that does not, which is every fence-rendered diagram', () => {
      expect(shippedGate()(sourceElement([]))).toBe(false);
      expect(shippedGate()(sourceElement(['data-output-id', 'hidden']))).toBe(false);
    });

    it('gates the stamping loop rather than running it unconditionally', () => {
      expect(html).toContain('if (stampsItemNodes(sourceEl)) {');
    });
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

  it('renders the refresh button immediately left of back/forward, inside the same button group', () => {
    const html = buildHistoryToolbarHtml('TASK-452 — Title', true, true);
    const buttonsIndex = html.indexOf('sq-nav-buttons');
    const refreshIndex = html.indexOf('data-sq-refresh');
    const backIndex = html.indexOf('data-sq-nav="back"');
    expect(refreshIndex).toBeGreaterThan(buttonsIndex);
    expect(backIndex).toBeGreaterThan(refreshIndex);
  });

  it('the refresh button carries no disabled state, unlike the arrows at the ends of history', () => {
    const html = buildHistoryToolbarHtml('TASK-452 — Title', false, false);
    const refreshButton = /<button[^>]*data-sq-refresh[^>]*>/.exec(html)?.[0] ?? '';
    expect(refreshButton).not.toContain('disabled');
    expect(refreshButton).toContain('title="Refresh" aria-label="Refresh"');
  });
});

describe('buildGraphsHtml', () => {
  const withSource: GraphOutcome = { mermaidSource: 'flowchart TD\n  A["a"]' };
  const withoutSource: GraphOutcome = { mermaidSource: null, message: 'sq graph failed: boom' };

  it('renders each graph as its own independently-foldable <details> section, collapsed by default (F23)', () => {
    const html = buildGraphsHtml(withSource, withSource);
    expect(html.match(/<details class="sq-graph" data-sq-fold-id="[a-z]+">/g)).toHaveLength(2);
    expect(html).not.toContain('open>');
    expect(html).toContain('Children / Subtree');
    expect(html).toContain('Ref Graph');
  });

  it('stamps each graph section with its own stable fold id', () => {
    const html = buildGraphsHtml(withSource, withSource);
    expect(html).toContain('data-sq-fold-id="children"');
    expect(html).toContain('data-sq-fold-id="refs"');
  });

  it('restores a fold as open per the childrenOpen/refsOpen flags, independently', () => {
    const bothOpen = buildGraphsHtml(withSource, withSource, true, true);
    expect(bothOpen.match(/ open>/g)).toHaveLength(2);

    const childrenOnly = buildGraphsHtml(withSource, withSource, true, false);
    expect(childrenOnly).toContain('data-sq-fold-id="children" open>');
    expect(childrenOnly).not.toContain('data-sq-fold-id="refs" open>');
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
    expect(html.match(/<details class="sq-graph" data-sq-fold-id="[a-z]+">/g)).toHaveLength(2);
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
    story: null,
    body: 'Add a section listing sub-entities.',
    badges: { severity: 'high' },
  };
  const story: SqSubEntity = {
    local_id: 'US1',
    title: 'Render sub-entities',
    status: 'InProgress',
    assignee: 'typescript-dev',
    story: null,
    body: '',
  };
  /** The two catalogs joined into sub-entity field bindings, as the preview manager does. */
  const findingFields: SubEntityFieldContext = {
    itemType: 'review',
    fieldBindings: buildSubEntityFieldBindings(
      [
        {
          type: 'review',
          order: null,
          prefix: 'REV',
          reserved: false,
          category: 'work',
          subentity_kind: 'finding',
        },
      ],
      [
        {
          subentity_kind: 'finding',
          fields: [{ code: 'severity', label: 'Severity', collection: 'severity' }],
        },
      ],
    ),
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

  it('renders the head badge line with status/declared fields/assignee/story, omitting absent fields', () => {
    const html = buildSubEntitiesHtml(
      { entities: [finding] },
      undefined,
      undefined,
      undefined,
      findingFields,
    );
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

  /**
   * The head line reads the payload's own `badges` map and labels it from the kind catalog, so
   * a project that renames its sub-entity axis is followed with no client change. These drive
   * the same production function the preview calls.
   */
  it('labels a badge field by the label the kind declares for it', () => {
    const relabelled: SubEntityFieldContext = {
      itemType: 'review',
      fieldBindings: buildSubEntityFieldBindings(
        [
          {
            type: 'review',
            order: null,
            prefix: 'REV',
            reserved: false,
            category: 'work',
            subentity_kind: 'finding',
          },
        ],
        [
          {
            subentity_kind: 'finding',
            fields: [{ code: 'impact', label: 'Impact', collection: 'impact' }],
          },
        ],
      ),
    };
    const html = buildSubEntitiesHtml(
      { entities: [{ ...finding, badges: { impact: 'high' } }] },
      undefined,
      undefined,
      undefined,
      relabelled,
    );

    expect(html).toContain('Impact: high');
    expect(html).not.toContain('Severity:');
  });

  it('renders every declared field the sub-entity carries, in the payload’s own key order', () => {
    const twoFields: SubEntityFieldContext = {
      itemType: 'review',
      fieldBindings: buildSubEntityFieldBindings(
        [
          {
            type: 'review',
            order: null,
            prefix: 'REV',
            reserved: false,
            category: 'work',
            subentity_kind: 'finding',
          },
        ],
        [
          {
            subentity_kind: 'finding',
            fields: [
              { code: 'severity', label: 'Severity', collection: 'severity' },
              { code: 'confidence', label: 'Confidence', collection: 'confidence' },
            ],
          },
        ],
      ),
    };
    const html = buildSubEntitiesHtml(
      { entities: [{ ...finding, badges: { severity: 'high', confidence: 'low' } }] },
      undefined,
      undefined,
      undefined,
      twoFields,
    );

    expect(html).toContain('Severity: high · Confidence: low');
  });

  it('falls back to the raw field code when no kind catalog is available', () => {
    const html = buildSubEntitiesHtml({ entities: [finding] });

    expect(html).toContain('severity: high');
  });

  it('renders no badge entry for a sub-entity whose payload omits the badges map', () => {
    const html = buildSubEntitiesHtml(
      { entities: [story] },
      undefined,
      undefined,
      undefined,
      findingFields,
    );

    expect(html).toContain('Status: InProgress');
    expect(html).not.toContain('Severity:');
  });

  it('escapes a badge label and value rather than emitting them raw', () => {
    const html = buildSubEntitiesHtml({
      entities: [{ ...finding, badges: { '<field>': '<value>' } }],
    });

    expect(html).toContain('&lt;field&gt;: &lt;value&gt;');
    expect(html).not.toContain('<field>');
  });

  it('renders a non-blank body as collapsible prose through the markdown renderer', () => {
    const html = buildSubEntitiesHtml({ entities: [finding] });
    expect(html).toContain('<details class="sq-subentity-body" data-sq-fold-id="F15">');
    expect(html).toContain('<p>Add a section listing sub-entities.</p>');
  });

  it('renders no body <details> when the sub-entity has no body', () => {
    const html = buildSubEntitiesHtml({ entities: [story] });
    expect(html).not.toContain('sq-subentity-body');
  });

  it('closes the body fold by default, with no isOpen predicate given', () => {
    const html = buildSubEntitiesHtml({ entities: [finding] });
    expect(html).not.toContain('data-sq-fold-id="F15" open>');
  });

  it('restores a body fold as open when the isOpen predicate says so, by local id', () => {
    const html = buildSubEntitiesHtml(
      { entities: [finding] },
      undefined,
      undefined,
      (localId) => localId === 'F15',
    );
    expect(html).toContain('data-sq-fold-id="F15" open>');
  });

  it('leaves a fold the predicate reports as closed, closed', () => {
    const html = buildSubEntitiesHtml({ entities: [finding] }, undefined, undefined, () => false);
    expect(html).not.toContain('data-sq-fold-id="F15" open>');
  });

  it('the wrapper section always renders open regardless of the isOpen predicate (unaffected by the regression this fixes)', () => {
    const html = buildSubEntitiesHtml({ entities: [finding] }, undefined, undefined, () => false);
    expect(html).toContain('<details class="sq-graph" open><summary>Sub-entities (1)</summary>');
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

  it('renders a comment on a sub-entity, with author and timestamp, like the item-level section', () => {
    const html = buildSubEntitiesHtml({
      entities: [
        {
          ...finding,
          discussion: [{ author: 'Paul Reviewer', ts: '2026-08-03T09:00:00Z', body: 'Confirmed.' }],
        },
      ],
    });
    expect(html).toContain('Discussion (1)');
    expect(html).toContain('Paul Reviewer');
    expect(html).toContain('2026-08-03T09:00:00Z');
    expect(html).toContain('<p>Confirmed.</p>');
  });

  it('renders no comments block when a sub-entity has an empty discussion array', () => {
    const html = buildSubEntitiesHtml({ entities: [{ ...finding, discussion: [] }] });
    expect(html).not.toContain('Discussion');
  });

  it('renders no comments block when a sub-entity carries no discussion key at all (older sq)', () => {
    const html = buildSubEntitiesHtml({ entities: [finding] });
    expect(html).not.toContain('Discussion');
  });

  it('escapes HTML in a sub-entity comment body rather than interpreting it', () => {
    const html = buildSubEntitiesHtml({
      entities: [
        {
          ...finding,
          discussion: [{ author: 'x', ts: 't', body: '<img src=x onerror=alert(1)>' }],
        },
      ],
    });
    expect(html).not.toContain('<img');
    expect(html).toContain('&lt;img');
  });

  it('escapes HTML in a sub-entity comment author and timestamp', () => {
    const html = buildSubEntitiesHtml({
      entities: [
        {
          ...finding,
          discussion: [{ author: '<b>x</b>', ts: '<i>t</i>', body: 'ok' }],
        },
      ],
    });
    expect(html).not.toContain('<b>x</b>');
    expect(html).not.toContain('<i>t</i>');
    expect(html).toContain('&lt;b&gt;x&lt;/b&gt;');
    expect(html).toContain('&lt;i&gt;t&lt;/i&gt;');
  });

  it('renders multiple sub-entity comments in array order', () => {
    const html = buildSubEntitiesHtml({
      entities: [
        {
          ...finding,
          discussion: [
            { author: 'a', ts: '1', body: 'first' },
            { author: 'b', ts: '2', body: 'second' },
          ],
        },
      ],
    });
    expect(html).toContain('Discussion (2)');
    expect(html.indexOf('first')).toBeLessThan(html.indexOf('second'));
  });

  it("keeps one sub-entity's comments out of another's pane", () => {
    const html = buildSubEntitiesHtml({
      entities: [
        { ...finding, discussion: [{ author: 'a', ts: '1', body: 'finding comment' }] },
        { ...story, discussion: [{ author: 'b', ts: '2', body: 'story comment' }] },
      ],
    });
    // Slice the markup at the second sub-entity's own header rather than comparing positions:
    // an `indexOf`/`toBeLessThan` pair would still pass — vacuously — if comments rendered for
    // neither pane at all (both indexes -1), which is exactly the defect this test must catch.
    const boundary = html.indexOf('<span class="sq-subentity-id">US1</span>');
    expect(boundary).toBeGreaterThan(-1);
    const findingPane = html.slice(0, boundary);
    const storyPane = html.slice(boundary);
    expect(findingPane).toContain('finding comment');
    expect(findingPane).not.toContain('story comment');
    expect(storyPane).toContain('story comment');
    expect(storyPane).not.toContain('finding comment');
  });

  it('closes the discussion fold by default too, with no isOpen predicate given', () => {
    const html = buildSubEntitiesHtml({
      entities: [{ ...finding, discussion: [{ author: 'a', ts: '1', body: 'c' }] }],
    });
    expect(html).toContain('data-sq-fold-id="F15:discussion">');
    expect(html).not.toContain('data-sq-fold-id="F15:discussion" open>');
  });

  it("tracks the comments block under its own fold id, distinct from the sub-entity's local id, so the two can't collide", () => {
    const html = buildSubEntitiesHtml(
      {
        entities: [
          { ...finding, body: 'has a body too', discussion: [{ author: 'a', ts: '1', body: 'c' }] },
        ],
      },
      undefined,
      undefined,
      // Matches only the plain local id — the body's fold id, not the discussion's.
      (foldId) => foldId === 'F15',
    );
    // the body fold is restored open by the predicate; the comments block is tracked under
    // its own, differently-keyed fold id, so it stays closed rather than following the body.
    expect(html).toContain('data-sq-fold-id="F15" open>');
    expect(html).toContain('data-sq-fold-id="F15:discussion">');
    expect(html.match(/data-sq-fold-id/g)).toHaveLength(2);
  });

  it('restores the comments block open when the predicate matches its own fold id, independently of the body', () => {
    const html = buildSubEntitiesHtml(
      {
        entities: [
          { ...finding, body: 'has a body too', discussion: [{ author: 'a', ts: '1', body: 'c' }] },
        ],
      },
      undefined,
      undefined,
      (foldId) => foldId === 'F15:discussion',
    );
    expect(html).toContain('data-sq-fold-id="F15:discussion" open>');
    expect(html).not.toContain('data-sq-fold-id="F15" open>');
  });
});

/**
 * The hover text has to reach every surface the preview renders markdown into, not just the
 * dossier body — a reader hovers an id in a comment or a sub-entity body the same way. One case
 * per surface, each driving the exported builder the preview manager actually calls.
 */
describe('item hover text reaches every rendered surface', () => {
  const items = buildItemDirectory([
    {
      id: 'TASK-452',
      sequence_id: 452,
      type: 'task',
      title: 'Wire the preview',
      slug: 'wire-the-preview',
      status: 'Ready',
      description: '',
      parent: null,
      author: null,
      assignee: null,
      priority: null,
      severity: null,
      labels: [],
      refs: [],
      path: 'tasks/x.md',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  ]);
  const TITLE = 'title="TASK-452 — Wire the preview"';

  it('titles an id in the dossier body', () => {
    const { bodyHtml } = renderOutcomeHtml(
      'REV-1',
      { kind: 'success', data: '# REV-1 — A review\n\n- **status:** Open\n\nSee TASK-452.' },
      undefined,
      undefined,
      items,
    );

    expect(bodyHtml).toContain(TITLE);
  });

  it('titles an id in the dossier’s metadata header (a refs bullet)', () => {
    const { headerHtml } = renderOutcomeHtml(
      'REV-1',
      { kind: 'success', data: '# REV-1 — A review\n\n- **refs:** TASK-452 (addresses)\n\nBody.' },
      undefined,
      undefined,
      items,
    );

    expect(headerHtml).toContain(TITLE);
  });

  it('titles an id in a discussion comment', () => {
    const html = buildDiscussionHtml(
      { entries: [{ author: 'a', ts: '2026-01-01T00:00:00Z', body: 'Fixed under TASK-452.' }] },
      undefined,
      undefined,
      undefined,
      items,
    );

    expect(html).toContain(TITLE);
  });

  it('titles an id in a sub-entity body and in a sub-entity comment', () => {
    const html = buildSubEntitiesHtml(
      {
        entities: [
          {
            local_id: 'F1',
            title: 'A finding',
            status: 'Open',
            assignee: null,
            story: null,
            body: 'Traced to TASK-452.',
            discussion: [{ author: 'a', ts: '2026-01-01T00:00:00Z', body: 'Also TASK-452.' }],
          },
        ],
      },
      undefined,
      undefined,
      undefined,
      {},
      undefined,
      items,
    );

    expect(html.match(new RegExp(TITLE.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'))).toHaveLength(
      2,
    );
  });

  it('renders every surface untitled when the directory is unavailable', () => {
    const html = buildDiscussionHtml({
      entries: [{ author: 'a', ts: '2026-01-01T00:00:00Z', body: 'Fixed under TASK-452.' }],
    });

    expect(html).toContain('data-item-id="TASK-452"');
    expect(html).not.toContain('title=');
  });
});

/**
 * The marker that pairs with the webview gate above: it is what tells the post-render pass a
 * diagram's node ids are item ids. Asserted at both producers, because the guard only holds if
 * exactly one of them claims it.
 */
describe('data-sq-item-nodes marks only the structured item graphs', () => {
  it('both graph sections declare their nodes are items', () => {
    const html = buildGraphsHtml(
      { mermaidSource: 'flowchart TD\n  A[x]' },
      { mermaidSource: 'flowchart TD\n  B[y]' },
    );

    expect(html.match(/data-sq-item-nodes/g)).toHaveLength(2);
  });

  it('a fence-rendered diagram does not, whatever its content', () => {
    const html = renderWorkflowHtml({
      kind: 'success',
      data: '# Cheatsheet\n\n```mermaid\nflowchart TD\n  InProgress[In progress]\n```\n',
    });

    expect(html).toContain('sq-graph-source');
    expect(html).not.toContain('data-sq-item-nodes');
  });

  it('a graph section that failed to fetch renders no source element to stamp at all', () => {
    const html = buildGraphsHtml(
      { mermaidSource: null, message: 'sq tree failed' },
      { mermaidSource: null, message: 'sq graph failed' },
    );

    expect(html).not.toContain('data-sq-item-nodes');
    expect(html).not.toContain('sq-graph-source');
  });

  it('an item body’s own fence is not live-rendered in the first place', () => {
    // The narrower reason the item-preview surfaces were never exposed: they render a
    // ```mermaid``` fence as plain code, so it never becomes a diagram with nodes.
    const { bodyHtml } = renderOutcomeHtml('TASK-1', {
      kind: 'success',
      data: '# TASK-1 — x\n\n- **status:** Ready\n\n```mermaid\nflowchart TD\n  A[x]\n```\n',
    });

    expect(bodyHtml).toContain('<pre><code class="language-mermaid">');
    expect(bodyHtml).not.toContain('sq-graph-source');
  });
});
