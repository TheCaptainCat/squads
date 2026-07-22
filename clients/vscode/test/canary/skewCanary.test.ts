/**
 * Integration skew canary (ADR-427 #3; addresses REV-438 F2).
 *
 * The unit layer (test/*.test.ts) validates parsing logic against committed fixture
 * snapshots (test/fixtures/) with no `sq` binary — fast, hermetic, the bulk of the value.
 * This suite is the other half of that guarantee: it runs a REAL `sq` against a scratch
 * squad and checks that the committed fixtures still describe the live shape of the
 * surfaces the client depends on (ADR-427 #2) — `sq tree --json`, `sq graph --json`,
 * `sq list --json`, `sq show <id> --raw`, `sq workflow types --json`,
 * `sq workflow statuses --json`, `sq workflow roles --json`.
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
 */
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';

import { afterAll, beforeAll, describe, expect, it } from 'vitest';

import {
  isSqCollectionCatalogEntry,
  isSqGraphNode,
  isSqListItem,
  isSqRoleCatalogEntry,
  isSqStatusCatalogEntry,
  isSqTreeNode,
  isSqTypeCatalogEntry,
} from '../../src/sqAdapter';
import type {
  SqCollectionCatalogEntry,
  SqGraphNode,
  SqListItem,
  SqRoleCatalogEntry,
  SqStatusCatalogEntry,
  SqTreeNode,
  SqTypeCatalogEntry,
} from '../../src/types';

interface CreatedItem {
  readonly id: string;
}

function isSqOnPath(): boolean {
  try {
    execFileSync('sq', ['--version'], { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

const SQ_AVAILABLE = isSqOnPath();

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

/** The ADR-427 #2/US2 contract for `sq show --raw`: an H1 title, then a metadata block of
 * bold-key bullets, and none of `sq show`'s default Rich box-drawing chrome. */
function assertCleanMarkdownDossier(text: string): void {
  const lines = text.split('\n');
  expect(lines[0]).toMatch(/^# \S/);
  expect(lines.some((line) => /^- \*\*[\w-]+:\*\* /.test(line))).toBe(true);
  expect(text).not.toMatch(/[─│┌┐└┘├┤┬┴┼╭╮╰╯═║]/);
  expect(text).not.toMatch(/^=== .+ ===$/m);
}

describe.skipIf(!SQ_AVAILABLE)('integration skew canary: live sq vs committed fixtures', () => {
  let scratchDir: string;
  let epicId: string;
  let taskId: string;

  function runSq(args: readonly string[]): string {
    return execFileSync('sq', args, { cwd: scratchDir, encoding: 'utf8' });
  }

  function createItem(args: readonly string[]): string {
    return (JSON.parse(runSq([...args, '--json'])) as CreatedItem).id;
  }

  beforeAll(() => {
    // A throwaway squad, independent of this repo's own — real `sq`, real markdown files,
    // real index, nothing mocked.
    scratchDir = mkdtempSync(path.join(os.tmpdir(), 'squads-vscode-skew-canary-'));
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
    rmSync(scratchDir, { recursive: true, force: true });
  });

  describe('sq tree --json', () => {
    it('every live node has the shape the adapter (and the committed fixture) expect', () => {
      const parsed = JSON.parse(runSq(['tree', epicId, '--json'])) as unknown;
      expect(Array.isArray(parsed)).toBe(true);

      const nodes = flattenTree(parsed as SqTreeNode[]);
      expect(nodes.length).toBeGreaterThanOrEqual(3); // the epic, feature, and task above

      for (const node of nodes) {
        expect(isSqTreeNode(node)).toBe(true);
        expect(Object.keys(node)).toEqual(
          expect.arrayContaining([
            'id',
            'type',
            'title',
            'status',
            'priority',
            'assignee',
            'blocked',
            'badges',
            'children',
          ]),
        );
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
        expect(Object.keys(node)).toEqual(
          expect.arrayContaining([
            'id',
            'type',
            'status',
            'priority',
            'assignee',
            'edge_kind',
            'direction',
            'seen',
            'children',
          ]),
        );
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
      for (const row of rows) {
        expect(isSqListItem(row)).toBe(true);
        expect(Object.keys(row)).toEqual(
          expect.arrayContaining([
            'id',
            'labels',
            'refs',
            'path',
            'created_at',
            'updated_at',
            'badges',
          ]),
        );
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

      const entries = parsed as SqTypeCatalogEntry[];
      // Every declared type, work and reserved alike — at least the bundled defaults
      // (epic/feature/task/bug/decision/review/guide) plus the 3 reserved meta types.
      expect(entries.length).toBeGreaterThanOrEqual(10);
      for (const entry of entries) {
        expect(isSqTypeCatalogEntry(entry)).toBe(true);
        expect(Object.keys(entry)).toEqual(
          expect.arrayContaining(['type', 'order', 'prefix', 'reserved', 'category', 'fields']),
        );
      }
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
          expect.arrayContaining(['role', 'settled', 'hidden', 'color']),
        );
      }
      // "active" (work in flight): not settled, not hidden, a positive colour intent — the join
      // the client uses to colour "work in flight" items, never by the literal status name.
      const active = entries.find((entry) => entry.role === 'active');
      expect(active).toEqual({ role: 'active', settled: false, hidden: false, color: 'positive' });
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
});
