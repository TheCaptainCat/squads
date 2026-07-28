import { describe, expect, it } from 'vitest';

import { refreshAll } from '../src/domain/refreshAll';

class CountingRefreshable {
  calls = 0;

  refresh(): Promise<void> {
    this.calls += 1;
    return Promise.resolve();
  }
}

describe('refreshAll', () => {
  it('refreshes the work tree, the roster tree, the records tree, and every open preview', async () => {
    const work = new CountingRefreshable();
    const roster = new CountingRefreshable();
    const records = new CountingRefreshable();
    let previewCalls = 0;
    const previews = {
      refreshOpenPreviews: (): Promise<void> => {
        previewCalls += 1;
        return Promise.resolve();
      },
    };

    await refreshAll(work, roster, records, previews);

    expect(work.calls).toBe(1);
    expect(roster.calls).toBe(1);
    expect(records.calls).toBe(1);
    expect(previewCalls).toBe(1);
  });

  it('refreshes all four on every call, not just the first (repeated manual refreshes)', async () => {
    const work = new CountingRefreshable();
    const roster = new CountingRefreshable();
    const records = new CountingRefreshable();
    let previewCalls = 0;
    const previews = {
      refreshOpenPreviews: (): Promise<void> => {
        previewCalls += 1;
        return Promise.resolve();
      },
    };

    await refreshAll(work, roster, records, previews);
    await refreshAll(work, roster, records, previews);

    expect(work.calls).toBe(2);
    expect(roster.calls).toBe(2);
    expect(records.calls).toBe(2);
    expect(previewCalls).toBe(2);
  });
});
