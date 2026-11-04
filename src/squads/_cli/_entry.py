"""The root application with its eagerly registered commands: the entry point `squads._cli` exposes.

The command modules decorate `app` as they are imported; `_import`, `_main` and `_ui` are
imported for that and never referenced by name.
"""

from squads._cli import _import as _import
from squads._cli import _main as _main
from squads._cli import _ui as _ui
from squads._cli._app import app as app
from squads._cli._app import main as main
from squads._cli._app import run as run
