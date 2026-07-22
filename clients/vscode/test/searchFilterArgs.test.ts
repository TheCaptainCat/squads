import { describe, expect, it } from 'vitest';

import { buildSearchFilterArgs, NO_NARROWING } from '../src/domain/searchFilterArgs';

describe('buildSearchFilterArgs', () => {
  it('builds no args when nothing is set', () => {
    expect(buildSearchFilterArgs(NO_NARROWING)).toEqual([]);
    expect(buildSearchFilterArgs({ type: null, status: null, category: null })).toEqual([]);
  });

  it('builds --type alone', () => {
    expect(buildSearchFilterArgs({ type: 'task', status: null, category: null })).toEqual([
      '--type',
      'task',
    ]);
  });

  it('builds --status alone', () => {
    expect(buildSearchFilterArgs({ type: null, status: 'InProgress', category: null })).toEqual([
      '--status',
      'InProgress',
    ]);
  });

  it('builds --category alone', () => {
    expect(buildSearchFilterArgs({ type: null, status: null, category: 'records' })).toEqual([
      '--category',
      'records',
    ]);
  });

  it('AND-composes all three when all are set', () => {
    expect(buildSearchFilterArgs({ type: 'task', status: 'InProgress', category: 'work' })).toEqual(
      ['--type', 'task', '--status', 'InProgress', '--category', 'work'],
    );
  });

  it('omits a cleared (null) narrowing even when the others are set', () => {
    expect(buildSearchFilterArgs({ type: 'task', status: null, category: 'work' })).toEqual([
      '--type',
      'task',
      '--category',
      'work',
    ]);
  });
});
