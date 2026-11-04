"""A small JSON-over-HTTP client on the standard library: pagination, backoff on rate limits and
timeouts, with no third-party dependency."""

import http.client
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator, Mapping
from email.message import Message
from http.client import HTTPMessage
from typing import Any, cast

from squads import _clock as clock
from squads._errors import SquadsError
from squads._sources._records import mapping

DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 4
#: The longest a single wait for a rate limit may take, in seconds.
MAX_WAIT = 60.0
#: The most pages one listing follows, so a tracker repeating its cursor cannot loop for ever.
MAX_PAGES = 5000
_LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})
_TRANSIENT = frozenset({502, 503, 504})
_NOT_FOUND = frozenset({404, 410})
_PAGE_SIZE = "100"
_TOO_MANY = 429
_FORBIDDEN = 403
_DETAIL_LIMIT = 200
_NETWORK_ERRORS = (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError)


class NotFoundError(SquadsError):
    """The tracker answered 404 or 410."""


class UnreachableError(SquadsError):
    """No answer came from the tracker's host: it could not be reached or timed out."""


class RejectedError(SquadsError):
    """The tracker answered 401 or 403: it refused the credential or the scope it carries."""


class RateLimitedError(SquadsError):
    """The tracker kept asking to slow down until the retries ran out."""


class StatusError(SquadsError):
    """The tracker refused a request with an HTTP status other than 401, 403 or 404."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


class UnexpectedAnswerError(SquadsError):
    """The tracker answered, but not with the document the request was for."""


class MalformedAnswerError(ValueError):
    """A tracker answer that is not the document the caller expects; the client names the URL."""


#: Given a page's document, headers and the query that fetched it, the query of the next page, or
#: ``None`` after the last.
type Advance = Callable[[Any, Message, Mapping[str, str]], dict[str, str] | None]
#: The elements of a page's document; raises ``MalformedAnswerError`` when it is not one.
type Items = Callable[[Any], list[Any]]


def _elements(found: Any, *, objects: bool) -> list[Any]:
    """The elements of the JSON array *found*; it must be an array, and hold objects only when
    *objects* is set."""
    if not isinstance(found, list):
        raise MalformedAnswerError
    elements = list(cast("list[Any]", found))
    if objects and not all(isinstance(e, dict) for e in elements):
        raise MalformedAnswerError
    return elements


def list_items(document: Any) -> list[Any]:
    """*document* as a JSON array of objects; anything else is a malformed answer."""
    return _elements(document, objects=True)


def member_items(key: str, *, objects: bool = True) -> Items:
    """The elements of the array under *key* of a JSON object page."""

    def items(document: Any) -> list[Any]:
        return _elements(mapping(document).get(key), objects=objects)

    return items


def next_page_header(
    _document: Any, headers: Message, params: Mapping[str, str]
) -> dict[str, str] | None:
    """The next query of a tracker that names the following page in ``X-Next-Page``."""
    following = headers.get("X-Next-Page")
    return {**params, "page": following} if following else None


_NEXT_LINK_RE = re.compile(r'<([^>]*)>\s*;\s*rel="?next"?')


def next_page_link(
    _document: Any, headers: Message, _params: Mapping[str, str]
) -> dict[str, str] | None:
    """The next query of a tracker that names the following page in a ``Link`` header: the query
    string of its ``rel="next"`` address."""
    for value in headers.get_all("Link") or []:
        found = _NEXT_LINK_RE.search(value)
        if found:
            return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(found.group(1)).query))
    return None


def _origin(url: str) -> tuple[str, str, int | None]:
    parts = urllib.parse.urlsplit(url)
    return parts.scheme, (parts.hostname or "").lower(), parts.port


def _detail(body: bytes) -> str:
    """A short printable reason from an error answer's JSON body (a ``message``, or the first of
    Jira's ``errorMessages``), or an empty string."""
    try:
        document = mapping(json.loads(body.decode("utf-8")))
    except ValueError:
        return ""
    found: Any = document.get("message") or document.get("errorMessages")
    if isinstance(found, list):
        found = next(iter(cast("list[Any]", found)), None)
    if not isinstance(found, str):
        return ""
    return "".join(c if c.isprintable() else " " for c in found).strip()[:_DETAIL_LIMIT]


def _rate_limited(exc: urllib.error.HTTPError, reason: str) -> bool:
    """Whether *exc* is a tracker's request to slow down: a 429, or a 403 that carries a wait or
    names a rate limit (GitHub's limits answer 403)."""
    if exc.code == _TOO_MANY:
        return True
    headers = exc.headers
    return exc.code == _FORBIDDEN and (
        headers.get("Retry-After") is not None
        or headers.get("X-RateLimit-Remaining") == "0"
        or "rate limit" in reason.lower()
    )


class _SameOriginRedirects(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only within the tracker's own scheme, host and port, so the credential
    travels nowhere else."""

    def __init__(self, base_url: str) -> None:
        self._origin = _origin(base_url)

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        target = urllib.parse.urljoin(req.full_url, newurl)
        if _origin(target) != self._origin:
            raise SquadsError(
                f"{req.full_url} redirected to {target}, which is not the tracker's own address; "
                "the credential is not sent there. Set the source's base_url to the final address"
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class HttpClient:
    """GET requests against one tracker base URL, authenticated by fixed headers."""

    def __init__(
        self,
        base_url: str,
        headers: Mapping[str, str],
        *,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._headers = dict(headers)
        self._timeout = timeout
        self._retries = retries
        self._sleep = sleep
        host = urllib.parse.urlsplit(base_url).hostname or ""
        handlers: list[urllib.request.BaseHandler] = [_SameOriginRedirects(base_url)]
        if host in _LOOPBACK:
            handlers.append(urllib.request.ProxyHandler({}))
        self._opener = urllib.request.build_opener(*handlers)

    def _url(self, path: str, params: Mapping[str, str]) -> str:
        query = urllib.parse.urlencode(params)
        return f"{self._base}{path}" + (f"?{query}" if query else "")

    def _wait(self, headers: Message, attempt: int) -> float:
        """Seconds to wait before retrying: the tracker's own hint, else exponential."""
        retry_after = headers.get("Retry-After")
        if retry_after is not None:
            try:
                return min(max(float(retry_after), 0.0), MAX_WAIT)
            except ValueError:
                pass
        for name in ("RateLimit-Reset", "X-RateLimit-Reset"):
            reset = headers.get(name)
            if reset is not None:
                try:
                    return min(max(float(reset) - clock.now().timestamp(), 0.0), MAX_WAIT)
                except ValueError:
                    pass
        return min(float(2**attempt), MAX_WAIT)

    def _open(self, url: str) -> tuple[Any, Message]:
        """The JSON document at *url* and the response headers, retrying a rate limit."""
        request = urllib.request.Request(url, headers=self._headers)
        for attempt in range(self._retries + 1):
            try:
                with self._opener.open(request, timeout=self._timeout) as response:
                    return json.loads(response.read().decode("utf-8")), response.headers
            except urllib.error.HTTPError as exc:
                reason = _detail(exc.read())
                if exc.code in _NOT_FOUND:
                    raise NotFoundError(f"{url}: not found") from exc
                limited = _rate_limited(exc, reason)
                if (limited or exc.code in _TRANSIENT) and attempt < self._retries:
                    self._sleep(self._wait(exc.headers, attempt))
                    continue
                if limited:
                    raise RateLimitedError(
                        f"{self._base} is rate limiting requests (HTTP {exc.code}); try again later"
                    ) from exc
                if exc.code in (401, 403):
                    raise RejectedError(
                        f"{self._base} rejected the credential (HTTP {exc.code})"
                    ) from exc
                raise StatusError(
                    exc.code,
                    f"{self._base} answered HTTP {exc.code} for {url}"
                    + (f": {reason}" if reason else ""),
                ) from exc
            except ValueError as exc:
                raise UnexpectedAnswerError(
                    f"{self._base} answered something other than JSON for {url}"
                ) from exc
            except _NETWORK_ERRORS as exc:
                raise UnreachableError(f"cannot reach {self._base}: {exc}") from exc
        raise RateLimitedError(f"{self._base} is rate limiting requests; try again later")

    def get(self, path: str, params: Mapping[str, str] | None = None) -> Any:
        """The JSON document at *path*."""
        document, _ = self._open(self._url(path, params or {}))
        return document

    def paged(
        self, path: str, params: Mapping[str, str], advance: Advance, items: Items
    ) -> Iterator[Any]:
        """Every element of a paginated listing: *items* reads a page's elements and *advance* says
        where the next page is, until it answers ``None`` or the page limit is reached."""
        query: dict[str, str] | None = dict(params)
        for _ in range(MAX_PAGES):
            if query is None:
                return
            url = self._url(path, query)
            document, headers = self._open(url)
            try:
                found = items(document)
            except MalformedAnswerError as exc:
                raise UnexpectedAnswerError(
                    f"{self._base} answered something unexpected for {url}"
                ) from exc
            yield from found
            query = advance(document, headers, query)
        raise SquadsError(f"{self._base} kept paging {path} past {MAX_PAGES} pages")

    def link_pages(self, path: str, params: Mapping[str, str] | None = None) -> Iterator[Any]:
        """Every element of a paginated JSON array, following the tracker's ``Link`` header."""
        first = {**(params or {}), "per_page": _PAGE_SIZE}
        return self.paged(path, first, next_page_link, list_items)

    def pages(self, path: str, params: Mapping[str, str] | None = None) -> Iterator[Any]:
        """Every element of a paginated JSON array, following the tracker's next-page header."""
        first = {**(params or {}), "per_page": _PAGE_SIZE, "page": "1"}
        return self.paged(path, first, next_page_header, list_items)
