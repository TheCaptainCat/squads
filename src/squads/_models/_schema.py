"""The durable on-disk schema version this code reads and writes.

Single source of truth, kept dependency-free so both the models (`_config`, `_index`) and the
migration registry can import it without an import cycle. Bump it in lock-step with adding a runner
to `squads._migrations._registry`.
"""

SCHEMA_VERSION = 2
