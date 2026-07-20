import { describe, expect, it } from 'vitest';

import {
  canStepBack,
  canStepForward,
  createHistory,
  currentId,
  pushHistory,
  stepBack,
  stepForward,
} from '../src/domain/previewHistory';

describe('createHistory', () => {
  it('seeds a single-entry history at index 0', () => {
    const history = createHistory('TASK-1');

    expect(history).toEqual({ ids: ['TASK-1'], index: 0 });
    expect(currentId(history)).toBe('TASK-1');
  });

  it('has both ends inert on a fresh history', () => {
    const history = createHistory('TASK-1');

    expect(canStepBack(history)).toBe(false);
    expect(canStepForward(history)).toBe(false);
  });
});

describe('pushHistory', () => {
  it('appends a new id after the current position', () => {
    const history = pushHistory(createHistory('TASK-1'), 'TASK-2');

    expect(history).toEqual({ ids: ['TASK-1', 'TASK-2'], index: 1 });
    expect(currentId(history)).toBe('TASK-2');
  });

  it('is a no-op when navigating to the id already current', () => {
    const history = createHistory('TASK-1');

    expect(pushHistory(history, 'TASK-1')).toEqual(history);
  });

  it('truncates the forward stack when navigating to a new item after stepping back', () => {
    let history = createHistory('TASK-1');
    history = pushHistory(history, 'TASK-2');
    history = pushHistory(history, 'TASK-3');
    history = stepBack(history);
    expect(currentId(history)).toBe('TASK-2');

    history = pushHistory(history, 'TASK-4');

    expect(history).toEqual({ ids: ['TASK-1', 'TASK-2', 'TASK-4'], index: 2 });
    expect(canStepForward(history)).toBe(false);
  });
});

describe('stepBack / stepForward', () => {
  it('retraces one step at a time', () => {
    let history = createHistory('TASK-1');
    history = pushHistory(history, 'TASK-2');
    history = pushHistory(history, 'TASK-3');

    history = stepBack(history);
    expect(currentId(history)).toBe('TASK-2');

    history = stepBack(history);
    expect(currentId(history)).toBe('TASK-1');
  });

  it('re-advances one step at a time', () => {
    let history = createHistory('TASK-1');
    history = pushHistory(history, 'TASK-2');
    history = pushHistory(history, 'TASK-3');
    history = stepBack(history);
    history = stepBack(history);

    history = stepForward(history);
    expect(currentId(history)).toBe('TASK-2');

    history = stepForward(history);
    expect(currentId(history)).toBe('TASK-3');
  });

  it('is a no-op at the oldest entry', () => {
    const history = createHistory('TASK-1');

    expect(stepBack(history)).toEqual(history);
  });

  it('is a no-op at the newest entry', () => {
    const history = pushHistory(createHistory('TASK-1'), 'TASK-2');

    expect(stepForward(history)).toEqual(history);
  });

  it('reports bounds correctly mid-history', () => {
    let history = createHistory('TASK-1');
    history = pushHistory(history, 'TASK-2');
    history = pushHistory(history, 'TASK-3');
    history = stepBack(history);

    expect(canStepBack(history)).toBe(true);
    expect(canStepForward(history)).toBe(true);
  });
});
