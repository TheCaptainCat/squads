/**
 * Client-side mirror of `sq`'s own squad-folder resolution (`_paths.py::find_config`/`resolve`):
 * walk up from the workspace root looking for `.squads.toml`, then read its `squad_dir` key
 * (defaulting to `"squads"`, same as `SquadsConfig`) to get the folder that holds `.squads.json`.
 *
 * This exists purely so `squadWatcher.ts` (F17) knows *which directory* to watch — it is never
 * used to read item data itself (the extension stays a pure consumer of `sq … --json`).
 * Pure/injectable like `discovery.ts`, so the walk-up + TOML-key parsing is unit-testable with
 * no real filesystem or VS Code host.
 */

export interface SquadDirEnvironment {
  /** True if `path` exists on disk as a regular file. */
  fileExists(path: string): boolean;
  /** File contents, or `undefined` if it can't be read. */
  readFile(path: string): string | undefined;
  /** Parent directory of `path` (OS-appropriate); returns `path` itself at the filesystem root. */
  dirname(path: string): string;
}

const CONFIG_FILENAME = '.squads.toml';
const DEFAULT_SQUAD_DIR = 'squads';

/** Extracts `squad_dir = "..."` from raw TOML text — the one key this client needs, so it
 * doesn't pull in a full TOML parser for one string field. Falls back to the same default the
 * Python `SquadsConfig` model uses when the key is absent or empty. */
export function parseSquadDirKey(tomlText: string): string {
  const match = /^\s*squad_dir\s*=\s*"([^"]*)"/m.exec(tomlText);
  const value = match?.[1];
  return value === undefined || value === '' ? DEFAULT_SQUAD_DIR : value;
}

/** Walk up from `startDir` (inclusive) to the nearest `.squads.toml`, mirroring
 * `_paths.py::find_config`. Returns its path, or `undefined` if none is found before the
 * filesystem root. */
export function findSquadConfig(startDir: string, env: SquadDirEnvironment): string | undefined {
  let dir = startDir;
  for (;;) {
    const candidate = `${dir}/${CONFIG_FILENAME}`;
    if (env.fileExists(candidate)) {
      return candidate;
    }
    const parent = env.dirname(dir);
    if (parent === dir) {
      return undefined;
    }
    dir = parent;
  }
}

/** Resolve the active squad directory for `workspaceRoot`, or `undefined` when no
 * `.squads.toml` is found (mirrors `_paths.py::resolve`'s config-walk-up branch; the
 * `--dir`-override and default-on-init branches don't apply to a read-only client). */
export function resolveSquadDir(
  workspaceRoot: string,
  env: SquadDirEnvironment,
): string | undefined {
  const configPath = findSquadConfig(workspaceRoot, env);
  if (configPath === undefined) {
    return undefined;
  }
  const configDir = env.dirname(configPath);
  const contents = env.readFile(configPath);
  const squadDirName = contents === undefined ? DEFAULT_SQUAD_DIR : parseSquadDirKey(contents);
  return `${configDir}/${squadDirName}`;
}
