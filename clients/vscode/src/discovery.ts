/**
 * Resolves how to invoke `sq` against a workspace root.
 *
 * Order (first that works wins), auto-detecting the workspace toolchain — never PATH-only:
 *   1. explicit config override (`squads.sqPath`, or a `squads.command` array)
 *   2. workspace virtualenv — `.venv/bin/sq` (`.venv/Scripts/sq.exe` on Windows)
 *   3. `uv` on PATH + a project at the workspace root -> `uv run sq`
 *   4. `poetry` on PATH + a project at the workspace root -> `poetry run sq`
 *   5. bare `sq` on PATH (fallback)
 *
 * This module is pure/injectable: it takes an explicit `DiscoveryEnvironment` rather than
 * touching `node:fs`/`process.env`/the `vscode` API directly, so it's unit-testable with no
 * real filesystem, PATH, or VS Code host (see `createNodeDiscoveryEnvironment` for the real
 * one, wired up from `extension.ts`).
 */

export interface DiscoveryConfig {
  /** `squads.sqPath` — an explicit absolute path to the `sq` binary. Wins over `command`. */
  readonly sqPath?: string;
  /** `squads.command` — a full command + argv prefix, e.g. `["uv", "run", "sq"]`. */
  readonly command?: readonly string[];
}

export type DiscoverySource =
  'config-sq-path' | 'config-command' | 'venv' | 'uv' | 'poetry' | 'path';

/** How to spawn `sq`: run `command` with `[...args, ...subcommandArgs]`. */
export interface SqInvocation {
  readonly command: string;
  readonly args: readonly string[];
  readonly source: DiscoverySource;
}

export interface DiscoveryEnvironment {
  readonly platform: NodeJS.Platform;
  /** True if `path` exists on disk (used for the venv strategy and `squads.sqPath`). */
  fileExists(path: string): boolean;
  /**
   * True if `name` resolves to an executable via PATH (used for `uv`/`poetry`/bare `sq`).
   * Does not execute it — existence/executability only.
   */
  isOnPath(name: string): boolean;
}

export type DiscoveryResult =
  | { readonly ok: true; readonly invocation: SqInvocation }
  | { readonly ok: false; readonly triedOrder: readonly DiscoverySource[] };

function venvSqPath(workspaceRoot: string, env: DiscoveryEnvironment): string {
  return env.platform === 'win32'
    ? `${workspaceRoot}/.venv/Scripts/sq.exe`
    : `${workspaceRoot}/.venv/bin/sq`;
}

/** A `pyproject.toml` at the workspace root, taken as "this is a Python project". */
function hasProject(workspaceRoot: string, env: DiscoveryEnvironment): boolean {
  return env.fileExists(`${workspaceRoot}/pyproject.toml`);
}

function tryConfigSqPath(
  sqPath: string | undefined,
  env: DiscoveryEnvironment,
): SqInvocation | undefined {
  if (sqPath === undefined || sqPath === '' || !env.fileExists(sqPath)) {
    return undefined;
  }
  return { command: sqPath, args: [], source: 'config-sq-path' };
}

/** True if `value` looks like a filesystem path (has a separator) rather than a bare name. */
function looksLikeFilesystemPath(value: string): boolean {
  return value.includes('/') || value.includes('\\');
}

function tryConfigCommand(
  command: readonly string[] | undefined,
  env: DiscoveryEnvironment,
): SqInvocation | undefined {
  if (command === undefined || command.length === 0) {
    return undefined;
  }
  const [first, ...rest] = command;
  if (first === undefined) {
    return undefined;
  }
  // A bare name (e.g. "uv") is PATH-scanned; an absolute/relative path (e.g.
  // "/opt/py/bin/python") is checked for existence directly — a PATH scan would never
  // match it and silently skip an explicit override.
  const resolvable = looksLikeFilesystemPath(first) ? env.fileExists(first) : env.isOnPath(first);
  if (!resolvable) {
    return undefined;
  }
  return { command: first, args: rest, source: 'config-command' };
}

function tryVenv(workspaceRoot: string, env: DiscoveryEnvironment): SqInvocation | undefined {
  const venvPath = venvSqPath(workspaceRoot, env);
  return env.fileExists(venvPath) ? { command: venvPath, args: [], source: 'venv' } : undefined;
}

function tryUv(workspaceRoot: string, env: DiscoveryEnvironment): SqInvocation | undefined {
  return env.isOnPath('uv') && hasProject(workspaceRoot, env)
    ? { command: 'uv', args: ['run', 'sq'], source: 'uv' }
    : undefined;
}

function tryPoetry(workspaceRoot: string, env: DiscoveryEnvironment): SqInvocation | undefined {
  return env.isOnPath('poetry') && hasProject(workspaceRoot, env)
    ? { command: 'poetry', args: ['run', 'sq'], source: 'poetry' }
    : undefined;
}

function tryPath(env: DiscoveryEnvironment): SqInvocation | undefined {
  return env.isOnPath('sq') ? { command: 'sq', args: [], source: 'path' } : undefined;
}

/**
 * Resolve the invocation to use for `sq`, trying each strategy in the order documented
 * above and returning the first that works. Callers should cache the result and re-probe
 * on failure (see `SqDiscovery`) rather than calling this on every invocation.
 */
export function resolveSqInvocation(
  workspaceRoot: string,
  config: DiscoveryConfig,
  env: DiscoveryEnvironment,
): DiscoveryResult {
  const tried: DiscoverySource[] = [];

  if (config.sqPath !== undefined && config.sqPath !== '') {
    tried.push('config-sq-path');
    const invocation = tryConfigSqPath(config.sqPath, env);
    if (invocation !== undefined) {
      return { ok: true, invocation };
    }
  }

  if (config.command !== undefined && config.command.length > 0) {
    tried.push('config-command');
    const invocation = tryConfigCommand(config.command, env);
    if (invocation !== undefined) {
      return { ok: true, invocation };
    }
  }

  const remainingStrategies: readonly [DiscoverySource, () => SqInvocation | undefined][] = [
    ['venv', () => tryVenv(workspaceRoot, env)],
    ['uv', () => tryUv(workspaceRoot, env)],
    ['poetry', () => tryPoetry(workspaceRoot, env)],
    ['path', () => tryPath(env)],
  ];
  for (const [source, attempt] of remainingStrategies) {
    tried.push(source);
    const invocation = attempt();
    if (invocation !== undefined) {
      return { ok: true, invocation };
    }
  }

  return { ok: false, triedOrder: tried };
}

/**
 * Caches the resolved `sq` invocation and re-probes on demand (call `invalidate()` after a
 * spawn fails, e.g. with `ENOENT`, so the next call re-runs discovery instead of retrying a
 * stale answer forever).
 */
export class SqDiscovery {
  private cached: SqInvocation | undefined;

  constructor(
    private readonly workspaceRoot: string,
    private readonly getConfig: () => DiscoveryConfig,
    private readonly env: DiscoveryEnvironment,
  ) {}

  resolve(): DiscoveryResult {
    if (this.cached !== undefined) {
      return { ok: true, invocation: this.cached };
    }
    const result = resolveSqInvocation(this.workspaceRoot, this.getConfig(), this.env);
    if (result.ok) {
      this.cached = result.invocation;
    }
    return result;
  }

  /** Drop the cached invocation so the next `resolve()` re-runs discovery from scratch. */
  invalidate(): void {
    this.cached = undefined;
  }
}

/** Human-readable description of the strategies tried, for the "none found" notification. */
export function describeTriedOrder(triedOrder: readonly DiscoverySource[]): string {
  const labels: Record<DiscoverySource, string> = {
    'config-sq-path': 'squads.sqPath',
    'config-command': 'squads.command',
    venv: '.venv',
    uv: 'uv run',
    poetry: 'poetry run',
    path: 'sq on PATH',
  };
  return triedOrder.map((source) => labels[source]).join(' -> ');
}
