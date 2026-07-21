/**
 * The full-text search QuickPick (`squads.search`): a read-only consumer of `sq search --json`,
 * the same engine the TUI search page uses — no new search capability lives here. Opens a
 * `vscode.window.createQuickPick()` (not `showQuickPick`, so `onDidChangeValue`/`onDidAccept` and
 * `busy`/`placeholder` are all under our control), drives the submit/debounced query through
 * `domain/searchRunner.ts`'s pure sequencer, and renders hits mapped by
 * `domain/searchResults.ts`'s pure `hitsToResultRows`. Thin glue only, mirroring
 * `treeDataProvider.ts`/`itemPreviewManager.ts`'s unit-vs-host split: the pure mapping/sequencing
 * is unit-tested, this module's actual QuickPick wiring is exercised by the extension-host smoke
 * path.
 *
 * `matchOnDescription`/`matchOnDetail` are turned on to widen VS Code's own always-on local
 * label/description/detail filter over `items` — a QuickPick has no way to disable that filter
 * outright, so without this a legitimate server-returned row whose *title* doesn't contain the
 * query (e.g. a body/discussion match) could be hidden by the widget itself after being rendered.
 * Every hit's `detail` always carries the matched snippet (which does contain the query), so this
 * is a mitigation of a VS Code API constraint, not additional client-side re-matching of our own.
 */
import * as vscode from 'vscode';

import { describeTriedOrder, type SqDiscovery } from './discovery';
import { isReservedType } from './domain/reservedTypes';
import { decideAccept } from './domain/searchAccept';
import {
  buildSearchFilterArgs,
  NO_NARROWING,
  type SearchNarrowing,
} from './domain/searchFilterArgs';
import { hitsToResultRows, type SearchResultRow } from './domain/searchResults';
import { SearchRunner } from './domain/searchRunner';
import type { ItemPreviewManager } from './itemPreviewManager';
import type { ProcessRunner } from './processRunner';
import {
  describeFailure,
  getSearch,
  getStatusesCatalog,
  getTypeCatalog,
  type SqOutcome,
} from './sqAdapter';
import type { SqSearchHit } from './types';

/** Not per-keystroke: fires on submit (Enter) or after this short a pause in typing. */
const DEBOUNCE_MS = 300;
const PLACEHOLDER_IDLE = 'Type to search…';
const TITLE_IDLE = 'Squads Search';
const CLEAR_TYPE_LABEL = 'All types';
const CLEAR_STATUS_LABEL = 'All statuses';

interface SearchQuickPickItem extends vscode.QuickPickItem {
  readonly itemId: string;
}

function toQuickPickItem(row: SearchResultRow): SearchQuickPickItem {
  return {
    itemId: row.itemId,
    label: row.label,
    description: row.description,
    detail: row.detail,
  };
}

/** Title-bar buttons for the type/status narrowing controls — module-level singletons so
 * `onDidTriggerButton` can tell them apart by reference. Sourced vocab, not the buttons
 * themselves, is what's spec-driven here. */
const TYPE_FILTER_BUTTON: vscode.QuickInputButton = {
  iconPath: new vscode.ThemeIcon('symbol-class'),
  tooltip: 'Filter by item type',
};
const STATUS_FILTER_BUTTON: vscode.QuickInputButton = {
  iconPath: new vscode.ThemeIcon('symbol-enum'),
  tooltip: 'Filter by status',
};

/** Reflects the active narrowing in the picker's title so it's never invisible state — "Squads
 * Search" when neither is set. */
function describeNarrowing(narrowing: SearchNarrowing): string {
  const parts: string[] = [];
  if (narrowing.type !== null) {
    parts.push(`type: ${narrowing.type}`);
  }
  if (narrowing.status !== null) {
    parts.push(`status: ${narrowing.status}`);
  }
  return parts.length === 0 ? TITLE_IDLE : `${TITLE_IDLE} — ${parts.join(', ')}`;
}

export class SearchQuickPickController {
  // Reset at the top of every `open()` — a search session (and its narrowing) is transient,
  // scoped to one QuickPick, never carried over to the next invocation.
  private narrowing: SearchNarrowing = NO_NARROWING;

  constructor(
    private readonly runner: ProcessRunner,
    private readonly discovery: SqDiscovery,
    private readonly workspaceRoot: string,
    private readonly notifyError: (message: string) => void,
    private readonly previewManager: ItemPreviewManager,
  ) {}

  /** Entry point for the `squads.search` command. Creates a fresh QuickPick every invocation
   * (no reused/owned panel, unlike the item preview) — a search session is transient by nature. */
  open(): void {
    this.narrowing = NO_NARROWING;
    const quickPick = vscode.window.createQuickPick<SearchQuickPickItem>();
    quickPick.title = TITLE_IDLE;
    quickPick.placeholder = PLACEHOLDER_IDLE;
    quickPick.matchOnDescription = true;
    quickPick.matchOnDetail = true;
    quickPick.buttons = [TYPE_FILTER_BUTTON, STATUS_FILTER_BUTTON];
    quickPick.items = [];

    const searchRunner = new SearchRunner<SqOutcome<SqSearchHit[]>>(
      (query, filterArgs) => this.runSearch(query, filterArgs),
      DEBOUNCE_MS,
      {
        onStart: () => {
          quickPick.busy = true;
        },
        onResult: (outcome, query) => {
          quickPick.busy = false;
          this.applyOutcome(quickPick, outcome, query);
        },
        onEmptyQuery: () => {
          quickPick.busy = false;
          quickPick.items = [];
          quickPick.placeholder = PLACEHOLDER_IDLE;
        },
      },
    );

    quickPick.onDidChangeValue((value) => {
      // Drop the previous query's rows (and with them any stale active/selected row) *before*
      // the debounced re-search resolves. Without this, refining "login" -> "logout" and
      // pressing Enter inside the debounce window could leave the old "login" row as
      // `selectedItems[0]` — decideAccept would then read that as an accept and open the stale
      // item instead of falling through to submit the refined query. Busy/last-wins are
      // untouched: this only clears the displayed list, not `SearchRunner`'s own state.
      quickPick.items = [];
      searchRunner.typed(value, this.currentFilterArgs());
    });
    quickPick.onDidAccept(() => {
      const decision = decideAccept(quickPick.selectedItems[0]);
      if (decision.kind === 'open') {
        // Hide first so focus lands on the opened preview, not the (now-stale) picker.
        quickPick.hide();
        void this.previewManager.openFromTree(decision.itemId);
        return;
      }
      // Enter with nothing currently selected/active: treat as an explicit "search now" that
      // bypasses the debounce window, rather than an accept with no target.
      searchRunner.submit(quickPick.value, this.currentFilterArgs());
    });
    quickPick.onDidTriggerButton((button) => {
      if (button === TYPE_FILTER_BUTTON) {
        void this.pickType(quickPick, searchRunner);
      } else if (button === STATUS_FILTER_BUTTON) {
        void this.pickStatus(quickPick, searchRunner);
      }
    });
    quickPick.onDidHide(() => {
      searchRunner.dispose();
      quickPick.dispose();
    });

    quickPick.show();
  }

  /** Re-runs the current query (if any) through the same submit/debounce path — same busy
   * indicator, same last-query-wins protection — rather than re-filtering the already-returned
   * list client-side. A blank query just updates the title; there's nothing to re-run. */
  private applyNarrowing(
    quickPick: vscode.QuickPick<SearchQuickPickItem>,
    searchRunner: SearchRunner<SqOutcome<SqSearchHit[]>>,
  ): void {
    quickPick.title = describeNarrowing(this.narrowing);
    if (quickPick.value.trim() !== '') {
      searchRunner.submit(quickPick.value, this.currentFilterArgs());
    }
  }

  /** Type narrowing: a companion pick over the spec's declared type catalog (never a
   * hardcoded list), reserved meta types (role/skill/operator) excluded the same way the browse
   * tree's type filter excludes them. A failed/unreachable catalog fetch degrades to just the
   * "All types" clear option rather than blocking the picker. */
  private async pickType(
    quickPick: vscode.QuickPick<SearchQuickPickItem>,
    searchRunner: SearchRunner<SqOutcome<SqSearchHit[]>>,
  ): Promise<void> {
    const resolution = this.discovery.resolve();
    const catalog = resolution.ok
      ? await getTypeCatalog(this.runner, resolution.invocation, this.workspaceRoot)
      : undefined;
    const types =
      catalog?.kind === 'success'
        ? catalog.data.filter((entry) => !isReservedType(entry.type)).map((entry) => entry.type)
        : [];
    const picked = await vscode.window.showQuickPick([CLEAR_TYPE_LABEL, ...types], {
      placeHolder: 'Filter search results by item type',
    });
    if (picked === undefined) {
      return;
    }
    this.narrowing = { ...this.narrowing, type: picked === CLEAR_TYPE_LABEL ? null : picked };
    this.applyNarrowing(quickPick, searchRunner);
  }

  /** Status narrowing — same shape as `pickType`, sourced from the spec's declared status
   * catalog instead. */
  private async pickStatus(
    quickPick: vscode.QuickPick<SearchQuickPickItem>,
    searchRunner: SearchRunner<SqOutcome<SqSearchHit[]>>,
  ): Promise<void> {
    const resolution = this.discovery.resolve();
    const catalog = resolution.ok
      ? await getStatusesCatalog(this.runner, resolution.invocation, this.workspaceRoot)
      : undefined;
    const statuses = catalog?.kind === 'success' ? catalog.data.map((entry) => entry.status) : [];
    const picked = await vscode.window.showQuickPick([CLEAR_STATUS_LABEL, ...statuses], {
      placeHolder: 'Filter search results by status',
    });
    if (picked === undefined) {
      return;
    }
    this.narrowing = { ...this.narrowing, status: picked === CLEAR_STATUS_LABEL ? null : picked };
    this.applyNarrowing(quickPick, searchRunner);
  }

  private async runSearch(
    text: string,
    filterArgs: readonly string[],
  ): Promise<SqOutcome<SqSearchHit[]>> {
    const resolution = this.discovery.resolve();
    if (!resolution.ok) {
      return {
        kind: 'spawn-error',
        message: `No sq invocation found. Tried, in order: ${describeTriedOrder(resolution.triedOrder)}.`,
      };
    }
    return getSearch(this.runner, resolution.invocation, this.workspaceRoot, text, filterArgs);
  }

  private applyOutcome(
    quickPick: vscode.QuickPick<SearchQuickPickItem>,
    outcome: SqOutcome<SqSearchHit[]>,
    query: string,
  ): void {
    if (outcome.kind !== 'success') {
      if (outcome.kind === 'spawn-error') {
        this.discovery.invalidate();
      }
      this.notifyError(`Squads: ${describeFailure(outcome)}`);
      quickPick.items = [];
      quickPick.placeholder = PLACEHOLDER_IDLE;
      return;
    }
    const rows = hitsToResultRows(outcome.data);
    if (rows.length === 0) {
      // A clean "no results" state, not an error — the query text was valid and understood, it
      // simply matched nothing.
      quickPick.items = [];
      quickPick.placeholder = `No matches for "${query}"`;
      return;
    }
    quickPick.placeholder = PLACEHOLDER_IDLE;
    quickPick.items = rows.map(toQuickPickItem);
  }

  /** The active `--type`/`--status` narrowing, AND-composed with the query text exactly as
   * `sq search` composes its own filters — see `domain/searchFilterArgs.ts`. */
  private currentFilterArgs(): readonly string[] {
    return buildSearchFilterArgs(this.narrowing);
  }
}
