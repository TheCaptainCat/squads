/**
 * Command-id string constants shared across modules that need to invoke a registered command
 * by id without importing the module that registers it (and risking a cycle). Currently just
 * the one global refresh command (`commands.ts` registers it; `extension.ts`'s `.squads.json`
 * watcher and `itemPreviewManager.ts`'s in-content refresh button both invoke it by id — see
 * `commands.ts`'s module doc comment for why there is exactly one definition of "refresh
 * everything").
 */
export const REFRESH_ALL_COMMAND = 'squads.refreshAll';
