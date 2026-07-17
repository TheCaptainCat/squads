// Vendors mermaid's pre-built browser bundle (dist/mermaid.min.js — the "batteries included"
// IIFE build meant for a plain `<script src>` tag, every diagram type statically bundled so it
// needs no dynamic import()/CDN fetch at runtime) into media/, the one webview asset the item
// preview's CSP-locked panel loads (see src/domain/previewDocument.ts, src/itemPreviewManager.ts).
//
// Run via `npm run compile` (which runs `vendor:mermaid` first) — media/ is git-ignored and
// reproducible from the pinned `mermaid` devDependency, the same way out/ is a build product
// rather than a committed artifact. Not part of the TypeScript build itself, so this is a plain
// CommonJS script, not compiled/type-checked (see eslint.config.mjs's ignore for this file).
const fs = require('node:fs');
const path = require('node:path');

const source = path.join(__dirname, '..', 'node_modules', 'mermaid', 'dist', 'mermaid.min.js');
const destDir = path.join(__dirname, '..', 'media');
const dest = path.join(destDir, 'mermaid.min.js');

fs.mkdirSync(destDir, { recursive: true });
fs.copyFileSync(source, dest);

console.log(
  `vendored ${path.relative(process.cwd(), source)} -> ${path.relative(process.cwd(), dest)}`,
);
