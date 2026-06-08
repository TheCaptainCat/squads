"""Jinja2 environment for generating item files and Claude Code artifacts.

Templates are package data under ``templates/``. ``StrictUndefined`` makes a missing variable a
loud error rather than a silent blank.
"""

from functools import lru_cache

from jinja2 import Environment, PackageLoader, StrictUndefined

from squads._util import slugify


@lru_cache(maxsize=1)
def _env() -> Environment:
    env = Environment(
        loader=PackageLoader("squads._rendering", "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
        # Templates render Markdown/TOML/JSON files (never HTML served to a browser), so HTML
        # autoescaping would corrupt output (e.g. turn `>` into `&gt;`). Safe to disable here.
        autoescape=False,
    )
    env.filters["slugify"] = slugify
    return env


def render(template_name: str, /, **context: object) -> str:
    return _env().get_template(template_name).render(**context)
