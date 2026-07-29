import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

/**
 * VS Code never reads a per-item `toggled` property for extension-contributed `contributes.menus`
 * entries — that field only exists on the internal `ICommandAction` core VS Code registers its own
 * commands with, never on the declarative JSON an extension ships — so it renders no checkmark or
 * pressed state anywhere, toolbar or dropdown, no matter how a command is wired. The Work Items
 * view's two title-bar toggles carry the state visually instead: each contributes *two* commands
 * with distinct icons/titles and mutually exclusive `when` clauses on the same context key, so
 * whichever half is visible shows an icon for the current state and a title for the action a click
 * performs. This guards that pairing structurally so a future edit can't silently drop one half,
 * reuse an icon across both, or leave a `toggled` property lying around again.
 */

interface ManifestCommand {
  command: string;
  title: string;
  icon?: string;
}

interface ManifestMenuItem {
  command: string;
  when: string;
  group: string;
  toggled?: unknown;
}

interface ExtensionManifest {
  contributes: {
    commands: ManifestCommand[];
    menus: { 'view/title': ManifestMenuItem[] };
  };
}

const PACKAGE_ROOT = path.resolve(__dirname, '..');
const manifest = JSON.parse(
  readFileSync(path.join(PACKAGE_ROOT, 'package.json'), 'utf8'),
) as ExtensionManifest;

function commandFor(id: string): ManifestCommand {
  const found = manifest.contributes.commands.find((c) => c.command === id);
  if (found === undefined) {
    throw new Error(`no contributes.commands entry for ${id}`);
  }
  return found;
}

function menuItemFor(id: string): ManifestMenuItem {
  const found = manifest.contributes.menus['view/title'].find((m) => m.command === id);
  if (found === undefined) {
    throw new Error(`no view/title entry for ${id}`);
  }
  return found;
}

const TOGGLE_PAIRS: readonly { on: string; off: string; contextKey: string }[] = [
  { on: 'squads.toggleGroupByType', off: 'squads.ungroupByType', contextKey: 'squads.groupByType' },
  { on: 'squads.toggleShowClosed', off: 'squads.hideClosed', contextKey: 'squads.showClosed' },
];

describe('view-title toggle icon pairs', () => {
  it('declares no `toggled` property anywhere (VS Code never reads it for extension menus)', () => {
    const withToggled = manifest.contributes.menus['view/title'].filter(
      (item) => item.toggled !== undefined,
    );
    expect(withToggled).toEqual([]);
  });

  it.each(TOGGLE_PAIRS)(
    'shows exactly one of $on / $off at a time, with distinct icons in the same nav slot',
    ({ on, off, contextKey }) => {
      const onCommand = commandFor(on);
      const offCommand = commandFor(off);
      const onMenuItem = menuItemFor(on);
      const offMenuItem = menuItemFor(off);

      // Distinct, present icons — the whole point is the button's appearance changes.
      expect(onCommand.icon).toBeDefined();
      expect(offCommand.icon).toBeDefined();
      expect(onCommand.icon).not.toBe(offCommand.icon);

      // Same toolbar slot, so swapping which one is visible doesn't move the button.
      expect(onMenuItem.group).toBe(offMenuItem.group);

      // Mutually exclusive `when` on the same context key: exactly one renders per state.
      expect(onMenuItem.when).toContain(`!${contextKey}`);
      expect(offMenuItem.when).toContain(contextKey);
      expect(offMenuItem.when).not.toContain(`!${contextKey}`);
    },
  );
});
