import * as path from 'node:path';

import { type DiscoveryEnvironment, resolveSqInvocation } from '../../src/discovery';

/** How the canary spawns `sq`: `command` with `[...args, ...subcommandArgs]`. */
export interface CanaryInvocation {
  readonly command: string;
  readonly args: readonly string[];
  readonly source: string;
}

export type CanaryResolution =
  | { readonly ok: true; readonly invocation: CanaryInvocation }
  | { readonly ok: false; readonly reason: string };

/** The canary runs from a scratch dir, so `uv`/`poetry` must be pointed at the project with a
 * flag that selects it and keeps the cwd (never `--directory`, which moves the cwd into it). */
function pointAtProject(inv: CanaryInvocation, repoRoot: string): CanaryInvocation {
  const tool = path
    .basename(inv.command)
    .replace(/\.exe$/i, '')
    .toLowerCase();
  if (tool === 'uv' && inv.args[0] === 'run') {
    return { ...inv, args: ['run', '--project', repoRoot, ...inv.args.slice(1)] };
  }
  if (tool === 'poetry') {
    return { ...inv, args: ['--project', repoRoot, ...inv.args] };
  }
  return inv;
}

/** True for an argument that moves the child's cwd: `--directory`, `--cwd`, `--chdir`, `-C`,
 * in either the split or the `=`/attached form. */
export function movesCwd(arg: string): boolean {
  return /^(--directory|--cwd|--chdir)(=|$)/.test(arg) || arg.startsWith('-C');
}

/** A relative path is resolved against the process cwd, since the canary spawns from another. */
function absolutize(value: string): string {
  const isPath = /[\\/]/.test(value);
  return !isPath || path.isAbsolute(value) || path.win32.isAbsolute(value)
    ? value
    : path.resolve(value);
}

/**
 * Splits a pin into argv: a value naming an existing file is one path (spaces and all), a JSON
 * array of strings is taken as-is, anything else splits on whitespace.
 */
export function parsePin(pin: string, env: DiscoveryEnvironment): string[] {
  const trimmed = pin.trim();
  if (env.fileExists(absolutize(trimmed))) {
    return [absolutize(trimmed)];
  }
  if (trimmed.startsWith('[')) {
    try {
      const parsed: unknown = JSON.parse(trimmed);
      if (Array.isArray(parsed) && parsed.every((part) => typeof part === 'string')) {
        return parsed;
      }
    } catch {
      // Not JSON: fall through to whitespace splitting.
    }
  }
  return trimmed
    .split(/\s+/)
    .filter(Boolean)
    .map((part, index) => (index === 0 ? absolutize(part) : part));
}

/**
 * Resolves `sq` through the extension's own order (`src/discovery.ts`), with the repo root as
 * the workspace. A pin (`SQ_CANARY_CMD`) is never a preference: if it does not resolve, the
 * result is a failure, not a fall-through to another binary.
 */
export function resolveCanarySq(
  repoRoot: string,
  env: DiscoveryEnvironment,
  pinned?: string,
): CanaryResolution {
  const trimmedPin = pinned?.trim() ?? '';
  if (trimmedPin !== '') {
    const command = parsePin(trimmedPin, env).map((part, index) =>
      index === 0 ? absolutize(part) : part,
    );
    const result = resolveSqInvocation(repoRoot, { command }, env);
    if (!result.ok || result.invocation.source !== 'config-command') {
      return { ok: false, reason: `SQ_CANARY_CMD does not resolve: ${trimmedPin}` };
    }
    const { command: first, args } = result.invocation;
    if (args.some(movesCwd)) {
      return { ok: false, reason: `SQ_CANARY_CMD moves the working directory: ${trimmedPin}` };
    }
    return {
      ok: true,
      invocation: pointAtProject({ command: first, args, source: 'pinned' }, repoRoot),
    };
  }
  const result = resolveSqInvocation(repoRoot, {}, env);
  if (!result.ok) {
    return { ok: false, reason: 'no sq found' };
  }
  const { command, args, source } = result.invocation;
  return { ok: true, invocation: pointAtProject({ command, args, source }, repoRoot) };
}
