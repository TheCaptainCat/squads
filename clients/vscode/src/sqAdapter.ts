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
import type { SqListItem, SqTreeNode } from './types';

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

function isSqTreeNode(value: unknown): value is SqTreeNode {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const node = value as Record<string, unknown>;
  return (
    typeof node.id === 'string' &&
    typeof node.type === 'string' &&
    typeof node.status === 'string' &&
    (typeof node.priority === 'string' || node.priority === null) &&
    (typeof node.assignee === 'string' || node.assignee === null) &&
    typeof node.blocked === 'boolean' &&
    Array.isArray(node.children) &&
    node.children.every(isSqTreeNode)
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
    typeof item.updated_at === 'string'
  );
}

function hasNullableListItemStrings(item: Record<string, unknown>): boolean {
  return (
    (typeof item.parent === 'string' || item.parent === null) &&
    (typeof item.assignee === 'string' || item.assignee === null)
  );
}

function isSqListItem(value: unknown): value is SqListItem {
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

function parseJsonArray<T>(stdout: string, isItem: (value: unknown) => value is T): SqOutcome<T[]> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(stdout);
  } catch (error) {
    return { kind: 'parse-error', message: error instanceof Error ? error.message : String(error) };
  }
  if (!Array.isArray(parsed) || !parsed.every(isItem)) {
    return { kind: 'parse-error', message: 'sq --json output did not match the expected shape' };
  }
  return { kind: 'success', data: parsed };
}

async function runSqJson<T>(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
  subcommandArgs: readonly string[],
  isItem: (value: unknown) => value is T,
): Promise<SqOutcome<T[]>> {
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
  return parseJsonArray(result.stdout, isItem);
}

/** `sq tree [<root>] --json` — drives the sidebar tree. */
export function getTree(
  runner: ProcessRunner,
  invocation: SqInvocation,
  workspaceRoot: string,
  root?: string,
): Promise<SqOutcome<SqTreeNode[]>> {
  const args = root === undefined ? ['tree', '--json'] : ['tree', root, '--json'];
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
