import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { SearchRunner } from '../src/domain/searchRunner';

const DEBOUNCE_MS = 300;

/** A search stub whose promise resolves only when the test calls `resolve` — lets a test control
 * exactly when an in-flight run completes, to exercise last-query-wins ordering. */
function deferredSearch(): {
  runSearch: (query: string, filterArgs: readonly string[]) => Promise<string>;
  resolve: (query: string, value: string) => void;
  calls: { query: string; filterArgs: readonly string[] }[];
} {
  const pending = new Map<string, (value: string) => void>();
  const calls: { query: string; filterArgs: readonly string[] }[] = [];
  return {
    calls,
    runSearch: (query, filterArgs) => {
      calls.push({ query, filterArgs });
      return new Promise<string>((resolvePromise) => {
        pending.set(query, resolvePromise);
      });
    },
    resolve: (query, value) => {
      pending.get(query)?.(value);
      pending.delete(query);
    },
  };
}

describe('SearchRunner.typed', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('does not spawn a search for an empty/whitespace query', () => {
    const runSearch = vi.fn();
    const onEmptyQuery = vi.fn();
    const runner = new SearchRunner(runSearch, DEBOUNCE_MS, {
      onStart: vi.fn(),
      onResult: vi.fn(),
      onEmptyQuery,
    });

    runner.typed('', []);
    runner.typed('   ', []);
    vi.advanceTimersByTime(DEBOUNCE_MS + 1);

    expect(runSearch).not.toHaveBeenCalled();
    expect(onEmptyQuery).toHaveBeenCalledTimes(2);
  });

  it('coalesces rapid keystrokes into exactly one search after the debounce window', async () => {
    const runSearch = vi.fn().mockResolvedValue('result');
    const onStart = vi.fn();
    const onResult = vi.fn();
    const runner = new SearchRunner(runSearch, DEBOUNCE_MS, {
      onStart,
      onResult,
      onEmptyQuery: vi.fn(),
    });

    runner.typed('l', []);
    vi.advanceTimersByTime(DEBOUNCE_MS - 1);
    runner.typed('lo', []);
    vi.advanceTimersByTime(DEBOUNCE_MS - 1);
    runner.typed('log', []);
    vi.advanceTimersByTime(DEBOUNCE_MS);
    await vi.runOnlyPendingTimersAsync();

    expect(runSearch).toHaveBeenCalledTimes(1);
    expect(runSearch).toHaveBeenCalledWith('log', []);
    expect(onStart).toHaveBeenCalledTimes(1);
    expect(onResult).toHaveBeenCalledWith('result', 'log');
  });

  it('never fires a scheduled search once the query goes back to empty', () => {
    const runSearch = vi.fn();
    const runner = new SearchRunner(runSearch, DEBOUNCE_MS, {
      onStart: vi.fn(),
      onResult: vi.fn(),
      onEmptyQuery: vi.fn(),
    });

    runner.typed('login', []);
    vi.advanceTimersByTime(DEBOUNCE_MS - 1);
    runner.typed('', []);
    vi.advanceTimersByTime(DEBOUNCE_MS + 1);

    expect(runSearch).not.toHaveBeenCalled();
  });

  it('drops a superseded in-flight result (last-query-wins)', async () => {
    const { runSearch, resolve, calls } = deferredSearch();
    const onResult = vi.fn();
    const runner = new SearchRunner(runSearch, DEBOUNCE_MS, {
      onStart: vi.fn(),
      onResult,
      onEmptyQuery: vi.fn(),
    });

    runner.submit('stale', []);
    await Promise.resolve();
    runner.submit('fresh', []);
    await Promise.resolve();
    expect(calls.map((call) => call.query)).toEqual(['stale', 'fresh']);

    // Resolve out of order: the newer query answers first, then the stale one arrives late.
    resolve('fresh', 'fresh-result');
    await Promise.resolve();
    resolve('stale', 'stale-result');
    await Promise.resolve();

    expect(onResult).toHaveBeenCalledTimes(1);
    expect(onResult).toHaveBeenCalledWith('fresh-result', 'fresh');
  });
});

describe('SearchRunner.submit', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('cancels a pending debounce timer and runs immediately instead', async () => {
    const runSearch = vi.fn().mockResolvedValue('result');
    const runner = new SearchRunner(runSearch, DEBOUNCE_MS, {
      onStart: vi.fn(),
      onResult: vi.fn(),
      onEmptyQuery: vi.fn(),
    });

    runner.typed('log', []);
    runner.submit('login', []);
    await vi.runOnlyPendingTimersAsync();

    expect(runSearch).toHaveBeenCalledTimes(1);
    expect(runSearch).toHaveBeenCalledWith('login', []);
  });

  it('treats an empty query as the empty state, spawning no process', () => {
    const runSearch = vi.fn();
    const onEmptyQuery = vi.fn();
    const runner = new SearchRunner(runSearch, DEBOUNCE_MS, {
      onStart: vi.fn(),
      onResult: vi.fn(),
      onEmptyQuery,
    });

    runner.submit('', []);

    expect(runSearch).not.toHaveBeenCalled();
    expect(onEmptyQuery).toHaveBeenCalledTimes(1);
  });

  it('passes filter args through to the search function unchanged', async () => {
    const runSearch = vi.fn().mockResolvedValue('result');
    const runner = new SearchRunner(runSearch, DEBOUNCE_MS, {
      onStart: vi.fn(),
      onResult: vi.fn(),
      onEmptyQuery: vi.fn(),
    });

    runner.submit('login', ['--type', 'task']);
    await vi.runOnlyPendingTimersAsync();

    expect(runSearch).toHaveBeenCalledWith('login', ['--type', 'task']);
  });
});

describe('SearchRunner.dispose', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('cancels a pending debounce timer so it never fires', () => {
    const runSearch = vi.fn();
    const runner = new SearchRunner(runSearch, DEBOUNCE_MS, {
      onStart: vi.fn(),
      onResult: vi.fn(),
      onEmptyQuery: vi.fn(),
    });

    runner.typed('login', []);
    runner.dispose();
    vi.advanceTimersByTime(DEBOUNCE_MS + 1);

    expect(runSearch).not.toHaveBeenCalled();
  });

  it('drops a result that was already in flight when disposed', async () => {
    const { runSearch, resolve } = deferredSearch();
    const onResult = vi.fn();
    const runner = new SearchRunner(runSearch, DEBOUNCE_MS, {
      onStart: vi.fn(),
      onResult,
      onEmptyQuery: vi.fn(),
    });

    runner.submit('login', []);
    await Promise.resolve();
    runner.dispose();
    resolve('login', 'result');
    await Promise.resolve();

    expect(onResult).not.toHaveBeenCalled();
  });
});
