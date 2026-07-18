import { describe, expect, it } from 'vitest';

import { buildTooltip, emphasisForNode } from '../src/domain/displayNode';

describe('emphasisForNode', () => {
  it('is "none" when blocked/closed/active are all false', () => {
    expect(emphasisForNode({ blocked: false, closed: false, active: false })).toBe('none');
  });

  it('is "active" (green) when only active is true', () => {
    expect(emphasisForNode({ blocked: false, closed: false, active: true })).toBe('active');
  });

  it('is "closed" (dimmed) when only closed is true', () => {
    expect(emphasisForNode({ blocked: false, closed: true, active: false })).toBe('closed');
  });

  it('is "blocked" (red) when only blocked is true', () => {
    expect(emphasisForNode({ blocked: true, closed: false, active: false })).toBe('blocked');
  });

  it('closed wins over active when somehow both are set (F26/F7 disjoint-in-practice, but the precedence still resolves deterministically)', () => {
    expect(emphasisForNode({ blocked: false, closed: true, active: true })).toBe('closed');
  });

  it('blocked wins over both closed and active — the highest-priority emphasis', () => {
    expect(emphasisForNode({ blocked: true, closed: true, active: true })).toBe('blocked');
    expect(emphasisForNode({ blocked: true, closed: false, active: true })).toBe('blocked');
  });
});

describe('buildTooltip', () => {
  it('backslash-escapes markdown metacharacters in the assignee name (REV-485 F3)', () => {
    const tooltip = buildTooltip({
      id: 'TASK-1',
      type: 'task',
      status: 'InProgress',
      assignee: '_Ada_ *Typescript* `dev`',
      badges: [],
      blocked: false,
    });
    expect(tooltip).toContain('Assignee: \\_Ada\\_ \\*Typescript\\* \\`dev\\`');
  });

  it('leaves an unassigned tooltip line unescaped', () => {
    const tooltip = buildTooltip({
      id: 'TASK-1',
      type: 'task',
      status: 'InProgress',
      assignee: null,
      badges: [],
      blocked: false,
    });
    expect(tooltip).toContain('Assignee: unassigned');
  });
});
