import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import type { SqInvocation } from '../src/discovery';
import type { ProcessResult, ProcessRunner } from '../src/processRunner';
import {
  describeFailure,
  getGraph,
  getList,
  getRaw,
  getTree,
  getWorkflowRaw,
} from '../src/sqAdapter';

const WORKSPACE_ROOT = '/workspace/example';

function fixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const TREE_FIXTURE = fixture('tree.json');
const LIST_FIXTURE = fixture('list.json');
const SHOW_RAW_FIXTURE = fixture('show-raw.txt');
const GRAPH_FIXTURE = fixture('graph.json');
const WORKFLOW_RAW_FIXTURE = fixture('workflow-raw.txt');

function stubRunner(result: ProcessResult): ProcessRunner {
  return { run: () => Promise.resolve(result) };
}

function recordingRunner(result: ProcessResult): {
  runner: ProcessRunner;
  calls: { command: string; args: readonly string[]; cwd: string }[];
} {
  const calls: { command: string; args: readonly string[]; cwd: string }[] = [];
  return {
    calls,
    runner: {
      run(command, args, cwd) {
        calls.push({ command, args, cwd });
        return Promise.resolve(result);
      },
    },
  };
}

const VENV_INVOCATION: SqInvocation = { command: '/venv/bin/sq', args: [], source: 'venv' };
const UV_INVOCATION: SqInvocation = { command: 'uv', args: ['run', 'sq'], source: 'uv' };

describe('getTree', () => {
  it('parses a real committed sq tree --json fixture', async () => {
    const runner = stubRunner({ stdout: TREE_FIXTURE, stderr: '', exitCode: 0 });
    const outcome = await getTree(runner, VENV_INVOCATION, WORKSPACE_ROOT, 'EPIC-99');

    expect(outcome.kind).toBe('success');
    if (outcome.kind !== 'success') {
      throw new Error('expected success');
    }
    expect(outcome.data[0]?.id).toBe('EPIC-99');
    expect(outcome.data[0]?.children[0]?.id).toBe('FEAT-100');
  });

  it('builds argv from the invocation prefix plus the tree subcommand', async () => {
    const { runner, calls } = recordingRunner({ stdout: '[]', stderr: '', exitCode: 0 });
    await getTree(runner, UV_INVOCATION, WORKSPACE_ROOT, 'EPIC-99');

    expect(calls).toEqual([
      { command: 'uv', args: ['run', 'sq', 'tree', 'EPIC-99', '--json'], cwd: WORKSPACE_ROOT },
    ]);
  });

  it('omits the root argument when none is given', async () => {
    const { runner, calls } = recordingRunner({ stdout: '[]', stderr: '', exitCode: 0 });
    await getTree(runner, VENV_INVOCATION, WORKSPACE_ROOT);

    expect(calls[0]?.args).toEqual(['tree', '--json']);
  });
});

describe('getList', () => {
  it('parses a real committed sq list --json fixture', async () => {
    const runner = stubRunner({ stdout: LIST_FIXTURE, stderr: '', exitCode: 0 });
    const outcome = await getList(runner, VENV_INVOCATION, WORKSPACE_ROOT);

    expect(outcome.kind).toBe('success');
    if (outcome.kind !== 'success') {
      throw new Error('expected success');
    }
    expect(outcome.data.length).toBeGreaterThan(0);
    expect(outcome.data.every((item) => typeof item.id === 'string')).toBe(true);
  });

  it('appends filter args before --json', async () => {
    const { runner, calls } = recordingRunner({ stdout: '[]', stderr: '', exitCode: 0 });
    await getList(runner, VENV_INVOCATION, WORKSPACE_ROOT, ['-t', 'task']);

    expect(calls[0]?.args).toEqual(['list', '-t', 'task', '--json']);
  });
});

describe('getGraph', () => {
  it('parses a real committed sq graph --json fixture (a single nested object, not an array)', async () => {
    const runner = stubRunner({ stdout: GRAPH_FIXTURE, stderr: '', exitCode: 0 });
    const outcome = await getGraph(runner, VENV_INVOCATION, WORKSPACE_ROOT, 'FEAT-449');

    expect(outcome.kind).toBe('success');
    if (outcome.kind !== 'success') {
      throw new Error('expected success');
    }
    expect(outcome.data.id).toBe('FEAT-449');
    expect(outcome.data.children[0]?.id).toBe('FEAT-100');
  });

  it('builds argv as "graph <id> --json --all"', async () => {
    const { runner, calls } = recordingRunner({ stdout: GRAPH_FIXTURE, stderr: '', exitCode: 0 });
    await getGraph(runner, UV_INVOCATION, WORKSPACE_ROOT, 'FEAT-449');

    expect(calls).toEqual([
      {
        command: 'uv',
        args: ['run', 'sq', 'graph', 'FEAT-449', '--json', '--all'],
        cwd: WORKSPACE_ROOT,
      },
    ]);
  });

  it('surfaces well-formed JSON that is an array (not the expected single object) as a parse-error', async () => {
    const runner = stubRunner({ stdout: '[]', stderr: '', exitCode: 0 });
    const outcome = await getGraph(runner, VENV_INVOCATION, WORKSPACE_ROOT, 'FEAT-449');

    expect(outcome.kind).toBe('parse-error');
  });

  it('maps a non-zero exit the same way as the other json surfaces', async () => {
    const runner = stubRunner({ stdout: '', stderr: 'No such item: BOGUS-1', exitCode: 1 });
    const outcome = await getGraph(runner, VENV_INVOCATION, WORKSPACE_ROOT, 'BOGUS-1');

    expect(outcome).toEqual({
      kind: 'runtime-error',
      message: 'No such item: BOGUS-1',
      exitCode: 1,
    });
  });
});

describe('exit code mapping', () => {
  it('maps exit 2 to a usage-error carrying the full, runnable command line', async () => {
    const runner = stubRunner({ stdout: '', stderr: 'No such option: --bogus-flag', exitCode: 2 });
    const outcome = await getTree(runner, VENV_INVOCATION, WORKSPACE_ROOT, 'EPIC-99');

    expect(outcome).toEqual({
      kind: 'usage-error',
      message: 'No such option: --bogus-flag',
      argv: ['/venv/bin/sq', 'tree', 'EPIC-99', '--json'],
    });
  });

  it('includes the invocation prefix (e.g. "uv run") in the usage-error command line too', async () => {
    const runner = stubRunner({ stdout: '', stderr: 'No such option: --bogus-flag', exitCode: 2 });
    const outcome = await getTree(runner, UV_INVOCATION, WORKSPACE_ROOT, 'EPIC-99');

    expect(outcome).toEqual({
      kind: 'usage-error',
      message: 'No such option: --bogus-flag',
      argv: ['uv', 'run', 'sq', 'tree', 'EPIC-99', '--json'],
    });
  });

  it('maps exit 3 to a check-error, surfaced verbatim', async () => {
    const runner = stubRunner({ stdout: '', stderr: '3 issues found', exitCode: 3 });
    const outcome = await getList(runner, VENV_INVOCATION, WORKSPACE_ROOT);

    expect(outcome).toEqual({ kind: 'check-error', message: '3 issues found' });
  });

  it('maps exit 1 to a runtime-error, surfaced verbatim (including schema skew)', async () => {
    const runner = stubRunner({
      stdout: '',
      stderr: 'Schema mismatch: run `sq migrate up`.',
      exitCode: 1,
    });
    const outcome = await getTree(runner, VENV_INVOCATION, WORKSPACE_ROOT, 'EPIC-99');

    expect(outcome).toEqual({
      kind: 'runtime-error',
      message: 'Schema mismatch: run `sq migrate up`.',
      exitCode: 1,
    });
  });

  it('maps an unexpected non-zero exit code to a runtime-error too', async () => {
    const runner = stubRunner({ stdout: '', stderr: 'boom', exitCode: 17 });
    const outcome = await getList(runner, VENV_INVOCATION, WORKSPACE_ROOT);

    expect(outcome).toEqual({ kind: 'runtime-error', message: 'boom', exitCode: 17 });
  });

  it('surfaces a spawn failure (e.g. the binary vanished) without throwing', async () => {
    const runner: ProcessRunner = { run: () => Promise.reject(new Error('ENOENT')) };
    const outcome = await getTree(runner, VENV_INVOCATION, WORKSPACE_ROOT, 'EPIC-99');

    expect(outcome).toEqual({ kind: 'spawn-error', message: 'ENOENT' });
  });

  it('surfaces malformed JSON as a parse-error rather than throwing', async () => {
    const runner = stubRunner({ stdout: 'not json', stderr: '', exitCode: 0 });
    const outcome = await getTree(runner, VENV_INVOCATION, WORKSPACE_ROOT, 'EPIC-99');

    expect(outcome.kind).toBe('parse-error');
  });

  it('surfaces well-formed JSON that does not match the expected shape as a parse-error', async () => {
    const runner = stubRunner({ stdout: '[{"unexpected": true}]', stderr: '', exitCode: 0 });
    const outcome = await getTree(runner, VENV_INVOCATION, WORKSPACE_ROOT, 'EPIC-99');

    expect(outcome.kind).toBe('parse-error');
  });
});

describe('getRaw', () => {
  it('returns the committed sq show --raw fixture text verbatim on success', async () => {
    const runner = stubRunner({ stdout: SHOW_RAW_FIXTURE, stderr: '', exitCode: 0 });
    const outcome = await getRaw(runner, VENV_INVOCATION, WORKSPACE_ROOT, 'TASK-430');

    expect(outcome).toEqual({ kind: 'success', data: SHOW_RAW_FIXTURE });
  });

  it('builds argv as "show <id> --raw"', async () => {
    const { runner, calls } = recordingRunner({ stdout: 'ignored', stderr: '', exitCode: 0 });
    await getRaw(runner, UV_INVOCATION, WORKSPACE_ROOT, 'TASK-430');

    expect(calls).toEqual([
      { command: 'uv', args: ['run', 'sq', 'show', 'TASK-430', '--raw'], cwd: WORKSPACE_ROOT },
    ]);
  });

  it('maps a non-zero exit the same way as the JSON surfaces', async () => {
    const runner = stubRunner({ stdout: '', stderr: 'No such item: BOGUS-1', exitCode: 1 });
    const outcome = await getRaw(runner, VENV_INVOCATION, WORKSPACE_ROOT, 'BOGUS-1');

    expect(outcome).toEqual({
      kind: 'runtime-error',
      message: 'No such item: BOGUS-1',
      exitCode: 1,
    });
  });

  it('surfaces a spawn failure without throwing', async () => {
    const runner: ProcessRunner = { run: () => Promise.reject(new Error('ENOENT')) };
    const outcome = await getRaw(runner, VENV_INVOCATION, WORKSPACE_ROOT, 'TASK-430');

    expect(outcome).toEqual({ kind: 'spawn-error', message: 'ENOENT' });
  });
});

describe('getWorkflowRaw', () => {
  it('returns the committed sq workflow --raw fixture text verbatim on success', async () => {
    const runner = stubRunner({ stdout: WORKFLOW_RAW_FIXTURE, stderr: '', exitCode: 0 });
    const outcome = await getWorkflowRaw(runner, VENV_INVOCATION, WORKSPACE_ROOT);

    expect(outcome).toEqual({ kind: 'success', data: WORKFLOW_RAW_FIXTURE });
  });

  it('builds argv as "workflow --raw", no item id involved', async () => {
    const { runner, calls } = recordingRunner({ stdout: 'ignored', stderr: '', exitCode: 0 });
    await getWorkflowRaw(runner, UV_INVOCATION, WORKSPACE_ROOT);

    expect(calls).toEqual([
      { command: 'uv', args: ['run', 'sq', 'workflow', '--raw'], cwd: WORKSPACE_ROOT },
    ]);
  });

  it('maps a non-zero exit the same way as the other plain-text surface', async () => {
    const runner = stubRunner({ stdout: '', stderr: 'Schema mismatch', exitCode: 1 });
    const outcome = await getWorkflowRaw(runner, VENV_INVOCATION, WORKSPACE_ROOT);

    expect(outcome).toEqual({ kind: 'runtime-error', message: 'Schema mismatch', exitCode: 1 });
  });

  it('surfaces a spawn failure without throwing', async () => {
    const runner: ProcessRunner = { run: () => Promise.reject(new Error('ENOENT')) };
    const outcome = await getWorkflowRaw(runner, VENV_INVOCATION, WORKSPACE_ROOT);

    expect(outcome).toEqual({ kind: 'spawn-error', message: 'ENOENT' });
  });
});

describe('describeFailure', () => {
  it('appends the replayable command line to a usage-error message', () => {
    const message = describeFailure({
      kind: 'usage-error',
      message: 'No such option: --bogus-flag',
      argv: ['sq', 'tree', '--json'],
    });

    expect(message).toBe('No such option: --bogus-flag (command: sq tree --json)');
  });

  it('passes every other outcome kind through verbatim', () => {
    expect(describeFailure({ kind: 'check-error', message: '3 issues found' })).toBe(
      '3 issues found',
    );
    expect(describeFailure({ kind: 'runtime-error', message: 'boom', exitCode: 17 })).toBe('boom');
    expect(describeFailure({ kind: 'parse-error', message: 'bad json' })).toBe('bad json');
    expect(describeFailure({ kind: 'spawn-error', message: 'ENOENT' })).toBe('ENOENT');
  });
});
