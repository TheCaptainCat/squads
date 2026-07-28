/**
 * The one definition of "refresh everything": all three tree providers plus every open preview
 * panel. Every entry point — the three view-title buttons (all bound to the same
 * `squads.refreshAll` command, `commands.ts`), the `.squads.json` watcher (`extension.ts`), and
 * the in-content preview refresh button (`itemPreviewManager.ts`'s message handler) — calls this
 * one function rather than keeping its own copy of the four calls, so the next thing that needs
 * to join a refresh only has to be added here.
 *
 * Deliberately typed against minimal structural interfaces (`Refreshable`/
 * `PreviewRefreshable`) rather than the real `SquadsTreeDataProvider`/`ItemPreviewManager`
 * classes, so this orchestration — the actual "what does refresh everything mean" logic — is
 * unit-testable with plain call-recording fakes and no `vscode` host, the same testability
 * discipline the rest of `domain/` holds to.
 */

export interface Refreshable {
  refresh(): Promise<void> | void;
}

export interface PreviewRefreshable {
  refreshOpenPreviews(): Promise<void> | void;
}

export async function refreshAll(
  work: Refreshable,
  roster: Refreshable,
  records: Refreshable,
  previews: PreviewRefreshable,
): Promise<void> {
  await Promise.all([
    work.refresh(),
    roster.refresh(),
    records.refresh(),
    previews.refreshOpenPreviews(),
  ]);
}
