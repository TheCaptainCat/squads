"""The declared-view surface: resolve a ``[views]`` entry against one item, project it, and
optionally render it.

The mechanism itself (source resolution, projection, presentation) lives in ``squads._views`` —
a top-level module with no service dependency, the same layering ``squads._discussion`` already
has. This mixin is the one seam that loads the index and hands the already-open ``db`` to it,
so a resolve-and-render call costs one index load, matching ``sq tree``/``sq blocked``.
"""

from squads import _views as views
from squads._errors import SquadsError
from squads._index._resolver import require_item
from squads._services._base import ServiceCore
from squads._views import Projection


class ViewsMixin(ServiceCore):
    async def resolve_view(self, view_name: str, item_id: str) -> Projection:
        """The projection *view_name* produces when resolved against *item_id* — records,
        never presentation. Raises :class:`SquadsError` when *view_name* isn't declared."""
        view = self.spec.views.get(view_name)
        if view is None:
            raise SquadsError(
                f"no declared view {view_name!r}; see `sq workflow views` for the declared set"
            )
        db = await self.store.load()
        item = require_item(db, item_id)
        records = views.resolve_records(view, view_name, item, db, self.spec)
        return views.project(view, records, self.spec)

    async def render_view(self, view_name: str, item_id: str) -> str:
        """*view_name* resolved against *item_id* and rendered through its declared
        presentation template — one index load, then the same Jinja2 engine every other
        rendering path uses."""
        projection = await self.resolve_view(view_name, item_id)
        return views.render_view(view_name, projection)
