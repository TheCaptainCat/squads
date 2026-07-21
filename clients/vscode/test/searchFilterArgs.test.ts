import { describe, expect, it } from 'vitest';

import { buildSearchFilterArgs, NO_NARROWING } from '../src/domain/searchFilterArgs';

describe('buildSearchFilterArgs', () => {
  it('builds no args when neither type nor status is set', () => {
    expect(buildSearchFilterArgs(NO_NARROWING)).toEqual([]);
    expect(buildSearchFilterArgs({ type: null, status: null })).toEqual([]);
  });

  it('builds --type alone', () => {
    expect(buildSearchFilterArgs({ type: 'task', status: null })).toEqual(['--type', 'task']);
  });

  it('builds --status alone', () => {
    expect(buildSearchFilterArgs({ type: null, status: 'InProgress' })).toEqual([
      '--status',
      'InProgress',
    ]);
  });

  it('AND-composes both when both are set', () => {
    expect(buildSearchFilterArgs({ type: 'task', status: 'InProgress' })).toEqual([
      '--type',
      'task',
      '--status',
      'InProgress',
    ]);
  });
});
