/**
 * Extension-host smoke suite — run inside a real VS Code Extension Development Host by
 * `@vscode/test-electron`'s `runTests()` (see `../runTest.ts`). Scaffold only: exercising the
 * real "sidebar tree loads, preview opens" flow needs a live squad workspace opened in the
 * host plus headless-display CI wiring that is a tracked follow-up, not implemented here —
 * see the task handoff for the note. `run()` is the entry point `@vscode/test-electron`
 * expects; left empty (a no-op pass) rather than a fake assertion, so it doesn't misreport an
 * untested flow as a passing smoke test.
 */
export async function run(): Promise<void> {
  // Follow-up: open a scratch squad workspace in the host, await the `squadsTree` view
  // populating, select a node, and assert the `squads:` preview document opens with content.
}
