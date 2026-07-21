/**
 * `onDidAccept` fires both for "open this result" (an item is selected) and for "Enter with
 * nothing selected yet" (the debounce-bypass submit path — see `searchRunner.ts`'s `submit`).
 * This resolves a `QuickPickItem`-shaped selection to that decision — pure/vscode-free so the
 * id-resolution is unit-testable without a host. The actual dispatch (hiding the picker, calling
 * into `ItemPreviewManager`) is vscode wiring, exercised by the extension-host smoke path,
 * mirroring the existing item-preview split.
 */

export type AcceptDecision =
  { readonly kind: 'open'; readonly itemId: string } | { readonly kind: 'submit' };

/** `selected` is `quickPick.selectedItems[0]` — `undefined` when nothing is currently
 * selected/active (an empty results list, or a query still in flight). */
export function decideAccept(selected: { readonly itemId: string } | undefined): AcceptDecision {
  return selected === undefined ? { kind: 'submit' } : { kind: 'open', itemId: selected.itemId };
}
