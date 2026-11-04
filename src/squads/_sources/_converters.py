"""Converters: pure functions of a tracker's text, base URL and issue URL, with no network access.

The table names each converter and where it lives, so reading the names, as the sources loader
does to validate one, imports none of them."""

import re
import urllib.parse
from collections.abc import Callable
from importlib import import_module

type Converter = Callable[[str, str, str], str]

#: The target of a markdown link or image: ``](target)`` or ``](target "title")``.
_MD_TARGET_RE = re.compile(r"(\]\()([^)\s]+)")
_SCHEME_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
#: The part of a GitLab issue address after its project.
_ISSUE_PATH = "/-/issues/"
_UPLOADS = "/uploads/"


def gitlab_md(text: str, base_url: str, issue_url: str) -> str:
    """Markdown with each relative link and image target made absolute: an upload against the
    project of the issue at *issue_url*, any other against *base_url*."""
    base = base_url.rstrip("/")
    project = issue_url.partition(_ISSUE_PATH)[0] if _ISSUE_PATH in issue_url else base

    def absolute(match: re.Match[str]) -> str:
        target = match.group(2)
        if target.startswith(("#", "//")) or _SCHEME_RE.match(target):
            return match.group(0)
        root = project if target.startswith(_UPLOADS) else base
        return f"{match.group(1)}{root}/{target.lstrip('/')}"

    return _MD_TARGET_RE.sub(absolute, text)


#: A raw ``src`` or ``href`` attribute whose value is a relative address.
_HTML_TARGET_RE = re.compile(r"""(\b(?:src|href)=)(["'])([^"']+)\2""")
#: A link reference definition: ``[label]: target``.
_DEFINITION_RE = re.compile(r"^(\[[^\]\n]+\]:\s*)(\S+)", re.MULTILINE)


def _joined(target: str, issue_url: str) -> str:
    if target.startswith("#") or _SCHEME_RE.match(target):
        return target
    return urllib.parse.urljoin(issue_url, target)


def github_md(text: str, base_url: str, issue_url: str) -> str:
    """Markdown with each relative link, image, reference definition and ``src``/``href``
    attribute resolved against the issue at *issue_url* (*base_url* when it is empty); nothing is
    downloaded."""
    where = issue_url or base_url
    text = _MD_TARGET_RE.sub(lambda m: f"{m.group(1)}{_joined(m.group(2), where)}", text)
    text = _DEFINITION_RE.sub(lambda m: f"{m.group(1)}{_joined(m.group(2), where)}", text)
    return _HTML_TARGET_RE.sub(
        lambda m: f"{m.group(1)}{m.group(2)}{_joined(m.group(3), where)}{m.group(2)}", text
    )


CONVERTERS: dict[str, str] = {
    "adf": "squads._sources._jira:adf",
    "gitlab-md": "squads._sources._converters:gitlab_md",
    "github-md": "squads._sources._converters:github_md",
    "jira-wiki": "squads._sources._jira:jira_wiki",
}


def load_converter(name: str) -> Converter:
    """The converter function *name* names, imported now."""
    module, _, function = CONVERTERS[name].partition(":")
    loaded: Converter = getattr(import_module(module), function)
    return loaded
