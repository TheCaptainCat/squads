"""Layer-scoped fixtures for tests/integration/ only.

Cross-layer fixtures (frozen_time, project, svc, runner, invoke, the autouse leak-guards) live in
the root tests/conftest.py and are already visible here via pytest's normal conftest inheritance
— nothing needs re-importing. Add a fixture here only when it is integration-layer-specific, per
tests/CONVENTIONS.md. Empty for now.
"""
