/**
 * The `squads:` read-only `TextDocumentContentProvider`: resolves `sq`, shells out via
 * `getRaw`, and renders the outcome through the vscode-free `domain/showPreview` helpers. A
 * failure still returns document text (an actionable message) rather than leaving a blank/stale
 * preview, alongside a VS Code notification.
 */
import * as vscode from 'vscode';

import { describeTriedOrder, SqDiscovery } from './discovery';
import { extractIdFromUriPath, renderShowOutcome } from './domain/showPreview';
import type { ProcessRunner } from './processRunner';
import { describeFailure, getRaw } from './sqAdapter';

export class SquadsShowDocumentProvider implements vscode.TextDocumentContentProvider {
  constructor(
    private readonly runner: ProcessRunner,
    private readonly discovery: SqDiscovery,
    private readonly workspaceRoot: string,
    private readonly notifyError: (message: string) => void,
  ) {}

  async provideTextDocumentContent(uri: vscode.Uri): Promise<string> {
    const id = extractIdFromUriPath(uri.path);
    const resolution = this.discovery.resolve();
    if (!resolution.ok) {
      const message = `No sq invocation found. Tried, in order: ${describeTriedOrder(resolution.triedOrder)}.`;
      this.notifyError(`Squads: ${message}`);
      return renderShowOutcome(id, { kind: 'spawn-error', message });
    }
    const outcome = await getRaw(this.runner, resolution.invocation, this.workspaceRoot, id);
    if (outcome.kind !== 'success') {
      if (outcome.kind === 'spawn-error') {
        this.discovery.invalidate();
      }
      this.notifyError(`Squads: ${describeFailure(outcome)}`);
    }
    return renderShowOutcome(id, outcome);
  }
}
