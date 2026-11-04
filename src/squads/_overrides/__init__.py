"""Project-level overrides: stamp, manifest, drift detection, and the sq override command group.

This package provides:

- :mod:`._manifest` — load the per-release content-hash manifest shipped as package data.
- :mod:`._stamp` — read/write the ``squads:override-base:<version>`` stamp in override files.
- :mod:`._service` — service-level logic (scaffold, diff, update, list)."""

from squads._overrides._manifest import PLAYBOOK_KEY as PLAYBOOK_KEY
from squads._overrides._manifest import WORKFLOW_KEY as WORKFLOW_KEY
from squads._overrides._manifest import artifact_changed_since as artifact_changed_since
from squads._overrides._service import STATE_BROKEN as STATE_BROKEN
from squads._overrides._service import STATE_DRIFTED as STATE_DRIFTED
from squads._overrides._service import OverrideEntry as OverrideEntry
from squads._overrides._service import check_override_issues as check_override_issues
from squads._overrides._service import diff_override as diff_override
from squads._overrides._service import scaffold_playbook as scaffold_playbook
from squads._overrides._service import scaffold_role as scaffold_role
from squads._overrides._service import scaffold_roles_catalog as scaffold_roles_catalog
from squads._overrides._service import scaffold_sources as scaffold_sources
from squads._overrides._service import scaffold_template as scaffold_template
from squads._overrides._service import scaffold_workflow as scaffold_workflow
from squads._overrides._service import scan_overrides as scan_overrides
from squads._overrides._service import update_stamp as update_stamp
