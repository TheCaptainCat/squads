import { describe, expect, it } from 'vitest';

import { summarizeOmissions } from '../src/domain/omissions';

describe('summarizeOmissions', () => {
  it('names the count and pluralizes for more than one', () => {
    expect(
      summarizeOmissions([
        { code: 'unreadable', source: 'TASK-1', message: 'bad' },
        { code: 'unreadable', source: 'TASK-2', message: 'bad' },
      ]),
    ).toBe('2 entries could not be read — listing partial.');
  });

  it('uses the singular noun for exactly one', () => {
    expect(summarizeOmissions([{ code: 'unreadable', source: 'TASK-1', message: 'bad' }])).toBe(
      '1 entry could not be read — listing partial.',
    );
  });

  it('still states the listing is partial when there is no per-item detail', () => {
    expect(summarizeOmissions([])).toBe('Some entries could not be read — listing partial.');
  });

  it('never inspects the omission code — an unrecognised one is still counted', () => {
    expect(
      summarizeOmissions([{ code: 'some-future-code', source: 'TASK-1', message: 'bad' }]),
    ).toBe('1 entry could not be read — listing partial.');
  });
});
