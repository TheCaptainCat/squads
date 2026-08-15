import { describe, expect, it } from 'vitest';

import {
  findSquadConfig,
  parseSquadDirKey,
  resolveSquadDir,
  type SquadDirEnvironment,
} from '../src/domain/squadDir';

function makeEnvironment(opts: { files?: Readonly<Record<string, string>> }): SquadDirEnvironment {
  const files = opts.files ?? {};
  return {
    fileExists(path) {
      return path in files;
    },
    readFile(path) {
      return files[path];
    },
    dirname(path) {
      const idx = path.lastIndexOf('/');
      return idx <= 0 ? '/' : path.slice(0, idx);
    },
  };
}

describe('parseSquadDirKey', () => {
  it('reads the squad_dir value out of raw TOML text', () => {
    const toml = 'schema_version = "0.2"\nsquad_dir = "squads"\nactive_backends = []\n';
    expect(parseSquadDirKey(toml)).toBe('squads');
  });

  it('reads a custom squad_dir value', () => {
    const toml = 'squad_dir = "work"\n';
    expect(parseSquadDirKey(toml)).toBe('work');
  });

  it('falls back to the default "squads" when the key is absent', () => {
    expect(parseSquadDirKey('schema_version = "0.2"\n')).toBe('squads');
  });

  it('falls back to the default "squads" when the key is present but empty', () => {
    expect(parseSquadDirKey('squad_dir = ""\n')).toBe('squads');
  });

  // `sq` reads the config with a real TOML parser, so every spelling below is a config it
  // accepts. A client that reads only one of them watches a directory that does not exist, and
  // auto-refresh then never fires with nothing on screen to say so.
  it('reads a single-quoted (TOML literal) value', () => {
    expect(parseSquadDirKey("squad_dir = 'board'\n")).toBe('board');
  });

  it('reads a quoted key spelling', () => {
    expect(parseSquadDirKey('"squad_dir" = "board"\n')).toBe('board');
    expect(parseSquadDirKey("'squad_dir' = 'board'\n")).toBe('board');
  });

  it('reads a value with no spaces around the equals sign', () => {
    expect(parseSquadDirKey('squad_dir="board"\n')).toBe('board');
  });

  it('ignores a trailing inline comment', () => {
    expect(parseSquadDirKey('squad_dir = "board"  # where the squad lives\n')).toBe('board');
  });

  it('honours a backslash escape inside a basic string', () => {
    expect(parseSquadDirKey('squad_dir = "a\\"b"\n')).toBe('a"b');
    expect(parseSquadDirKey("squad_dir = 'a\\\\b'\n")).toBe('a\\\\b');
  });

  it('reads the key when other keys precede it', () => {
    const toml = '# a comment\n\nschema_version = "0.2"\nsquad_dir = \'board\'\n';
    expect(parseSquadDirKey(toml)).toBe('board');
  });

  it('ignores a squad_dir key nested under a table, which sq would not read either', () => {
    const toml = 'schema_version = "0.2"\n\n[tool]\nsquad_dir = "nested"\n';
    expect(parseSquadDirKey(toml)).toBe('squads');
  });

  it('reads the root key even when a table declares one of its own further down', () => {
    const toml = 'squad_dir = "board"\n\n[tool]\nsquad_dir = "nested"\n';
    expect(parseSquadDirKey(toml)).toBe('board');
  });

  it('falls back to the default for a value form it deliberately does not parse', () => {
    expect(parseSquadDirKey('squad_dir = """board"""\n')).toBe('squads');
    expect(parseSquadDirKey('squad_dir = board\n')).toBe('squads');
    expect(parseSquadDirKey('squad_dir = "unterminated\n')).toBe('squads');
  });

  it('does not match a different key that merely ends in squad_dir', () => {
    expect(parseSquadDirKey('other_squad_dir = "board"\n')).toBe('squads');
  });
});

describe('findSquadConfig', () => {
  it('finds .squads.toml at the starting directory', () => {
    const env = makeEnvironment({ files: { '/workspace/.squads.toml': 'squad_dir = "squads"' } });
    expect(findSquadConfig('/workspace', env)).toBe('/workspace/.squads.toml');
  });

  it('walks up through parent directories to find .squads.toml', () => {
    const env = makeEnvironment({ files: { '/workspace/.squads.toml': 'squad_dir = "squads"' } });
    expect(findSquadConfig('/workspace/packages/app', env)).toBe('/workspace/.squads.toml');
  });

  it('returns undefined when no .squads.toml exists anywhere up the tree', () => {
    const env = makeEnvironment({ files: {} });
    expect(findSquadConfig('/workspace/packages/app', env)).toBeUndefined();
  });
});

describe('resolveSquadDir', () => {
  it('resolves the squad dir relative to the config file, not the starting directory', () => {
    const env = makeEnvironment({
      files: { '/workspace/.squads.toml': 'squad_dir = "squads"' },
    });
    expect(resolveSquadDir('/workspace/packages/app', env)).toBe('/workspace/squads');
  });

  it('honors a custom squad_dir value', () => {
    const env = makeEnvironment({ files: { '/workspace/.squads.toml': 'squad_dir = "work"' } });
    expect(resolveSquadDir('/workspace', env)).toBe('/workspace/work');
  });

  it('honors a single-quoted custom squad_dir value, the same as sq does', () => {
    const env = makeEnvironment({ files: { '/workspace/.squads.toml': "squad_dir = 'board'" } });
    expect(resolveSquadDir('/workspace', env)).toBe('/workspace/board');
  });

  it('falls back to the default "squads" dir name when the config can\'t be read', () => {
    const files = { '/workspace/.squads.toml': 'squad_dir = "squads"' };
    const env: SquadDirEnvironment = {
      fileExists: (path) => path in files,
      readFile: () => undefined,
      dirname: (path) => {
        const idx = path.lastIndexOf('/');
        return idx <= 0 ? '/' : path.slice(0, idx);
      },
    };
    expect(resolveSquadDir('/workspace', env)).toBe('/workspace/squads');
  });

  it('returns undefined when no .squads.toml is found', () => {
    const env = makeEnvironment({ files: {} });
    expect(resolveSquadDir('/workspace', env)).toBeUndefined();
  });
});
