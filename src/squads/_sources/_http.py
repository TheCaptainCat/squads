"""A small JSON-over-HTTP client on the standard library: pagination, backoff on rate limits and
timeouts, with no third-party dependency."""

import json
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

DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 4
#: The longest a single wait for a rate limit may take, in seconds.
MAX_WAIT = 60.0
_LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})
_RETRYABLE = frozenset({429, 502, 503, 504})
_PAGE_SIZE = "100"


class NotFoundError(SquadsError):
    """The tracker answered 404."""


class UnreachableError(SquadsError):
    """No answer came from the tracker's host: it could not be reached or timed out."""


class RejectedError(SquadsError):
    """The tracker answered 401 or 403: it refused the credential or the scope it carries."""


def _origin(url: str) -> tuple[str, str, int | None]:
    parts = urllib.parse.urlsplit(url)
    return parts.scheme, (parts.hostname or "").lower(), parts.port


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
        reset = headers.get("RateLimit-Reset")
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
                if exc.code == 404:
                    raise NotFoundError(f"{url}: not found") from exc
                if exc.code in (401, 403):
                    raise RejectedError(
                        f"{self._base} rejected the credential (HTTP {exc.code})"
                    ) from exc
                if exc.code in _RETRYABLE and attempt < self._retries:
                    self._sleep(self._wait(exc.headers, attempt))
                    continue
                raise SquadsError(f"{self._base} answered HTTP {exc.code} for {url}") from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:  # fmt: skip
                raise UnreachableError(f"cannot reach {self._base}: {exc}") from exc
        raise SquadsError(f"{self._base} kept rate limiting {url}")

    def get(self, path: str, params: Mapping[str, str] | None = None) -> Any:
        """The JSON document at *path*."""
        document, _ = self._open(self._url(path, params or {}))
        return document

    def pages(self, path: str, params: Mapping[str, str] | None = None) -> Iterator[Any]:
        """Every element of a paginated JSON array, following the tracker's next-page header."""
        page = "1"
        while page:
            query = {**(params or {}), "per_page": _PAGE_SIZE, "page": page}
            document, headers = self._open(self._url(path, query))
            yield from cast("list[Any]", document)
            page = headers.get("X-Next-Page") or ""
