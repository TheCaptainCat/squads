import * as fs from 'node:fs';
import * as path from 'node:path';

import type { DiscoveryEnvironment } from './discovery';

function candidateNames(name: string, platform: NodeJS.Platform): readonly string[] {
  if (platform !== 'win32') {
    return [name];
  }
  const pathExt = (process.env.PATHEXT ?? '.EXE;.CMD;.BAT').split(';');
  return [name, ...pathExt.map((ext) => `${name}${ext.toLowerCase()}`)];
}

function isExecutableFile(candidate: string): boolean {
  try {
    const stat = fs.statSync(candidate);
    return stat.isFile();
  } catch {
    return false;
  }
}

/** The real, `node:fs`/`process.env`-backed `DiscoveryEnvironment` used at extension runtime. */
export function createNodeDiscoveryEnvironment(): DiscoveryEnvironment {
  const platform = process.platform;
  return {
    platform,
    fileExists(candidate: string): boolean {
      return isExecutableFile(candidate);
    },
    isOnPath(name: string): boolean {
      const dirs = (process.env.PATH ?? '').split(path.delimiter).filter((dir) => dir !== '');
      for (const dir of dirs) {
        for (const candidateName of candidateNames(name, platform)) {
          if (isExecutableFile(path.join(dir, candidateName))) {
            return true;
          }
        }
      }
      return false;
    },
  };
}
