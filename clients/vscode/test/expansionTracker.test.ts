import { describe, expect, it } from 'vitest';

import { ExpansionTracker } from '../src/domain/expansionTracker';

describe('ExpansionTracker', () => {
  it('reports an untracked id as not expanded', () => {
    const tracker = new ExpansionTracker();

    expect(tracker.isExpanded('node-1')).toBe(false);
  });

  it('reports an id as expanded once set, across repeated reads', () => {
    const tracker = new ExpansionTracker();

    tracker.setExpanded('node-1', true);

    expect(tracker.isExpanded('node-1')).toBe(true);
    expect(tracker.isExpanded('node-1')).toBe(true);
  });

  it('un-tracks an id once collapsed', () => {
    const tracker = new ExpansionTracker();
    tracker.setExpanded('node-1', true);

    tracker.setExpanded('node-1', false);

    expect(tracker.isExpanded('node-1')).toBe(false);
  });

  it('tracks multiple ids independently', () => {
    const tracker = new ExpansionTracker();

    tracker.setExpanded('node-1', true);
    tracker.setExpanded('node-2', true);
    tracker.setExpanded('node-1', false);

    expect(tracker.isExpanded('node-1')).toBe(false);
    expect(tracker.isExpanded('node-2')).toBe(true);
  });

  it('keeps a tracked id expanded across a simulated refresh that still contains it', () => {
    const tracker = new ExpansionTracker();
    tracker.setExpanded('node-1', true);

    // A refresh that still lists node-1 (e.g. an unrelated sibling item changed).
    tracker.prune(new Set(['node-1', 'node-2']));

    expect(tracker.isExpanded('node-1')).toBe(true);
  });

  it('prunes a tracked id absent from the current tree (a deleted or renamed-away item)', () => {
    const tracker = new ExpansionTracker();
    tracker.setExpanded('node-1', true);

    // A refresh where node-1 no longer appears anywhere in the tree.
    tracker.prune(new Set(['node-2']));

    expect(tracker.isExpanded('node-1')).toBe(false);
  });

  it('leaves an already-untracked id alone when pruning', () => {
    const tracker = new ExpansionTracker();

    tracker.prune(new Set());

    expect(tracker.isExpanded('node-1')).toBe(false);
  });
});
