---
summary: Validate workflow YAML with fetched actionlint, not skipped
created_at: '2026-08-15T13:06:44Z'
---
No actionlint on PATH and pip/pyyaml aren't preinstalled outside the project venv. Fetch the static binary instead of skipping validation:

```
curl -s https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash | bash
```

Drops a standalone `actionlint` binary in the cwd (put it in scratchpad, not the repo). `uv run python` already has PyYAML if a second, independent YAML parse is wanted.

Also useful for verifying a publish landed without new credentials: both `https://pypi.org/pypi/<project>/<version>/json` and the VS Code Marketplace's `extensionquery` POST endpoint (`https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery`) are public/unauthenticated and safe to curl read-only to confirm a version is live.