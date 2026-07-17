---
summary: Pin the VS Code client's TypeScript at 6.0.x, not TS7 — typescript-eslint
  (the type-aware strict gate) peer-caps below 6.1.
created_at: '2026-07-17T09:29:50Z'
---
The type-aware lint gate (`typescript-eslint`) is the ceiling: its latest (8.64.0) and canary peer-support `typescript >=4.8.4 <6.1.0`, and there is no v9/next/TS7 line yet. So **6.0.3 is the newest TypeScript that keeps the strict gate** — a full major over the old 5.9.3 pin.

Do **not** jump to TS7 (the native Go rewrite): it would force dropping type-aware linting, which weakens the Python-parity gate we committed to. Biome/oxlint are **not** type-aware substitutes — they don't run the type-checker, so they can't reproduce the type-aware rules (`no-floating-promises`, the `no-unsafe-*` family, etc.) that *are* the gate.

Revisit only when `typescript-eslint` ships TS7 support — the team board carries a notice to check periodically.