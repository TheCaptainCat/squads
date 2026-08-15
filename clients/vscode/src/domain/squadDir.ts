/**
 * Client-side mirror of `sq`'s own squad-folder resolution (`_paths.py::find_config`/`resolve`):
 * walk up from the workspace root looking for `.squads.toml`, then read its `squad_dir` key
 * (defaulting to `"squads"`, same as `SquadsConfig`) to get the folder that holds `.squads.json`.
 *
 * This exists purely so `squadWatcher.ts` knows *which directory* to watch — it is never
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

/** The `squad_dir` assignment at the start of a line: the key bare or quoted (all three TOML
 * spellings), then `=`, then the rest of the line for the value scanner below. */
const SQUAD_DIR_ASSIGNMENT = /^\s*(?:squad_dir|"squad_dir"|'squad_dir')\s*=\s*(.*)$/;

/** A line that opens a table (`[tool]`, `[[array]]`). Every bare key after one belongs to that
 * table, not to the document root — so the scan stops here rather than reading a `squad_dir`
 * that `sq` itself would never see. */
const TABLE_HEADER = /^\s*\[/;

/** Escapes TOML defines for a basic (double-quoted) string. Anything else after a backslash is
 * not valid TOML; the character is kept as-is rather than guessed at. */
const BASIC_ESCAPES: Readonly<Record<string, string>> = {
  n: '\n',
  t: '\t',
  r: '\r',
  '"': '"',
  '\\': '\\',
  b: '\b',
  f: '\f',
};

/** Reads a basic (double-quoted) string starting at `text[0] === '"'`, honouring backslash
 * escapes so an escaped quote doesn't terminate it early. `undefined` when unterminated. */
function readBasicString(text: string): string | undefined {
  let out = '';
  for (let i = 1; i < text.length; i++) {
    // `noUncheckedIndexedAccess` types this as possibly-undefined; the loop bound rules that
    // out, so the fallback is defensive rather than a semantic default.
    const char = text[i] ?? '';
    if (char === '"') {
      return out;
    }
    if (char === '\\' && i + 1 < text.length) {
      const escaped = text[i + 1] ?? '';
      out += BASIC_ESCAPES[escaped] ?? escaped;
      i++;
      continue;
    }
    out += char;
  }
  return undefined;
}

/** Reads a literal (single-quoted) string starting at `text[0] === "'"`. TOML literal strings
 * have no escape mechanism, so the first closing quote ends it. `undefined` when unterminated. */
function readLiteralString(text: string): string | undefined {
  const end = text.indexOf("'", 1);
  return end === -1 ? undefined : text.slice(1, end);
}

/** The value of a `squad_dir = <value>` assignment, or `undefined` when it isn't a form this
 * reader supports. Both single-line TOML string flavours are read — `sq` accepts either, and a
 * client that reads only one watches a directory that doesn't exist. A multi-line (`"""`/`'''`)
 * string, or a bare/unquoted value (not valid TOML for a string), is left unread: the caller
 * then falls back to the default the same way it does for an absent key. */
function readStringValue(rest: string): string | undefined {
  if (rest.startsWith('"""') || rest.startsWith("'''")) {
    return undefined;
  }
  if (rest.startsWith('"')) {
    return readBasicString(rest);
  }
  if (rest.startsWith("'")) {
    return readLiteralString(rest);
  }
  return undefined;
}

/** Extracts the document-root `squad_dir` value from raw TOML text — the one key this client
 * needs, so it doesn't pull in a full TOML parser for one string field. Falls back to the same
 * default the Python `SquadsConfig` model uses when the key is absent, empty, or written in a
 * form this reader deliberately doesn't cover (see `readStringValue`). */
export function parseSquadDirKey(tomlText: string): string {
  for (const line of tomlText.split('\n')) {
    if (TABLE_HEADER.test(line)) {
      break;
    }
    const match = SQUAD_DIR_ASSIGNMENT.exec(line);
    if (match === null) {
      continue;
    }
    const value = readStringValue((match[1] ?? '').trim());
    return value === undefined || value === '' ? DEFAULT_SQUAD_DIR : value;
  }
  return DEFAULT_SQUAD_DIR;
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
