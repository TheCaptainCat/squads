"""Project-level overrides: stamp, manifest, drift detection, and the sq override command group.

ADR-000085 defines the full design.  This package provides:

- :mod:`._manifest` — load the per-release content-hash manifest shipped as package data.
- :mod:`._stamp` — read/write the ``squads:override-base:<version>`` stamp in override files.
- :mod:`._service` — service-level logic (scaffold, diff, update, list).
"""
