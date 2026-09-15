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
  SqBoardNotice,
  SqCollectionBadge,
  SqCollectionCatalogEntry,
  SqDiscussionEntry,
  SqGraphNode,
  SqListItem,
  SqMemoryDetail,
  SqMemoryListRow,
  SqOmission,
  SqRoleCatalogEntry,
  SqSearchHit,
  SqSearchHitRegion,
  SqShowJson,
  SqStatusCatalogEntry,
  SqSubEntity,
  SqSubEntityKindCatalogEntry,
  SqTreeNode,
  SqTypeCatalogEntry,
  SqTypeField,
  SqTypeLabels,
} from './types';

export type SqOutcome<T> =
  | {
      readonly kind: 'success';
      readonly data: T;
      /** Present (an array, possibly empty) only on a partial result — the frozen contract's
       * exit code `4`: stdout is a valid, complete-shape payload and this names what it left
       * out. `undefined`
       * means an ordinary clean read (exit `0`); an empty array means the command signalled
       * "partial" but the omissions report itself was missing or malformed, which degrades to
       * "partial, no detail" rather than being read as clean. Never inspect `.length === 0` to
       * mean "not partial" — check `!== undefined` instead. */
      readonly omissions?: readonly SqOmission[];
    }
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

function isSqOmission(value: unknown): value is SqOmission {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const entry = value as Record<string, unknown>;
  return (
    typeof entry.code === 'string' &&
    typeof entry.source === 'string' &&
    typeof entry.message === 'string'
  );
}

/** The documented consumer rule for stderr under `--json`: "the one line of stderr that parses
 * as a JSON object is the report" — stderr can carry a prose co-tenant (the `sq sync` version
 * notice), so this can't assume the whole stream, or its first/last line, is the report. Returns
 * `[]` — never throws, never returns `undefined` — when no line parses as an object, or the one
 * that does lacks a well-formed `omitted` array: both cases degrade to "partial, no detail",
 * exactly like an older `sq` that emits the report in a shape this build doesn't recognise yet. */
function parseOmissionsReport(stderr: string): readonly SqOmission[] {
  for (const line of stderr.split('\n')) {
    const trimmed = line.trim();
    if (trimmed === '') {
      continue;
    }
    let parsed: unknown;
    try {
      parsed = JSON.parse(trimmed);
    } catch {
      continue;
    }
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      continue;
    }
    const omitted = (parsed as Record<string, unknown>).omitted;
    return Array.isArray(omitted) && omitted.every(isSqOmission) ? omitted : [];
  }
  return [];
}

function classifyNonZeroExit(
  exitCode: number,
  stdout: string,
  stderr: string,
  fullCommand: readonly string[],
): SqOutcome<string> {
  const message = stderr.trim();
  if (exitCode === 2) {
    return { kind: 'usage-error', message, argv: fullCommand };
  }
  if (exitCode === 3) {
    return { kind: 'check-error', message };
  }
  if (exitCode === 4) {
    // The command did what was asked, stdout is a valid payload in its documented shape, and
    // entries are missing — a success carrying omissions, not a runtime error. Every caller of
    // the adapter inherits this from one place; none needs its own exit-code knowledge.
    return { kind: 'success', data: stdout, omissions: parseOmissionsReport(stderr) };
  }
  // 1, or anything else (including a schema-skew hard-stop) — surfaced verbatim, no
  // special-casing: the adapter doesn't try to interpret it.
  return { kind: 'runtime-error', message, exitCode };
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((entry) => typeof entry === 'string');
}

function isStringOrNull(value: unknown): value is string | null {
  return typeof value === 'string' || value === null;
}

/** A key an older `sq` omits entirely and a newer one may legitimately emit as `null`. Absent
 * and `null` mean the same thing to every consumer here: nothing to join on. */
function isOptionalNullableString(value: unknown): value is string | null | undefined {
  return value === undefined || isStringOrNull(value);
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
    isOptionalBadgeMap(node.badges) &&
    // Optional: an older `sq` predates the field and omits it — tolerated, not rejected, the
    // same treatment `badges` gets. Present-and-not-a-boolean is still a rejection.
    (node.anchor === undefined || typeof node.anchor === 'boolean')
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
    // Optional: an older `sq` predates the field and simply omits it — tolerated, not rejected.
    (node.edge_semantic === undefined ||
      typeof node.edge_semantic === 'string' ||
      node.edge_semantic === null) &&
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

/** `labels` is optional the same way `fields` is — an older `sq` omits it, treated the same as
 * "no resolved labels known" (`domain/typeLabels.ts` falls back to the raw type string). */
function isOptionalTypeLabels(value: unknown): value is SqTypeLabels | undefined {
  if (value === undefined) {
    return true;
  }
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const labels = value as Record<string, unknown>;
  return (
    typeof labels.singular === 'string' &&
    typeof labels.plural === 'string' &&
    typeof labels.singular_lower === 'string' &&
    typeof labels.plural_lower === 'string'
  );
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
    typeof entry.category === 'string' &&
    isOptionalTypeFieldArray(entry.fields) &&
    isOptionalTypeLabels(entry.labels) &&
    isOptionalNullableString(entry.subentity_kind)
  );
}

/** Shape guard for one `sq workflow subentity-kinds --json` entry, trimmed to the two keys the
 * client joins on (`SqSubEntityKindCatalogEntry`). Unlike the optional keys above, both are
 * required: this catalog has no older-`sq` variant to tolerate — an `sq` predating it doesn't
 * emit the row at all, it refuses the sub-command, which the adapter already reports as an
 * ordinary failure the caller degrades through. Exported for the same reason as `isSqTreeNode`
 * — the skew canary reuses the real adapter predicate. */
export function isSqSubEntityKindCatalogEntry(
  value: unknown,
): value is SqSubEntityKindCatalogEntry {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const entry = value as Record<string, unknown>;
  return (
    typeof entry.subentity_kind === 'string' &&
    Array.isArray(entry.fields) &&
    entry.fields.every(isSqTypeField)
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
    (typeof entry.role === 'string' || entry.role === null) &&
    (typeof entry.badge === 'string' || entry.badge === null)
  );
}

/** Shape guard for one `sq workflow roles --json` entry . Exported for the same reason
 * as `isSqTreeNode` — the skew canary reuses the real adapter predicate. */
export function isSqRoleCatalogEntry(value: unknown): value is SqRoleCatalogEntry {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const entry = value as Record<string, unknown>;
  return (
    typeof entry.role === 'string' &&
    typeof entry.settled === 'boolean' &&
    typeof entry.hidden === 'boolean' &&
    typeof entry.color === 'string' &&
    typeof entry.live === 'boolean'
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

/** `discussion` is **optional**, not required: an older `sq` predating the field omits the key
 * entirely, and a required-field guard would reject the whole `sq show --json` payload over one
 * missing array, blanking the entire preview rather than just its comments. Split out of
 * `isSqSubEntity` to keep that guard's complexity in check as much as to name the check. */
function hasOptionalDiscussion(entry: Record<string, unknown>): boolean {
  return (
    entry.discussion === undefined ||
    (Array.isArray(entry.discussion) && entry.discussion.every(isSqDiscussionEntry))
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
    isStringOrNull(entry.assignee) &&
    isStringOrNull(entry.story) &&
    typeof entry.body === 'string' &&
    isOptionalBadgeMap(entry.badges) &&
    hasOptionalDiscussion(entry)
  );
}

/** Shape guard for `sq show <id> --json`. Only checks the keys this client reads
 * (`discussion`, `subentities`, `type`) — every other field `sq show --json` emits is ignored,
 * per `SqShowJson`'s hand-trimmed contract. `type` is checked as optional rather than required
 * so a payload without it degrades to unlabelled sub-entity fields instead of failing the whole
 * guard and blanking the preview. */
export function isSqShowJson(value: unknown): value is SqShowJson {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const obj = value as Record<string, unknown>;
  return (
    Array.isArray(obj.discussion) &&
    obj.discussion.every(isSqDiscussionEntry) &&
    Array.isArray(obj.subentities) &&
    obj.subentities.every(isSqSubEntity) &&
    (obj.type === undefined || typeof obj.type === 'string')
  );
}

/** Shape guard for one `sq memory <role> list --json` row. `created_at` is optional (an older
 * `sq` predates the field) — present-and-not-a-string is still a rejection, the same
 * present-vs-absent-vs-wrong-type contract `badges`/`anchor` already get. */
export function isSqMemoryListRow(value: unknown): value is SqMemoryListRow {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const row = value as Record<string, unknown>;
  return (
    typeof row.slug === 'string' &&
    typeof row.filename === 'string' &&
    typeof row.description === 'string' &&
    (row.created_at === undefined || typeof row.created_at === 'string')
  );
}

/** Shape guard for `sq memory <role> show <slug> --json`'s single-object payload. Unlike the
 * list row, every field here is required — `show` is a newer surface with no older-`sq` skew
 * to tolerate yet. */
export function isSqMemoryDetail(value: unknown): value is SqMemoryDetail {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const detail = value as Record<string, unknown>;
  return (
    typeof detail.slug === 'string' &&
    typeof detail.summary === 'string' &&
    typeof detail.created_at === 'string' &&
    isStringArray(detail.tags) &&
    typeof detail.body === 'string'
  );
}

/** Shape guard for one `sq board list --json` row. */
export function isSqBoardNotice(value: unknown): value is SqBoardNotice {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const notice = value as Record<string, unknown>;
  return (
    typeof notice.n === 'number' &&
    typeof notice.id === 'string' &&
    typeof notice.author === 'string' &&
    typeof notice.posted_at === 'string' &&
    (typeof notice.until === 'string' || notice.until === null) &&
    typeof notice.body === 'string'
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
    return classifyNonZeroExit(result.exitCode, result.stdout, result.stderr, [
      invocation.command,
      ...argv,
    ]);
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
  return {
    kind: 'success',
    data: parsed.data,
    ...(raw.omissions ? { omissions: raw.omissions } : {}),
  };
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
  return {
    kind: 'success',
    data: parsed.data,
    ...(raw.omissions ? { omissions: raw.omissions } : {}),
  };
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
 * `subentities` array (local_id/title/status/assignee/story/body/badges per sub-entity) are
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
 * order, prefix, reserved flag, category), already in spec order. Feeds the group-by-type sort
 * and the type-filter quick-pick order so neither hardcodes a type list or its ordering, and
 * `domain/typeCategory.ts`'s category map so the records view / work-tree exclusion never
 * hardcodes a records-type list either. */
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

/** `sq workflow subentity-kinds --json` — the spec's declared sub-entity kind catalog, whose
 * `fields` carry each kind's declared axes (code, label, bound collection). Joined from an
 * item's type through the type catalog's `subentity_kind`, so the preview labels a sub-entity's
 * badge by what the spec calls it instead of a literal. An `sq` that predates the sub-command
 * fails this call the same way any other unavailable surface does; the caller degrades to the
 * raw field code rather than losing the badge. */
export function getSubentityKindsCatalog(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
): Promise<SqOutcome<SqSubEntityKindCatalogEntry[]>> {
  return runSqJson(
    runner,
    invocation,
    workspaceRoot,
    ['workflow', 'subentity-kinds', '--json'],
    isSqSubEntityKindCatalogEntry,
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

/** `sq workflow roles --json` — the spec's declared role catalog: one row per role,
 * carrying the `settled`/`hidden`/`color` a status's `role` reference resolves to. Joined with
 * `getStatusesCatalog` (status -> role name -> this catalog's role object) by
 * `domain/statusRole.ts`; neither `terminal` nor `is_open` survives on any surface — both are
 * derived client-side from the resolved role's `settled`. */
export function getRolesCatalog(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
): Promise<SqOutcome<SqRoleCatalogEntry[]>> {
  return runSqJson(
    runner,
    invocation,
    workspaceRoot,
    ['workflow', 'roles', '--json'],
    isSqRoleCatalogEntry,
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

/** `sq memory <role> list --json` — one role/operator's notebook index, feeding the Roster
 * tree's eager memory children (`metaTreeDataProvider.ts::refresh`). One or more unreadable
 * entries exits `4` (the frozen partial-result contract): the readable rows are still a valid array on stdout, and the
 * outcome comes back `kind: 'success'` with `omissions` populated — never dropped to a plain
 * failure, never silently under-counted. Only a genuine fetch failure (bad role slug, `sq` not
 * found, malformed output) surfaces as a non-success outcome. */
export function getMemoryList(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
  roleSlug: string,
): Promise<SqOutcome<SqMemoryListRow[]>> {
  return runSqJson(
    runner,
    invocation,
    workspaceRoot,
    ['memory', roleSlug, 'list', '--json'],
    isSqMemoryListRow,
  );
}

/** `sq memory <role> show <slug> --json` — one memory's full record, feeding the Roster tree's
 * drill-to-body step. */
export function getMemoryShow(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
  roleSlug: string,
  entrySlug: string,
): Promise<SqOutcome<SqMemoryDetail>> {
  return runSqJsonObject(
    runner,
    invocation,
    workspaceRoot,
    ['memory', roleSlug, 'show', entrySlug, '--json'],
    isSqMemoryDetail,
  );
}

/** `sq board list --json` — the team bulletin board's current (unexpired) notices, feeding the
 * `Squads: Open Team Board` panel. One or more unreadable notices exits `4` (the partial-result
 * contract), and
 * `classifyNonZeroExit` maps that to a `success` outcome carrying `omissions` — the readable
 * notices that were already valid JSON on stdout are not discarded, and `renderBoardHtml`
 * (`domain/boardView.ts`) renders them plus a visible "listing is partial" line. */
export function getBoardList(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
): Promise<SqOutcome<SqBoardNotice[]>> {
  return runSqJson(runner, invocation, workspaceRoot, ['board', 'list', '--json'], isSqBoardNotice);
}
