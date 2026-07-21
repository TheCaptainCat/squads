/**
 * Thin adapter over `sq --json`: shells out via the resolved invocation, parses stdout as
 * the frozen JSON shapes, and maps the exit code per the documented contract.
 *
 * The adapter pins **no** schema knowledge of its own — a version/schema-skew failure is a
 * ordinary non-zero exit whose stderr is surfaced verbatim, exactly like any other runtime
 * error. Turning an outcome into a VS Code notification is the caller's job (kept out of
 * this module so it stays unit-testable with no `sq` binary and no VS Code host).
 */

import type { SqInvocation } from './discovery';
import type { ProcessRunner } from './processRunner';
import type {
  SqBadgeMap,
  SqCollectionBadge,
  SqCollectionCatalogEntry,
  SqDiscussionEntry,
  SqGraphNode,
  SqListItem,
  SqSearchHit,
  SqSearchHitRegion,
  SqShowJson,
  SqStatusCatalogEntry,
  SqSubEntity,
  SqTreeNode,
  SqTypeCatalogEntry,
  SqTypeField,
} from './types';

export type SqOutcome<T> =
  | { readonly kind: 'success'; readonly data: T }
  | {
      readonly kind: 'usage-error';
      readonly message: string;
      /** The full, runnable command line (resolved command + every arg) that was spawned. */
      readonly argv: readonly string[];
    }
  | { readonly kind: 'check-error'; readonly message: string }
  | { readonly kind: 'runtime-error'; readonly message: string; readonly exitCode: number }
  | { readonly kind: 'parse-error'; readonly message: string }
  | { readonly kind: 'spawn-error'; readonly message: string };

/** Human-readable message for any non-success outcome, for notifications/error nodes. Usage
 * errors additionally carry the replayable command line so it can be logged/reported. */
export function describeFailure(outcome: Exclude<SqOutcome<unknown>, { kind: 'success' }>): string {
  switch (outcome.kind) {
    case 'usage-error':
      return `${outcome.message} (command: ${outcome.argv.join(' ')})`;
    case 'check-error':
    case 'runtime-error':
    case 'parse-error':
    case 'spawn-error':
      return outcome.message;
  }
}

/** Full argv (invocation prefix + subcommand args) `sq` would be run with. */
export function buildArgv(invocation: SqInvocation, subcommandArgs: readonly string[]): string[] {
  return [...invocation.args, ...subcommandArgs];
}

function classifyNonZeroExit(
  exitCode: number,
  stderr: string,
  fullCommand: readonly string[],
): SqOutcome<never> {
  const message = stderr.trim();
  if (exitCode === 2) {
    return { kind: 'usage-error', message, argv: fullCommand };
  }
  if (exitCode === 3) {
    return { kind: 'check-error', message };
  }
  // 1, or anything else (including a schema-skew hard-stop) — surfaced verbatim, no
  // special-casing: the adapter doesn't try to interpret it.
  return { kind: 'runtime-error', message, exitCode };
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((entry) => typeof entry === 'string');
}

/** `badges` is optional on every item-bearing surface — absent (an older `sq`)
 * is valid, same as present-and-empty; present-and-non-object is not. */
function isOptionalBadgeMap(value: unknown): value is SqBadgeMap | undefined {
  if (value === undefined) {
    return true;
  }
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return false;
  }
  return Object.values(value).every((entry) => typeof entry === 'string');
}

function hasRequiredTreeNodeStrings(node: Record<string, unknown>): boolean {
  return (
    typeof node.id === 'string' &&
    typeof node.type === 'string' &&
    typeof node.title === 'string' &&
    typeof node.status === 'string' &&
    typeof node.blocked === 'boolean' &&
    typeof node.is_open === 'boolean' &&
    isOptionalBadgeMap(node.badges)
  );
}

function hasNullableTreeNodeStrings(node: Record<string, unknown>): boolean {
  return (
    (typeof node.priority === 'string' || node.priority === null) &&
    (typeof node.assignee === 'string' || node.assignee === null)
  );
}

/** Shape guard for one `sq tree --json` node (recursive). Exported so the integration
 * skew-canary test can validate live `sq` output with the exact same predicate the
 * adapter uses at runtime, rather than a parallel hand-rolled check that could itself
 * drift from what this module actually accepts. */
export function isSqTreeNode(value: unknown): value is SqTreeNode {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const node = value as Record<string, unknown>;
  return (
    hasRequiredTreeNodeStrings(node) &&
    hasNullableTreeNodeStrings(node) &&
    Array.isArray(node.children) &&
    node.children.every(isSqTreeNode)
  );
}

function hasRequiredGraphNodeStrings(node: Record<string, unknown>): boolean {
  return (
    typeof node.id === 'string' &&
    typeof node.type === 'string' &&
    typeof node.status === 'string' &&
    typeof node.seen === 'boolean'
  );
}

function hasNullableGraphNodeFields(node: Record<string, unknown>): boolean {
  return (
    (typeof node.priority === 'string' || node.priority === null) &&
    (typeof node.assignee === 'string' || node.assignee === null) &&
    (typeof node.edge_kind === 'string' || node.edge_kind === null) &&
    (node.direction === 'in' || node.direction === 'out' || node.direction === null)
  );
}

/** Shape guard for one `sq graph <id> --json` node (recursive). Exported for the same reason
 * as `isSqTreeNode` — the skew canary reuses the real adapter predicate. */
export function isSqGraphNode(value: unknown): value is SqGraphNode {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const node = value as Record<string, unknown>;
  return (
    hasRequiredGraphNodeStrings(node) &&
    hasNullableGraphNodeFields(node) &&
    Array.isArray(node.children) &&
    node.children.every(isSqGraphNode)
  );
}

function hasRequiredListItemStrings(item: Record<string, unknown>): boolean {
  return (
    typeof item.id === 'string' &&
    typeof item.sequence_id === 'number' &&
    typeof item.type === 'string' &&
    typeof item.title === 'string' &&
    typeof item.status === 'string' &&
    typeof item.path === 'string' &&
    typeof item.created_at === 'string' &&
    typeof item.updated_at === 'string' &&
    typeof item.is_open === 'boolean' &&
    isOptionalBadgeMap(item.badges)
  );
}

function hasNullableListItemStrings(item: Record<string, unknown>): boolean {
  return (
    (typeof item.parent === 'string' || item.parent === null) &&
    (typeof item.assignee === 'string' || item.assignee === null)
  );
}

/** Shape guard for one `sq list --json` row. Exported for the same reason as
 * `isSqTreeNode` — the skew canary reuses the real adapter predicate. */
export function isSqListItem(value: unknown): value is SqListItem {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const item = value as Record<string, unknown>;
  return (
    hasRequiredListItemStrings(item) &&
    hasNullableListItemStrings(item) &&
    isStringArray(item.labels) &&
    isStringArray(item.refs)
  );
}

function isSqSearchHitRegion(value: unknown): value is SqSearchHitRegion {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const region = value as Record<string, unknown>;
  return (
    typeof region.region === 'string' &&
    typeof region.location === 'string' &&
    typeof region.snippet === 'string'
  );
}

/** Shape guard for one `sq search <text> --json` row. Exported for the same reason as
 * `isSqTreeNode` — the skew canary reuses the real adapter predicate. */
export function isSqSearchHit(value: unknown): value is SqSearchHit {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const hit = value as Record<string, unknown>;
  return (
    typeof hit.id === 'string' &&
    typeof hit.title === 'string' &&
    typeof hit.type === 'string' &&
    typeof hit.status === 'string' &&
    Array.isArray(hit.hits) &&
    hit.hits.every(isSqSearchHitRegion)
  );
}

function isSqTypeField(value: unknown): value is SqTypeField {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const field = value as Record<string, unknown>;
  return (
    typeof field.code === 'string' &&
    typeof field.label === 'string' &&
    typeof field.collection === 'string'
  );
}

/** `fields` is optional the same way `badges` is — an older `sq` omits it,
 * treated the same as an empty (no field->collection binding known) array. */
function isOptionalTypeFieldArray(value: unknown): value is readonly SqTypeField[] | undefined {
  return value === undefined || (Array.isArray(value) && value.every(isSqTypeField));
}

/** Shape guard for one `sq workflow types --json` entry. Exported for the same reason as
 * `isSqTreeNode` — the skew canary reuses the real adapter predicate. */
export function isSqTypeCatalogEntry(value: unknown): value is SqTypeCatalogEntry {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const entry = value as Record<string, unknown>;
  return (
    typeof entry.type === 'string' &&
    (typeof entry.order === 'number' || entry.order === null) &&
    typeof entry.prefix === 'string' &&
    typeof entry.reserved === 'boolean' &&
    isOptionalTypeFieldArray(entry.fields)
  );
}

function isSqCollectionBadge(value: unknown): value is SqCollectionBadge {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const badge = value as Record<string, unknown>;
  return (
    typeof badge.code === 'string' &&
    typeof badge.label === 'string' &&
    typeof badge.emoji === 'string'
  );
}

/** Shape guard for one `sq workflow collections --json` entry . Exported for
 * the same reason as `isSqTreeNode` — the skew canary reuses the real adapter predicate. */
export function isSqCollectionCatalogEntry(value: unknown): value is SqCollectionCatalogEntry {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const entry = value as Record<string, unknown>;
  return (
    typeof entry.collection === 'string' &&
    typeof entry.label === 'string' &&
    typeof entry.ordered === 'boolean' &&
    (typeof entry.default === 'string' || entry.default === null) &&
    Array.isArray(entry.badges) &&
    entry.badges.every(isSqCollectionBadge)
  );
}

/** Shape guard for one `sq workflow statuses --json` entry . Exported for the
 * same reason as `isSqTreeNode` — the skew canary reuses the real adapter predicate. */
export function isSqStatusCatalogEntry(value: unknown): value is SqStatusCatalogEntry {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const entry = value as Record<string, unknown>;
  return (
    typeof entry.status === 'string' &&
    typeof entry.terminal === 'boolean' &&
    (typeof entry.role === 'string' || entry.role === null) &&
    (typeof entry.badge === 'string' || entry.badge === null)
  );
}

function isSqDiscussionEntry(value: unknown): value is SqDiscussionEntry {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const entry = value as Record<string, unknown>;
  return (
    typeof entry.author === 'string' &&
    typeof entry.ts === 'string' &&
    typeof entry.body === 'string'
  );
}

function isSqSubEntity(value: unknown): value is SqSubEntity {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const entry = value as Record<string, unknown>;
  return (
    typeof entry.local_id === 'string' &&
    typeof entry.title === 'string' &&
    typeof entry.status === 'string' &&
    (typeof entry.assignee === 'string' || entry.assignee === null) &&
    (typeof entry.severity === 'string' || entry.severity === null) &&
    (typeof entry.story === 'string' || entry.story === null) &&
    typeof entry.body === 'string'
  );
}

/** Shape guard for `sq show <id> --json`. Only checks the two keys this client reads
 * (`discussion`, `subentities`) — every other field `sq show --json` emits is ignored, per
 * `SqShowJson`'s hand-trimmed contract. */
export function isSqShowJson(value: unknown): value is SqShowJson {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const obj = value as Record<string, unknown>;
  return (
    Array.isArray(obj.discussion) &&
    obj.discussion.every(isSqDiscussionEntry) &&
    Array.isArray(obj.subentities) &&
    obj.subentities.every(isSqSubEntity)
  );
}

function parseJson(stdout: string): SqOutcome<unknown> {
  try {
    return { kind: 'success', data: JSON.parse(stdout) as unknown };
  } catch (error) {
    return { kind: 'parse-error', message: error instanceof Error ? error.message : String(error) };
  }
}

/** Runs one `sq` subcommand and returns its raw stdout on a zero exit — the shared plumbing
 * behind every adapter call (`getRaw`'s plain text and every `--json` parser below). */
async function runSqRaw(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
  subcommandArgs: readonly string[],
): Promise<SqOutcome<string>> {
  const argv = buildArgv(invocation, subcommandArgs);
  let result;
  try {
    result = await runner.run(invocation.command, argv, workspaceRoot);
  } catch (error) {
    return { kind: 'spawn-error', message: error instanceof Error ? error.message : String(error) };
  }
  if (result.exitCode !== 0) {
    return classifyNonZeroExit(result.exitCode, result.stderr, [invocation.command, ...argv]);
  }
  return { kind: 'success', data: result.stdout };
}

async function runSqJson<T>(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
  subcommandArgs: readonly string[],
  isItem: (value: unknown) => value is T,
): Promise<SqOutcome<T[]>> {
  const raw = await runSqRaw(runner, invocation, workspaceRoot, subcommandArgs);
  if (raw.kind !== 'success') {
    return raw;
  }
  const parsed = parseJson(raw.data);
  if (parsed.kind !== 'success') {
    return parsed;
  }
  if (!Array.isArray(parsed.data) || !parsed.data.every(isItem)) {
    return { kind: 'parse-error', message: 'sq --json output did not match the expected shape' };
  }
  return { kind: 'success', data: parsed.data };
}

/** Same as `runSqJson`, for a `--json` surface that emits a single nested object (`sq graph`)
 * rather than a top-level array (`sq tree`/`sq list`). */
async function runSqJsonObject<T>(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
  subcommandArgs: readonly string[],
  isItem: (value: unknown) => value is T,
): Promise<SqOutcome<T>> {
  const raw = await runSqRaw(runner, invocation, workspaceRoot, subcommandArgs);
  if (raw.kind !== 'success') {
    return raw;
  }
  const parsed = parseJson(raw.data);
  if (parsed.kind !== 'success') {
    return parsed;
  }
  if (!isItem(parsed.data)) {
    return { kind: 'parse-error', message: 'sq --json output did not match the expected shape' };
  }
  return { kind: 'success', data: parsed.data };
}

/** `sq tree [<root>] --json [--all]` — drives the sidebar tree. `includeClosed` (the
 * show-closed view-title toggle) appends `--all` so closed/terminal items are fetched too;
 * omitted (the default), `sq tree` hides them the same way it does from the terminal. */
export function getTree(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
  root?: string,
  includeClosed = false,
): Promise<SqOutcome<SqTreeNode[]>> {
  const args = ['tree'];
  if (root !== undefined) {
    args.push(root);
  }
  args.push('--json');
  if (includeClosed) {
    args.push('--all');
  }
  return runSqJson(runner, invocation, workspaceRoot, args, isSqTreeNode);
}

/** `sq list --json [filters...]` — feeds the flat/filtered/grouped views. */
export function getList(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
  filterArgs: readonly string[] = [],
): Promise<SqOutcome<SqListItem[]>> {
  return runSqJson(
    runner,
    invocation,
    workspaceRoot,
    ['list', ...filterArgs, '--json'],
    isSqListItem,
  );
}

/** `sq search <text> --json [--type/--status …]` — the full-text search QuickPick's only data
 * source (read-only consumer of the same engine the TUI search page uses; no new search
 * capability lives here). `filterArgs` is appended between `text` and `--json` so a caller can
 * layer `--type <type>`/`--status <status>` through unchanged, AND-composed with the query text
 * exactly as `sq search` composes them server-side — this adapter never re-matches or
 * post-filters the rows it gets back. A zero-match query is a success with an empty array, not
 * an error. */
export function getSearch(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
  text: string,
  filterArgs: readonly string[] = [],
): Promise<SqOutcome<SqSearchHit[]>> {
  return runSqJson(
    runner,
    invocation,
    workspaceRoot,
    ['search', text, ...filterArgs, '--json'],
    isSqSearchHit,
  );
}

/** `sq show <id> --raw` — the clean-markdown dossier fed into the read-only preview. Not JSON,
 * so the outcome carries the stdout text directly rather than a parsed shape. */
export function getRaw(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
  id: string,
): Promise<SqOutcome<string>> {
  return runSqRaw(runner, invocation, workspaceRoot, ['show', id, '--raw']);
}

/** `sq show <id> --json` — the structured `discussion` array (author/ts/body per comment) and
 * `subentities` array (local_id/title/status/assignee/severity/story/body per sub-entity) are
 * consumed, feeding the preview's collapsible discussion and sub-entities sections respectively;
 * every other key is ignored (see `SqShowJson`). Distinct from `getRaw`'s `--raw` dossier text,
 * fetched in parallel with it by the caller. */
export function getShowJson(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
  id: string,
): Promise<SqOutcome<SqShowJson>> {
  return runSqJsonObject(runner, invocation, workspaceRoot, ['show', id, '--json'], isSqShowJson);
}

/** `sq workflow --raw` — the clean-markdown workflow cheatsheet (tables + fenced mermaid, no
 * Rich terminal chrome) fed into the workflow-cheatsheet panel. Same plain-text shape as
 * `getRaw`; no item id involved, so there's no argument beyond the invocation. */
export function getWorkflowRaw(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
): Promise<SqOutcome<string>> {
  return runSqRaw(runner, invocation, workspaceRoot, ['workflow', '--raw']);
}

/** `sq workflow types --json` — the spec's declared type catalog (name, resolved
 * order, prefix, reserved flag), already in spec order. Feeds the group-by-type sort and the
 * type-filter quick-pick order so neither hardcodes a type list or its ordering. */
export function getTypeCatalog(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
): Promise<SqOutcome<SqTypeCatalogEntry[]>> {
  return runSqJson(
    runner,
    invocation,
    workspaceRoot,
    ['workflow', 'types', '--json'],
    isSqTypeCatalogEntry,
  );
}

/** `sq workflow collections --json` — the spec's declared badge collection
 * vocabulary (code, label, emoji per badge), so a client renders the real glyph for an item's
 * `badges` map entries without hardcoding a collection name or emoji set. */
export function getCollectionsCatalog(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
): Promise<SqOutcome<SqCollectionCatalogEntry[]>> {
  return runSqJson(
    runner,
    invocation,
    workspaceRoot,
    ['workflow', 'collections', '--json'],
    isSqCollectionCatalogEntry,
  );
}

/** `sq workflow statuses --json` — the spec's declared status vocabulary,
 * including each status's semantic `role` (e.g. `"active"`), so a client styles by the
 * spec-declared role rather than a hardcoded status name. */
export function getStatusesCatalog(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
): Promise<SqOutcome<SqStatusCatalogEntry[]>> {
  return runSqJson(
    runner,
    invocation,
    workspaceRoot,
    ['workflow', 'statuses', '--json'],
    isSqStatusCatalogEntry,
  );
}

/** `sq graph <id> --json` — the item's ref graph (an ego-centric BFS), feeding the preview's
 * second collapsible mermaid diagram. `--all` includes closed items so the graph isn't
 * silently missing terminal-status refs (e.g. an Accepted decision or a Done task). */
export function getGraph(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
  id: string,
): Promise<SqOutcome<SqGraphNode>> {
  return runSqJsonObject(
    runner,
    invocation,
    workspaceRoot,
    ['graph', id, '--json', '--all'],
    isSqGraphNode,
  );
}
