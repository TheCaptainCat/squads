/**
 * Query sequencing for the search QuickPick: submit/short-debounce (never per-keystroke), one
 * search in flight per query, and last-query-wins so a superseded in-flight result can never
 * clobber whatever a newer query already rendered. Kept `vscode`-free — real `setTimeout` is
 * used directly (exercised with `vi.useFakeTimers()` in tests) rather than an injected timer
 * abstraction, since nothing here needs a fake host, only fake time.
 */

export interface SearchRunnerCallbacks<T> {
  /** A search just started (query non-empty) — drive a busy indicator. */
  readonly onStart: () => void;
  /** The search for `query` completed and is still current (not superseded). */
  readonly onResult: (result: T, query: string) => void;
  /** The query is empty/whitespace-only — no process is spawned; render the idle state and
   * invalidate any run still in flight so its eventual result is dropped. */
  readonly onEmptyQuery: () => void;
}

export class SearchRunner<T> {
  private token = 0;
  private timer: ReturnType<typeof setTimeout> | undefined;

  constructor(
    private readonly runSearch: (query: string, filterArgs: readonly string[]) => Promise<T>,
    private readonly debounceMs: number,
    private readonly callbacks: SearchRunnerCallbacks<T>,
  ) {}

  private clearTimer(): void {
    if (this.timer !== undefined) {
      clearTimeout(this.timer);
      this.timer = undefined;
    }
  }

  private async execute(query: string, filterArgs: readonly string[]): Promise<void> {
    const myToken = ++this.token;
    this.callbacks.onStart();
    const result = await this.runSearch(query, filterArgs);
    // A newer query (typed/submit/dispose) bumped the token while this one was in flight —
    // drop the stale result instead of clobbering whatever the newer query already rendered.
    if (myToken === this.token) {
      this.callbacks.onResult(result, query);
    }
  }

  private startOrEmpty(query: string, run: () => void): void {
    this.clearTimer();
    if (query.trim() === '') {
      this.token += 1;
      this.callbacks.onEmptyQuery();
      return;
    }
    run();
  }

  /** `onDidChangeValue` — debounces; never spawns a process for an empty/whitespace query. */
  typed(query: string, filterArgs: readonly string[]): void {
    this.startOrEmpty(query, () => {
      this.timer = setTimeout(() => {
        void this.execute(query, filterArgs);
      }, this.debounceMs);
    });
  }

  /** `onDidAccept` with nothing currently selected — cancels any pending debounce timer and
   * runs immediately, so pressing Enter never has to wait out the debounce window. */
  submit(query: string, filterArgs: readonly string[]): void {
    this.startOrEmpty(query, () => {
      void this.execute(query, filterArgs);
    });
  }

  /** Cancels any pending timer and invalidates any run still in flight — call on QuickPick
   * dismissal so a late result never arrives after the picker (and its callbacks' targets) is
   * gone. */
  dispose(): void {
    this.clearTimer();
    this.token += 1;
  }
}
