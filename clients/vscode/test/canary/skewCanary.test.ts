/**
 * Integration skew canary (ADR-427 #3; addresses REV-438 F2).
 *
 * The unit layer (test/*.test.ts) validates parsing logic against committed fixture
 * snapshots (test/fixtures/) with no `sq` binary — fast, hermetic, the bulk of the value.
 * This suite is the other half of that guarantee: it runs a REAL `sq` against a scratch
 * squad and checks that the committed fixtures still describe the live shape of the
 * surfaces the client depends on (ADR-427 #2) — `sq tree --json`, `sq graph --json`,
 * `sq list --json`, `sq show <id> --raw`, `sq workflow types --json`,
 * `sq workflow statuses --json`, `sq workflow roles --json`,
 * `sq workflow subentity-kinds --json`.
 *
 * It asserts SHAPE (key set / types / structure), never exact values — a squad's actual
 * items, statuses, and prose legitimately vary between runs and machines. If a core-side
 * change adds/renames/drops a field the client reads, or the `--raw` dossier stops being
 * clean markdown, this is the layer that turns that into a red build instead of silent
 * drift between the two languages.
 *
 * Own layer, own npm script (`npm run test:canary`, see vitest.canary.config.ts) — never
 * run by the plain `npm test`, and vice versa. Skips cleanly (not a failure) when `sq`
 * isn't resolvable on PATH, so a contributor without the Python toolchain still gets a
 * hermetic `npm test`; CI provisions a real `sq` for this lane (see
 * ../../../.github/workflows/vscode-client.yml).
 *
 * `sq` is resolved the way the extension resolves it (`src/discovery.ts`, repo root as the
 * workspace): the repo `.venv` first, then `uv run`, `poetry run`, and bare PATH last. Set
 * `SQ_CANARY_CMD` (a path, a command such as `uv run sq`, or a JSON argv array) to pin a binary
 * on purpose; a pin that does not resolve or answer `--version` fails the suite, never falls
 * through. The suite prints the command it resolved and its `--version`, so a red run names the
 * binary that produced it.
 */
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';

import { afterAll, beforeAll, describe, expect, it } from 'vitest';

import { createNodeDiscoveryEnvironment } from '../../src/nodeEnvironment';
import {
  isSqCollectionCatalogEntry,
  isSqDiscussionEntry,
  isSqGraphNode,
  isSqListItem,
  isSqRoleCatalogEntry,
  isSqRoleListRow,
  isSqRosterIdentity,
  isSqStatusCatalogEntry,
  isSqSubEntityKindCatalogEntry,
  isSqTreeNode,
  isSqTypeCatalogEntry,
} from '../../src/sqAdapter';
import type {
  SqCollectionCatalogEntry,
  SqGraphNode,
  SqListItem,
  SqRoleCatalogEntry,
  SqStatusCatalogEntry,
  SqSubEntityKindCatalogEntry,
  SqTreeNode,
  SqTypeCatalogEntry,
} from '../../src/types';
import { type CanaryInvocation, resolveCanarySq } from './resolveSq';

interface CreatedItem {
  readonly id: string;
}

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..', '..');

const PINNED = (process.env.SQ_CANARY_CMD ?? '').trim() !== '';
const RESOLUTION = resolveCanarySq(
  REPO_ROOT,
  createNodeDiscoveryEnvironment(),
  process.env.SQ_CANARY_CMD,
);
const SQ = RESOLUTION.ok ? RESOLUTION.invocation : undefined;

/** Runs the resolved `sq` from `cwd`. The version probe and the live tests share this, from a
 * directory outside the repo, so the version printed is the binary under test. */
function execSq(sq: CanaryInvocation, args: readonly string[], cwd: string): string {
  return execFileSync(sq.command, [...sq.args, ...args], { cwd, encoding: 'utf8' });
}

function sqVersion(sq: CanaryInvocation): string | undefined {
  try {
    return execSq(sq, ['--version'], os.tmpdir()).trim();
  } catch {
    return undefined;
  }
}

/** True when `sq list --json` succeeds from `cwd`, i.e. `sq` found a squad there. */
function sqSeesASquadFrom(sq: CanaryInvocation, cwd: string): boolean {
  try {
    execSq(sq, ['list', '--json'], cwd);
    return true;
  } catch {
    return false;
  }
}

const SQ_VERSION = SQ === undefined ? undefined : sqVersion(SQ);
const SQ_AVAILABLE = SQ !== undefined && SQ_VERSION !== undefined;

/** A pin is set on purpose, so one that cannot answer fails the suite instead of skipping it. */
const PIN_FAILURE = !PINNED
  ? undefined
  : !RESOLUTION.ok
    ? RESOLUTION.reason
    : SQ_VERSION === undefined
      ? `SQ_CANARY_CMD does not answer --version: ${process.env.SQ_CANARY_CMD ?? ''}`
      : undefined;

if (SQ !== undefined) {
  process.stderr.write(
    `skew canary sq: ${[SQ.command, ...SQ.args].join(' ')} [${SQ.source}] -> ${SQ_VERSION ?? 'not runnable'}\n`,
  );
}

function fixture(name: string): string {
  return readFileSync(path.join(__dirname, '..', 'fixtures', name), 'utf8');
}

/** Every node reachable from `roots`, so shape checks cover the whole tree, not just its
 * top level. */
function flattenTree(roots: readonly SqTreeNode[]): SqTreeNode[] {
  const out: SqTreeNode[] = [];
  const queue: SqTreeNode[] = [...roots];
  for (let node = queue.shift(); node !== undefined; node = queue.shift()) {
    out.push(node);
    queue.push(...node.children);
  }
  return out;
}

/**
 * Every key one `sq tree --json` node carries, as an exact set rather than a floor.
 *
 * A superset assertion (`expect.arrayContaining`) cannot fail on an added key, which makes it
 * useless for the one thing this suite exists to notice: `sq` growing a field the client does
 * not model. A field the client cannot see is not inert — the cycle-anchor flag is the worked
 * example, a root `sq` invented rather than found, which a client that drops it renders as a
 * root somebody wrote. So the set is exact in both directions, and each direction means
 * something specific when it goes red:
 *
 * - an EXTRA key: `sq` emits something the client does not read. Model it (or decide, in
 *   writing, that ignoring it is correct) and add it here.
 * - a MISSING key: `sq` stopped emitting something the client reads, OR — far more often — the
 *   `sq` this suite found on PATH is older than the one being developed against. Check
 *   `sq --version` before believing it, per this file's header.
 *
 * `badges` and `anchor` are optional in the client's own `SqTreeNode` (an older `sq` omits
 * them, and the runtime guard tolerates that rather than rejecting the payload). They are
 * required *here* on purpose: this layer's job is to describe what the current `sq` actually
 * emits, not what the client can survive.
 */
const TREE_NODE_KEYS = [
  'id',
  'type',
  'title',
  'status',
  'assignee',
  'blocked',
  'badges',
  'anchor',
  'children',
  'display',
  'notebook',
  'closed',
  'updated_at',
] as const;

/** Sorted on both sides: key ORDER is not part of the JSON contract, only the key set is.
 * Shared by every exact-key-set assertion below (tree/graph/list) so the three surfaces stay
 * symmetric by construction rather than by three hand-copied `expect` calls drifting apart. */
function assertExactKeys(node: object, expectedKeys: readonly string[]): void {
  expect([...Object.keys(node)].sort()).toEqual([...expectedKeys].sort());
}

function assertExactTreeNodeKeys(node: object): void {
  assertExactKeys(node, TREE_NODE_KEYS);
}

/**
 * Every key one `sq workflow types --json` entry carries, as an exact set. `lifecycle` is
 * required here though the client does not model it, so the decision written in `types.ts`
 * cannot go stale unnoticed.
 */
const TYPE_ENTRY_KEYS = [
  'type',
  'order',
  'prefix',
  'reserved',
  'category',
  'subentity_kind',
  'lifecycle',
  'fields',
  'labels',
  'attributes',
] as const;

/** Same idea as `flattenTree`, for the single-root `sq graph --json` shape. */
function flattenGraph(root: SqGraphNode): SqGraphNode[] {
  const out: SqGraphNode[] = [];
  const queue: SqGraphNode[] = [root];
  for (let node = queue.shift(); node !== undefined; node = queue.shift()) {
    out.push(node);
    queue.push(...node.children);
  }
  return out;
}

/**
 * Every key one `sq graph --json` node carries, as an exact set rather than a floor — same
 * rationale as `TREE_NODE_KEYS` above (a superset assertion cannot fail on an added key, which
 * is the one thing this suite exists to notice).
 *
 * `badges` is genuinely emitted (`GraphNode` gained it as an additive field alongside the other
 * generic-badge-axis surfaces) but is **not** modelled on the client's own `SqGraphNode` — a
 * documented, deliberate choice (`types.ts`'s file-level policy: hand-trimmed to the fields the
 * client actually reads, extra keys ignored rather than rejected), because `domain/graphDiagrams.ts`
 * labels a node from `badges` and `display.badges`; the rest of `display` is unmodelled. It is included here anyway,
 * same as `edge_semantic`, so its removal still reddens this canary even though the shape guard
 * does not check its type.
 */
const GRAPH_NODE_KEYS = [
  'id',
  'type',
  'status',
  'assignee',
  'edge_kind',
  'edge_semantic',
  'direction',
  'seen',
  'badges',
  'children',
  'display',
] as const;

function assertExactGraphNodeKeys(node: object): void {
  assertExactKeys(node, GRAPH_NODE_KEYS);
}

/**
 * The core keys every `sq list --json` row carries, as an exact set rather than a floor — same
 * rationale as `TREE_NODE_KEYS` above.
 *
 * A row is the whole `Item` plus the resolved `badges` map, not a hand-trimmed row — so three of
 * these (`created_session`, `modified_session`, `subentities`) are genuinely emitted but are
 * **not** modelled on the client's own `SqListItem`, per the same `types.ts` hand-trim policy
 * noted on `GRAPH_NODE_KEYS`. They stay in this set anyway, so `sq` dropping one of them still
 * reddens this canary even though the shape guard does not check them.
 *
 * Each attribute a type declares is a flat key beside these, present only when the item stores
 * it; `assertListRowKeys` checks those against the type's `attributes`.
 */
const LIST_ROW_CORE_KEYS = [
  'id',
  'sequence_id',
  'type',
  'title',
  'slug',
  'status',
  'description',
  'parent',
  'author',
  'assignee',
  'labels',
  'refs',
  'path',
  'created_at',
  'updated_at',
  'badges',
  'created_session',
  'modified_session',
  'subentities',
  'display',
] as const;

/** One type's declared attribute names, from `sq workflow types --json`, keyed by type. */
type AttributeNamesByType = ReadonlyMap<string, ReadonlySet<string>>;

function attributeNamesByType(
  entries: readonly { type: string; attributes: object }[],
): AttributeNamesByType {
  return new Map(entries.map((entry) => [entry.type, new Set(Object.keys(entry.attributes))]));
}

/** A row carries exactly the core keys plus, flat, some subset of its type's declared
 * attributes: a key outside both is drift, and so is a retired nested `extra` object. */
function assertListRowKeys(row: object, attributes: AttributeNamesByType): void {
  const keys = Object.keys(row);
  const type = (row as { type: string }).type;
  const declared = attributes.get(type);
  expect(declared, `no declared attributes for type ${type}`).toBeDefined();
  const core: ReadonlySet<string> = new Set(LIST_ROW_CORE_KEYS);
  expect(keys.filter((key) => core.has(key)).sort()).toEqual([...LIST_ROW_CORE_KEYS].sort());
  expect(keys.filter((key) => !core.has(key) && !(declared?.has(key) ?? false))).toEqual([]);
}

/** The ADR-427 #2/US2 contract for `sq show --raw`: an H1 title, then a metadata block of
 * bold-key bullets, and none of `sq show`'s default Rich box-drawing chrome. */
function assertCleanMarkdownDossier(text: string): void {
  const lines = text.split('\n');
  expect(lines[0]).toMatch(/^# \S/);
  expect(lines.some((line) => /^- \*\*[\w-]+:\*\* /.test(line))).toBe(true);
  expect(text).not.toMatch(/[─│┌┐└┘├┤┬┴┼╭╮╰╯═║]/);
  expect(text).not.toMatch(/^=== .+ ===$/m);
}

/**
 * The drift detector's own test. It needs no `sq`, so it runs even where the suite above skips:
 * an assertion nobody has watched fail is an assumption, and this one's whole value is that it
 * bites on a key set that is merely *different*, not malformed — every node below satisfies the
 * runtime shape guard, which is exactly why the guard cannot be what catches drift.
 */
describe('the tree-node key assertion', () => {
  const modelled: Record<string, unknown> = {
    id: 'TASK-1',
    type: 'task',
    title: 'A task',
    status: 'Ready',
    assignee: null,
    blocked: false,
    badges: {},
    anchor: false,
    children: [],
    display: {},
    notebook: null,
    closed: false,
    updated_at: '2026-10-29T00:00:00Z',
  };

  it('accepts exactly the key set the client models', () => {
    expect(isSqTreeNode(modelled)).toBe(true);
    expect(() => {
      assertExactTreeNodeKeys(modelled);
    }).not.toThrow();
  });

  it('fails on a key the client does not model — the drift it exists to catch', () => {
    const withUnmodelledKey = { ...modelled, path_only: false };
    // The shape guard is happy: unknown keys are ignored, not rejected. Nothing else in the
    // client would notice this field either, which is the whole problem.
    expect(isSqTreeNode(withUnmodelledKey)).toBe(true);
    expect(() => {
      assertExactTreeNodeKeys(withUnmodelledKey);
    }).toThrow();
  });

  it('fails when a modelled key stops being emitted, including the anchor flag', () => {
    const { anchor: _anchor, ...withoutAnchor } = modelled;
    expect(isSqTreeNode(withoutAnchor)).toBe(true);
    expect(() => {
      assertExactTreeNodeKeys(withoutAnchor);
    }).toThrow();
  });

  it('does not care about key order', () => {
    const reordered = Object.fromEntries([...Object.entries(modelled)].reverse());
    expect(() => {
      assertExactTreeNodeKeys(reordered);
    }).not.toThrow();
  });
});

/** Same drift-detector self-test as `the tree-node key assertion` above, for the `sq graph
 * --json` surface. */
describe('the graph-node key assertion', () => {
  const modelled: Record<string, unknown> = {
    id: 'TASK-1',
    type: 'task',
    status: 'Ready',
    assignee: null,
    edge_kind: 'related',
    edge_semantic: null,
    direction: 'out',
    seen: false,
    badges: {},
    children: [],
    display: {},
  };

  it('accepts exactly the key set the client models', () => {
    expect(isSqGraphNode(modelled)).toBe(true);
    expect(() => {
      assertExactGraphNodeKeys(modelled);
    }).not.toThrow();
  });

  it('fails on a key the client does not model — the drift it exists to catch', () => {
    const withUnmodelledKey = { ...modelled, path_only: false };
    // The shape guard is happy: unknown keys are ignored, not rejected. Nothing else in the
    // client would notice this field either, which is the whole problem.
    expect(isSqGraphNode(withUnmodelledKey)).toBe(true);
    expect(() => {
      assertExactGraphNodeKeys(withUnmodelledKey);
    }).toThrow();
  });

  it('fails when a modelled key stops being emitted, including badges', () => {
    const { badges: _badges, ...withoutBadges } = modelled;
    expect(isSqGraphNode(withoutBadges)).toBe(true);
    expect(() => {
      assertExactGraphNodeKeys(withoutBadges);
    }).toThrow();
  });

  it('does not care about key order', () => {
    const reordered = Object.fromEntries([...Object.entries(modelled)].reverse());
    expect(() => {
      assertExactGraphNodeKeys(reordered);
    }).not.toThrow();
  });
});

/** Same drift-detector self-test as `the tree-node key assertion` above, for the `sq list
 * --json` surface. */
describe('the list-row key assertion', () => {
  const modelled: Record<string, unknown> = {
    id: 'TASK-1',
    sequence_id: 1,
    type: 'task',
    title: 'A task',
    slug: 'a-task',
    status: 'Ready',
    description: '',
    parent: null,
    author: 'manager',
    assignee: null,
    labels: [],
    refs: [],
    path: 'tasks/TASK-000001-a-task.md',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    badges: {},
    created_session: null,
    modified_session: null,
    subentities: [],
    display: {},
  };
  const attributes: AttributeNamesByType = attributeNamesByType([
    { type: 'task', attributes: {} },
    { type: 'guide', attributes: { tech: {}, tags: {} } },
  ]);
  const { subentities: _subentities, ...withoutSubentities } = modelled;
  const guide = { ...modelled, type: 'guide' };

  const shapes: readonly { name: string; payload: object; passes: boolean }[] = [
    { name: 'the core set', payload: modelled, passes: true },
    {
      name: 'the core set in reverse key order',
      payload: Object.fromEntries([...Object.entries(modelled)].reverse()),
      passes: true,
    },
    { name: 'a declared attribute, flat', payload: { ...guide, tech: 'python' }, passes: true },
    { name: 'every declared attribute', payload: { ...guide, tech: 'a', tags: [] }, passes: true },
    {
      name: 'a key the type does not declare',
      payload: { ...modelled, path_only: false },
      passes: false,
    },
    {
      name: 'a key declared on another type',
      payload: { ...modelled, tech: 'python' },
      passes: false,
    },
    { name: 'the retired nested extra object', payload: { ...modelled, extra: {} }, passes: false },
    { name: 'a core key dropped', payload: withoutSubentities, passes: false },
    {
      name: 'a type with no declared attributes entry',
      payload: { ...modelled, type: 'nope' },
      passes: false,
    },
  ];

  it.each(shapes)('$name', ({ payload, passes }) => {
    // The shape guard is happy with every one of these: unknown keys are ignored, not rejected,
    // and nothing else in the client would notice a stray field, which is the whole problem.
    const run = (): void => {
      assertListRowKeys(payload, attributes);
    };
    if (passes) {
      expect(run).not.toThrow();
    } else {
      expect(run).toThrow();
    }
  });

  it('the shape guard accepts a stray key and an older sq nested extra object', () => {
    expect(isSqListItem({ ...modelled, path_only: false })).toBe(true);
    expect(isSqListItem({ ...modelled, extra: { slug: 'a-task' } })).toBe(true);
  });
});

/** The keys every sub-entity object carries; a stored field of its kind sits flat beside them.
 * `maps_to` is always present (`null` when unset); `story`, `severity` and `extra` are retired
 * as fixed keys. */
const SUBENTITY_CORE_KEYS = [
  'local_id',
  'title',
  'status',
  'assignee',
  'maps_to',
  'deferred_to',
  'body',
  'badges',
  'discussion',
  'display',
] as const;

function assertSubEntityKeys(entry: object, declaredFields: ReadonlySet<string>): void {
  const core: ReadonlySet<string> = new Set(SUBENTITY_CORE_KEYS);
  const keys = Object.keys(entry);
  expect(keys.filter((key) => core.has(key)).sort()).toEqual([...SUBENTITY_CORE_KEYS].sort());
  expect(keys.filter((key) => !core.has(key) && !declaredFields.has(key))).toEqual([]);
}

describe('the sub-entity key assertion', () => {
  const modelled: Record<string, unknown> = {
    local_id: 'AC1',
    title: 't',
    status: 'Todo',
    assignee: null,
    maps_to: null,
    deferred_to: null,
    body: '',
    badges: {},
    discussion: [],
    display: {},
  };
  const fields: ReadonlySet<string> = new Set(['impact']);

  it.each([
    { name: 'the core set', payload: modelled, passes: true },
    { name: 'a declared field, flat', payload: { ...modelled, impact: 'large' }, passes: true },
    { name: 'the retired story key', payload: { ...modelled, story: null }, passes: false },
    { name: 'the retired extra object', payload: { ...modelled, extra: {} }, passes: false },
    { name: 'maps_to dropped', payload: { ...modelled, maps_to: undefined }, passes: false },
  ])('$name', ({ payload, passes }) => {
    const { maps_to: _drop, ...without } = payload;
    const subject = 'maps_to' in payload && payload.maps_to === undefined ? without : payload;
    const run = (): void => {
      assertSubEntityKeys(subject, fields);
    };
    if (passes) {
      expect(run).not.toThrow();
    } else {
      expect(run).toThrow();
    }
  });
});

/** Required here on purpose, `author_slug` included: this layer describes what the current `sq`
 * emits, not what the client's tolerant guard can survive. */
const DISCUSSION_ENTRY_KEYS = [
  'author',
  'author_slug',
  'ts',
  'body',
  'hash',
  'short_hash',
  'edited_ts',
] as const;

function assertDiscussionEntryKeys(entry: object): void {
  assertExactKeys(entry, DISCUSSION_ENTRY_KEYS);
  expect(isSqDiscussionEntry(entry)).toBe(true);
}

describe('the discussion-entry key assertion', () => {
  const base = { author: 'Ada', ts: '2026-01-01T00:00:00Z', body: 'hi' };
  const hashes = { hash: 'a'.repeat(64), short_hash: 'aaaaaaa', edited_ts: null };
  const shapes: readonly { name: string; payload: object; passes: boolean }[] = [
    { name: 'the full set', payload: { ...base, author_slug: 'a', ...hashes }, passes: true },
    { name: 'the hash keys omitted', payload: { ...base, author_slug: 'a' }, passes: false },
    { name: 'author_slug omitted', payload: base, passes: false },
    { name: 'a renamed key', payload: { ...base, slug: 'a' }, passes: false },
    { name: 'a key dropped', payload: { author: 'Ada', ts: base.ts }, passes: false },
    { name: 'an unmodelled key', payload: { ...base, extra: 1 }, passes: false },
    { name: 'a non-string author_slug', payload: { ...base, author_slug: 1 }, passes: false },
  ];

  it.each(shapes)('$name', ({ payload, passes }) => {
    const run = (): void => {
      assertDiscussionEntryKeys(payload);
    };
    if (passes) {
      expect(run).not.toThrow();
    } else {
      expect(run).toThrow();
    }
  });
});

describe('the type-entry key assertion', () => {
  const full: Record<string, unknown> = Object.fromEntries(
    TYPE_ENTRY_KEYS.map((key) => [key, null]),
  );
  const { labels: _labels, ...withoutLabels } = full;
  const { lifecycle: _lifecycle, ...withoutLifecycle } = full;
  const { attributes: _attributes, ...withoutAttributes } = full;
  const { labels: _renamed, ...rest } = full;

  const shapes: readonly { name: string; payload: object; passes: boolean }[] = [
    { name: 'the full set', payload: full, passes: true },
    {
      name: 'the full set in reverse key order',
      payload: Object.fromEntries(Object.entries(full).reverse()),
      passes: true,
    },
    { name: 'labels missing', payload: withoutLabels, passes: false },
    { name: 'lifecycle missing', payload: withoutLifecycle, passes: false },
    { name: 'attributes missing', payload: withoutAttributes, passes: false },
    { name: 'an extra key', payload: { ...full, extra_key: null }, passes: false },
    { name: 'a renamed key', payload: { ...rest, label: null }, passes: false },
  ];

  it.each(shapes)('$name', ({ payload, passes }) => {
    const run = (): void => {
      assertExactKeys(payload, TYPE_ENTRY_KEYS);
    };
    if (passes) {
      expect(run).not.toThrow();
    } else {
      expect(run).toThrow();
    }
  });
});

describe.skipIf(!SQ_AVAILABLE && PIN_FAILURE === undefined)(
  'integration skew canary: live sq vs committed fixtures',
  () => {
    let scratchDir: string | undefined;
    let epicId: string;
    let taskId: string;

    function runSq(args: readonly string[]): string {
      if (SQ === undefined || scratchDir === undefined) {
        throw new Error('sq or the scratch dir is not ready');
      }
      return execSq(SQ, args, scratchDir);
    }

    function createItem(args: readonly string[]): string {
      return (JSON.parse(runSq([...args, '--json'])) as CreatedItem).id;
    }

    beforeAll(() => {
      if (PIN_FAILURE !== undefined) {
        throw new Error(PIN_FAILURE);
      }
      // A throwaway squad, independent of this repo's own — real `sq`, real markdown files,
      // real index, nothing mocked.
      scratchDir = mkdtempSync(path.join(os.tmpdir(), 'squads-vscode-skew-canary-'));
      // Nothing is written before the invocation is proven to run in the scratch dir: it has no
      // squad yet, so a squad found from it means `sq` is running somewhere else.
      if (SQ !== undefined && sqSeesASquadFrom(SQ, scratchDir)) {
        throw new Error('the resolved sq finds a squad from the scratch dir; refusing to write');
      }
      runSq(['init', '--backend', 'none', '--roles', 'minimal', '--default-names']);

      epicId = createItem(['create', 'epic', 'Canary root epic', '--author', 'manager']);
      const featureId = createItem([
        'create',
        'feature',
        'Canary child feature',
        '--author',
        'manager',
        '--parent',
        epicId,
      ]);
      taskId = createItem([
        'create',
        'task',
        'Canary grandchild task',
        '--author',
        'manager',
        '--parent',
        featureId,
      ]);
      runSq(['task', taskId.replace(/^TASK-/, ''), 'body', '-m', 'Canary body paragraph.']);
      // A ref (distinct from the parent/child hierarchy above) so `sq graph` has an edge to
      // traverse, not just a childless root.
      runSq(['task', taskId.replace(/^TASK-/, ''), 'ref', 'add', epicId, '--kind', 'related']);
    });

    afterAll(() => {
      if (scratchDir !== undefined) {
        rmSync(scratchDir, { recursive: true, force: true });
      }
    });

    describe('sq show --json', () => {
      it('every discussion entry, on the item and on a sub-entity, has the keys the client reads', () => {
        runSq([
          'task',
          taskId.replace(/^TASK-/, ''),
          'comment',
          '--as',
          'manager',
          '-m',
          'Canary note.',
        ]);
        const number = taskId.replace(/^TASK-/, '');
        runSq(['task', number, 'add-subtask', 'Canary subtask', '-m', 'Canary subtask body.']);
        runSq(['task', number, 'subtask', '1', 'comment', '--as', 'manager', '-m', 'Sub note.']);
        const parsed = JSON.parse(runSq(['show', taskId, '--json'])) as {
          discussion: object[];
          subentities: { discussion: object[]; maps_to: string | null; display: object }[];
        };
        expect(parsed.discussion.length).toBeGreaterThan(0);
        for (const entry of parsed.discussion) {
          assertDiscussionEntryKeys(entry);
        }
        expect(parsed.subentities.length).toBeGreaterThan(0);
        for (const sub of parsed.subentities) {
          assertSubEntityKeys(sub, new Set());
          expect(sub).toHaveProperty('maps_to');
          // The target kind the mapping line is labelled by: an object (the kind maps) or null.
          expect(sub.display).toHaveProperty('maps_to_kind');
          expect(sub.discussion.length).toBeGreaterThan(0);
          for (const entry of sub.discussion) {
            assertDiscussionEntryKeys(entry);
          }
        }
      });

      it('the committed fixture still conforms to the shape the adapter accepts', () => {
        const parsed = JSON.parse(fixture('show-json.json')) as { discussion: unknown[] };
        expect(parsed.discussion.length).toBeGreaterThan(0);
        for (const entry of parsed.discussion) {
          expect(isSqDiscussionEntry(entry)).toBe(true);
        }
      });
    });

    describe('sq tree --json', () => {
      it('every live node has the shape the adapter (and the committed fixture) expect', () => {
        const parsed = JSON.parse(runSq(['tree', epicId, '--json'])) as unknown;
        expect(Array.isArray(parsed)).toBe(true);

        const nodes = flattenTree(parsed as SqTreeNode[]);
        expect(nodes.length).toBeGreaterThanOrEqual(3); // the epic, feature, and task above

        for (const node of nodes) {
          expect(isSqTreeNode(node)).toBe(true);
          assertExactTreeNodeKeys(node);
          // `is_open` no longer exists on any surface — a client re-derives it from the
          // referenced role's `settled`, joined through the statuses/roles catalogs.
          expect(node).not.toHaveProperty('is_open');
        }
      });

      it('the committed fixture still conforms to the shape the adapter accepts', () => {
        const parsed = JSON.parse(fixture('tree.json')) as unknown;
        const nodes = flattenTree(parsed as SqTreeNode[]);
        expect(nodes.length).toBeGreaterThan(0);
        for (const node of nodes) {
          expect(isSqTreeNode(node)).toBe(true);
        }
      });
    });

    describe('sq graph --json', () => {
      it('every live node has the shape the adapter (and the committed fixture) expect', () => {
        const parsed = JSON.parse(runSq(['graph', taskId, '--json', '--all'])) as unknown;
        expect(isSqGraphNode(parsed)).toBe(true);

        const nodes = flattenGraph(parsed as SqGraphNode);
        expect(nodes.length).toBeGreaterThanOrEqual(2); // the task root, plus the epic it refs

        for (const node of nodes) {
          expect(isSqGraphNode(node)).toBe(true);
          assertExactGraphNodeKeys(node);
        }
      });

      it('the committed fixture still conforms to the shape the adapter accepts', () => {
        const root = JSON.parse(fixture('graph.json')) as unknown;
        expect(isSqGraphNode(root)).toBe(true);
        for (const node of flattenGraph(root as SqGraphNode)) {
          expect(isSqGraphNode(node)).toBe(true);
        }
      });
    });

    describe('sq list --json', () => {
      it('every live row has the shape the adapter (and the committed fixture) expect', () => {
        const parsed = JSON.parse(runSq(['list', '--json'])) as unknown;
        expect(Array.isArray(parsed)).toBe(true);

        const rows = parsed as SqListItem[];
        expect(rows.length).toBeGreaterThan(0);
        const types = JSON.parse(runSq(['workflow', 'types', '--json'])) as {
          type: string;
          attributes: object;
        }[];
        const attributes = attributeNamesByType(types);
        for (const row of rows) {
          expect(isSqListItem(row)).toBe(true);
          assertListRowKeys(row, attributes);
          // See the `sq tree --json` case above — same removal, same reason.
          expect(row).not.toHaveProperty('is_open');
        }
      });

      it('the committed fixture still conforms to the shape the adapter accepts', () => {
        const rows = JSON.parse(fixture('list.json')) as unknown[];
        expect(rows.length).toBeGreaterThan(0);
        for (const row of rows) {
          expect(isSqListItem(row)).toBe(true);
        }
      });
    });

    describe('sq workflow types --json', () => {
      it('every live entry has the shape the adapter (and the committed fixture) expect', () => {
        const parsed = JSON.parse(runSq(['workflow', 'types', '--json'])) as unknown;
        expect(Array.isArray(parsed)).toBe(true);

        const entries = parsed as (SqTypeCatalogEntry & { attributes: Record<string, object> })[];
        // Every declared type, work and reserved alike — at least the bundled defaults
        // (epic/feature/task/bug/decision/review/guide) plus the 3 reserved meta types.
        expect(entries.length).toBeGreaterThanOrEqual(10);
        for (const entry of entries) {
          expect(isSqTypeCatalogEntry(entry)).toBe(true);
          assertExactKeys(entry, TYPE_ENTRY_KEYS);
          // Each attribute is `{kind, label, required, settable}`; the row assertion joins on the names.
          for (const attribute of Object.values(entry.attributes)) {
            assertExactKeys(attribute, ['kind', 'label', 'required', 'settable']);
          }
        }
        expect(entries.some((entry) => Object.keys(entry.attributes).length > 0)).toBe(true);
        // Present on every row, `null` where the type hosts no kind — the client joins on it and
        // an omitted key would silently degrade every sub-entity badge to its raw field code.
        expect(entries.every((entry) => entry.subentity_kind !== undefined)).toBe(true);
        expect(entries.some((entry) => entry.subentity_kind === null)).toBe(true);
        // Emitted in ascending resolved order, so the client's group-by-type sort can trust it
        // directly rather than re-deriving anything.
        const orders = entries.map((entry) => entry.order).filter((order) => order !== null);
        expect(orders).toEqual([...orders].sort((a, b) => a - b));
        expect(entries.some((entry) => entry.reserved)).toBe(true);
        // Every reserved type is `roster`-category; a work type not otherwise
        // records-category (e.g. `task`) is `work` — the join `domain/typeCategory.ts` relies on.
        expect(entries.find((entry) => entry.type === 'task')?.category).toBe('work');
        expect(
          entries.filter((entry) => entry.reserved).every((entry) => entry.category === 'roster'),
        ).toBe(true);
        // The bug type's `fields` binds both its priority and severity codes to a collection
        // (F19/F20's field->collection join) — a real, non-empty example, not just an empty array.
        //
        // `arrayContaining` here is a deliberate floor, not the same hole the key-set assertions
        // above close: `fields` is a project's own declared field->collection bindings, an
        // array whose LENGTH is genuinely open (a custom axis adds another entry) — unlike an
        // object's key set, which is fixed by the schema the payload was built from. Each named
        // entry is still checked for its exact three-key shape (`{code, label, collection}`,
        // `FIELD_ENTRY_FIELDS` on the core side) via `toEqual`'s own equality, so this is a floor
        // on which entries exist, never on what one entry itself carries.
        const bug = entries.find((entry) => entry.type === 'bug');
        expect(bug?.fields).toEqual(
          expect.arrayContaining([
            { code: 'priority', label: 'Priority', collection: 'priority' },
            { code: 'severity', label: 'Severity', collection: 'severity' },
          ]),
        );
      });

      it('the committed fixture still conforms to the shape the adapter accepts', () => {
        const entries = JSON.parse(fixture('type-catalog.json')) as unknown[];
        expect(entries.length).toBeGreaterThan(0);
        for (const entry of entries) {
          expect(isSqTypeCatalogEntry(entry)).toBe(true);
        }
      });
    });

    describe('sq workflow collections --json', () => {
      it('every live entry has the shape the adapter (and the committed fixture) expect', () => {
        const parsed = JSON.parse(runSq(['workflow', 'collections', '--json'])) as unknown;
        expect(Array.isArray(parsed)).toBe(true);

        const entries = parsed as SqCollectionCatalogEntry[];
        // At least the two bundled collections (priority, severity).
        expect(entries.length).toBeGreaterThanOrEqual(2);
        for (const entry of entries) {
          expect(isSqCollectionCatalogEntry(entry)).toBe(true);
          expect(Object.keys(entry)).toEqual(
            expect.arrayContaining(['collection', 'label', 'ordered', 'default', 'badges']),
          );
          expect(entry.badges.length).toBeGreaterThan(0);
        }
        expect(entries.some((entry) => entry.collection === 'priority')).toBe(true);
        expect(entries.some((entry) => entry.collection === 'severity')).toBe(true);
      });

      it('the committed fixture still conforms to the shape the adapter accepts', () => {
        const entries = JSON.parse(fixture('collections-catalog.json')) as unknown[];
        expect(entries.length).toBeGreaterThan(0);
        for (const entry of entries) {
          expect(isSqCollectionCatalogEntry(entry)).toBe(true);
        }
      });
    });

    describe('sq workflow statuses --json', () => {
      it('every live entry has the shape the adapter (and the committed fixture) expect', () => {
        const parsed = JSON.parse(runSq(['workflow', 'statuses', '--json'])) as unknown;
        expect(Array.isArray(parsed)).toBe(true);

        const entries = parsed as SqStatusCatalogEntry[];
        expect(entries.length).toBeGreaterThan(0);
        for (const entry of entries) {
          expect(isSqStatusCatalogEntry(entry)).toBe(true);
          expect(Object.keys(entry)).toEqual(expect.arrayContaining(['status', 'role', 'badge']));
          // `terminal` no longer exists — a client re-derives it from the referenced
          // role's `settled` via `sq workflow roles --json`.
          expect(entry).not.toHaveProperty('terminal');
        }
        // InProgress carries the "active" semantic role — the join the client uses to color "work
        // in flight" items, never by the literal status name.
        const inProgress = entries.find((entry) => entry.status === 'InProgress');
        expect(inProgress?.role).toBe('active');
      });

      it('the committed fixture still conforms to the shape the adapter accepts', () => {
        const entries = JSON.parse(fixture('statuses-catalog.json')) as unknown[];
        expect(entries.length).toBeGreaterThan(0);
        for (const entry of entries) {
          expect(isSqStatusCatalogEntry(entry)).toBe(true);
        }
      });
    });

    describe('sq workflow subentity-kinds --json', () => {
      it('every live entry has the shape the adapter (and the committed fixture) expect', () => {
        const parsed = JSON.parse(runSq(['workflow', 'subentity-kinds', '--json'])) as unknown;
        expect(Array.isArray(parsed)).toBe(true);

        const entries = parsed as SqSubEntityKindCatalogEntry[];
        // At least the 3 bundled kinds (story, subtask, finding).
        expect(entries.length).toBeGreaterThanOrEqual(3);
        for (const entry of entries) {
          expect(isSqSubEntityKindCatalogEntry(entry)).toBe(true);
          expect(Object.keys(entry)).toEqual(
            expect.arrayContaining([
              'subentity_kind',
              'lifecycle',
              'plural',
              'local_prefix',
              'container_heading',
              'completion',
              'label',
              'maps_to_parent',
              'fields',
            ]),
          );
        }
        // The finding kind's declared axis, a real non-empty example of the entry shape the
        // client reads — and the same `{code, label, collection}` shape a type row's own
        // `fields` carries, which is what lets one resolver serve both levels.
        //
        // Same deliberate floor as the type catalog's `bug.fields` check above, for the same
        // reason: a sub-entity kind's `fields` array length is open by declaration, not a fixed
        // object key set.
        const finding = entries.find((entry) => entry.subentity_kind === 'finding');
        expect(finding?.fields).toEqual(
          expect.arrayContaining([{ code: 'severity', label: 'Severity', collection: 'severity' }]),
        );
      });

      it('the type catalog’s subentity_kind resolves to a row in this catalog', () => {
        // The join itself, live: every non-null `subentity_kind` on a type row names a kind the
        // kind catalog publishes. A rename on either side that broke this would leave the
        // preview labelling sub-entity badges by their raw field code with nothing failing.
        const types = JSON.parse(runSq(['workflow', 'types', '--json'])) as SqTypeCatalogEntry[];
        const kinds = JSON.parse(
          runSq(['workflow', 'subentity-kinds', '--json']),
        ) as SqSubEntityKindCatalogEntry[];
        const declared = new Set(kinds.map((entry) => entry.subentity_kind));
        const hosted = types
          .map((entry) => entry.subentity_kind)
          .filter((kind): kind is string => typeof kind === 'string');

        expect(hosted.length).toBeGreaterThan(0);
        expect(hosted.every((kind) => declared.has(kind))).toBe(true);
      });

      it('the committed fixture still conforms to the shape the adapter accepts', () => {
        const entries = JSON.parse(fixture('subentity-kinds-catalog.json')) as unknown[];
        expect(entries.length).toBeGreaterThan(0);
        for (const entry of entries) {
          expect(isSqSubEntityKindCatalogEntry(entry)).toBe(true);
        }
      });
    });

    describe('sq workflow roles --json', () => {
      it('every live entry has the shape the adapter (and the committed fixture) expect', () => {
        const parsed = JSON.parse(runSq(['workflow', 'roles', '--json'])) as unknown;
        expect(Array.isArray(parsed)).toBe(true);

        const entries = parsed as SqRoleCatalogEntry[];
        // At least the 8 bundled roles.
        expect(entries.length).toBeGreaterThanOrEqual(8);
        for (const entry of entries) {
          expect(isSqRoleCatalogEntry(entry)).toBe(true);
          expect(Object.keys(entry)).toEqual(
            expect.arrayContaining(['role', 'settled', 'hidden', 'color', 'live', 'blocked']),
          );
        }
        // "active" (work in flight): not settled, not hidden, a positive colour intent, and the
        // one bundled role on offer — the join the client uses to colour "work in flight" items,
        // never by the literal status name.
        const active = entries.find((entry) => entry.role === 'active');
        expect(active).toEqual({
          role: 'active',
          settled: false,
          hidden: false,
          color: 'positive',
          live: true,
          blocked: false,
          deferred: false,
        });
        // Required here on purpose: the canary describes what the current `sq` emits, while the
        // client guard tolerates an older `sq` that omits the key.
        expect(entries.find((entry) => entry.role === 'blocked')?.blocked).toBe(true);
        // "in_force" (a settled record that stays visible, e.g. Accepted/Published) is the
        // case distinguishing it from "done" (settled AND hidden).
        const inForce = entries.find((entry) => entry.role === 'in_force');
        expect(inForce?.settled).toBe(true);
        expect(inForce?.hidden).toBe(false);
      });

      it('the committed fixture still conforms to the shape the adapter accepts', () => {
        const entries = JSON.parse(fixture('roles-catalog.json')) as unknown[];
        expect(entries.length).toBeGreaterThan(0);
        for (const entry of entries) {
          expect(isSqRoleCatalogEntry(entry)).toBe(true);
        }
      });
    });

    describe('roster identities (role and operator lists)', () => {
      const ROLE_LIST_KEYS = [
        'id',
        'slug',
        'full_name',
        'pronouns',
        'title',
        'description',
        'is_default',
        'capabilities',
        'status',
        'origin',
        'display',
      ];
      const OPERATOR_LIST_KEYS = ['id', 'slug', 'full_name', 'pronouns', 'status', 'display'];

      it('role and operator list rows carry pronouns (null when unset) and the adapter guard accepts them', () => {
        runSq(['role', 'manager', 'update', '--pronouns', 'she/her']);
        runSq(['operator', 'add', 'Canary Person', '--slug', 'op-canary']);

        const roles = JSON.parse(runSq(['role', 'list', '--json'])) as Record<string, unknown>[];
        expect(roles.length).toBeGreaterThan(0);
        for (const row of roles) {
          expect(Object.keys(row).sort()).toEqual([...ROLE_LIST_KEYS].sort());
          expect(isSqRoleListRow(row)).toBe(true);
        }
        expect(roles.find((row) => row.slug === 'manager')?.pronouns).toBe('she/her');
        // The hover reads the resolved description: non-empty on a catalog, a template and an
        // item-defined role.
        runSq(['dev', 'add', '--tech', 'python']);
        runSq([
          'role',
          'add',
          'release-captain',
          '--name',
          'Rhea Captain',
          '--job-title',
          'Release captain',
          '--desc',
          'Cuts the release.',
          '--mission',
          'Cut the release.',
        ]);
        const described = JSON.parse(runSq(['role', 'list', '--json'])) as Record<
          string,
          unknown
        >[];
        expect(described.map((row) => row.slug)).toEqual(
          expect.arrayContaining(['manager', 'python-dev', 'release-captain']),
        );
        for (const row of described) {
          expect(row.description).toEqual(expect.stringMatching(/\S/));
        }

        const operators = JSON.parse(runSq(['operator', 'list', '--json'])) as Record<
          string,
          unknown
        >[];
        expect(operators.length).toBeGreaterThan(0);
        for (const row of operators) {
          expect(Object.keys(row).sort()).toEqual([...OPERATOR_LIST_KEYS].sort());
          expect(isSqRosterIdentity(row)).toBe(true);
        }
        expect(operators.find((row) => row.slug === 'op-canary')?.pronouns).toBeNull();
      });
    });

    describe('sq show <id> --raw', () => {
      it('the live dossier is clean markdown with no Rich box chrome', () => {
        const stdout = runSq(['show', taskId, '--raw']);
        assertCleanMarkdownDossier(stdout);
        expect(stdout).toContain(`# ${taskId} —`);
      });

      it('the committed fixture still conforms to the clean-markdown contract', () => {
        assertCleanMarkdownDossier(fixture('show-raw.txt'));
      });
    });
  },
);
