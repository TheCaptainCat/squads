import { execFile } from 'node:child_process';

export interface ProcessResult {
  readonly stdout: string;
  readonly stderr: string;
  readonly exitCode: number;
}

export interface ProcessRunner {
  run(command: string, args: readonly string[], cwd: string): Promise<ProcessResult>;
}

/** The real, `node:child_process`-backed `ProcessRunner` used at extension runtime. */
export const nodeProcessRunner: ProcessRunner = {
  run(command, args, cwd) {
    return new Promise((resolve, reject) => {
      execFile(command, args, { cwd, maxBuffer: 64 * 1024 * 1024 }, (error, stdout, stderr) => {
        if (error === null) {
          resolve({ stdout, stderr, exitCode: 0 });
          return;
        }
        const code = error.code;
        if (typeof code !== 'number') {
          // Spawn-level failure (e.g. ENOENT: the binary doesn't exist) rather than the
          // child process running and exiting non-zero — nothing to classify by exit code.
          reject(new Error(error.message));
          return;
        }
        resolve({ stdout, stderr, exitCode: code });
      });
    });
  },
};
