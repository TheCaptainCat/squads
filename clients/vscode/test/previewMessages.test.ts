import { describe, expect, it } from 'vitest';

import {
  NAVIGATE_HISTORY_COMMAND,
  OPEN_ITEM_COMMAND,
  parseNavigateHistoryMessage,
  parseOpenItemMessage,
  parseRefreshMessage,
  parseToggleFoldMessage,
  REFRESH_COMMAND,
  routeForMessage,
  routeForTreeSelection,
  TOGGLE_FOLD_COMMAND,
} from '../src/domain/previewMessages';

describe('parseOpenItemMessage', () => {
  it('parses a well-formed message', () => {
    const message = parseOpenItemMessage({
      command: OPEN_ITEM_COMMAND,
      id: 'TASK-452',
      newTab: true,
    });
    expect(message).toEqual({ command: 'openItem', id: 'TASK-452', newTab: true });
  });

  it('rejects null/undefined/non-object payloads', () => {
    expect(parseOpenItemMessage(null)).toBeNull();
    expect(parseOpenItemMessage(undefined)).toBeNull();
    expect(parseOpenItemMessage('openItem')).toBeNull();
    expect(parseOpenItemMessage(42)).toBeNull();
    expect(parseOpenItemMessage({})).toBeNull();
  });

  it('rejects a wrong command discriminator', () => {
    expect(
      parseOpenItemMessage({ command: 'somethingElse', id: 'TASK-452', newTab: false }),
    ).toBeNull();
  });

  it('rejects an empty or non-string id', () => {
    expect(parseOpenItemMessage({ command: OPEN_ITEM_COMMAND, id: '', newTab: false })).toBeNull();
    expect(parseOpenItemMessage({ command: OPEN_ITEM_COMMAND, id: 42, newTab: false })).toBeNull();
  });

  it('rejects a missing or non-boolean newTab', () => {
    expect(
      parseOpenItemMessage({ command: OPEN_ITEM_COMMAND, id: 'TASK-452', newTab: 'yes' }),
    ).toBeNull();
    expect(parseOpenItemMessage({ command: OPEN_ITEM_COMMAND, id: 'TASK-452' })).toBeNull();
  });
});

describe('routeForMessage', () => {
  it('routes a plain click to the same panel', () => {
    expect(routeForMessage({ command: 'openItem', id: 'TASK-452', newTab: false })).toBe(
      'same-panel',
    );
  });

  it('routes a middle-click (or ctrl/cmd-click) to a new panel', () => {
    expect(routeForMessage({ command: 'openItem', id: 'TASK-452', newTab: true })).toBe(
      'new-panel',
    );
  });
});

describe('routeForTreeSelection', () => {
  it('reuses the active panel when one is already open', () => {
    expect(routeForTreeSelection(true)).toBe('same-panel');
  });

  it('opens a new panel when none is open yet', () => {
    expect(routeForTreeSelection(false)).toBe('new-panel');
  });
});

describe('parseNavigateHistoryMessage', () => {
  it('parses a well-formed back message', () => {
    const message = parseNavigateHistoryMessage({
      command: NAVIGATE_HISTORY_COMMAND,
      direction: 'back',
    });
    expect(message).toEqual({ command: 'navigateHistory', direction: 'back' });
  });

  it('parses a well-formed forward message', () => {
    const message = parseNavigateHistoryMessage({
      command: NAVIGATE_HISTORY_COMMAND,
      direction: 'forward',
    });
    expect(message).toEqual({ command: 'navigateHistory', direction: 'forward' });
  });

  it('rejects null/undefined/non-object payloads', () => {
    expect(parseNavigateHistoryMessage(null)).toBeNull();
    expect(parseNavigateHistoryMessage(undefined)).toBeNull();
    expect(parseNavigateHistoryMessage('navigateHistory')).toBeNull();
    expect(parseNavigateHistoryMessage({})).toBeNull();
  });

  it('rejects a wrong command discriminator', () => {
    expect(parseNavigateHistoryMessage({ command: 'somethingElse', direction: 'back' })).toBeNull();
  });

  it('rejects a missing or invalid direction', () => {
    expect(parseNavigateHistoryMessage({ command: NAVIGATE_HISTORY_COMMAND })).toBeNull();
    expect(
      parseNavigateHistoryMessage({ command: NAVIGATE_HISTORY_COMMAND, direction: 'sideways' }),
    ).toBeNull();
  });
});

describe('parseRefreshMessage', () => {
  it('parses a well-formed message', () => {
    expect(parseRefreshMessage({ command: REFRESH_COMMAND })).toEqual({ command: 'refresh' });
  });

  it('rejects null/undefined/non-object payloads', () => {
    expect(parseRefreshMessage(null)).toBeNull();
    expect(parseRefreshMessage(undefined)).toBeNull();
    expect(parseRefreshMessage('refresh')).toBeNull();
    expect(parseRefreshMessage({})).toBeNull();
  });

  it('rejects a wrong command discriminator', () => {
    expect(parseRefreshMessage({ command: 'somethingElse' })).toBeNull();
  });
});

describe('parseToggleFoldMessage', () => {
  it('parses a well-formed open message', () => {
    const message = parseToggleFoldMessage({
      command: TOGGLE_FOLD_COMMAND,
      id: 'ST1',
      open: true,
    });
    expect(message).toEqual({ command: 'toggleFold', id: 'ST1', open: true });
  });

  it('parses a well-formed close message', () => {
    const message = parseToggleFoldMessage({
      command: TOGGLE_FOLD_COMMAND,
      id: 'ST1',
      open: false,
    });
    expect(message).toEqual({ command: 'toggleFold', id: 'ST1', open: false });
  });

  it('rejects null/undefined/non-object payloads', () => {
    expect(parseToggleFoldMessage(null)).toBeNull();
    expect(parseToggleFoldMessage(undefined)).toBeNull();
    expect(parseToggleFoldMessage('toggleFold')).toBeNull();
    expect(parseToggleFoldMessage({})).toBeNull();
  });

  it('rejects a wrong command discriminator', () => {
    expect(parseToggleFoldMessage({ command: 'somethingElse', id: 'ST1', open: true })).toBeNull();
  });

  it('rejects an empty or non-string id', () => {
    expect(parseToggleFoldMessage({ command: TOGGLE_FOLD_COMMAND, id: '', open: true })).toBeNull();
    expect(parseToggleFoldMessage({ command: TOGGLE_FOLD_COMMAND, id: 42, open: true })).toBeNull();
  });

  it('rejects a missing or non-boolean open', () => {
    expect(
      parseToggleFoldMessage({ command: TOGGLE_FOLD_COMMAND, id: 'ST1', open: 'yes' }),
    ).toBeNull();
    expect(parseToggleFoldMessage({ command: TOGGLE_FOLD_COMMAND, id: 'ST1' })).toBeNull();
  });
});
