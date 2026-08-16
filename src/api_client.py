"""A tiny synthetic HTTP client used only as a demo/eval fixture.

`_send` is the seam: real code would perform an HTTP request here. Tests
monkeypatch it to return canned `Response` objects — nothing in this module
touches the network.

Six deliberate issues are marked BUG(n) below. `tests/test_api_client.py`
passes today precisely because none of its tests exercise the retry path.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


class ApiError(RuntimeError):
    pass


@dataclass
class Response:
    status: int
    body: dict
    headers: dict = field(default_factory=dict)


# BUG(6): `is` used to compare integers instead of `==`/`in`. This "usually
# works" for small literals CPython happens to intern, and quietly stops
# working for status codes that arrive as freshly-constructed ints (e.g.
# `int(json_value)`), which is exactly how a real HTTP client would produce
# them — Python even emits a SyntaxWarning ("is" with a literal) for this.
def _is_retryable(status: int) -> bool:
    return status is 429 or status is 503  # noqa: F632 -- intentional demo bug, see BUG(6)


def _backoff_delay(attempt: int, max_wait: float) -> float:
    """Exponential backoff, capped at `max_wait` seconds between attempts."""

    # BUG(4): requirement/implementation mismatch. The docstring above (and
    # this function's own `max_wait` parameter) promise a cap, but it is
    # never applied — delay grows unbounded with `attempt`.
    return 0.5 * (2 ** (attempt - 1))


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def _send(self, path: str, timeout: float) -> Response:  # pragma: no cover - real I/O seam
        raise NotImplementedError("real network I/O — replace/monkeypatch in tests")

    def get(self, path: str, *, timeout: float = 5.0, max_wait: float = 30.0) -> dict:
        """Fetch `path`, retrying on 429/503 with exponential backoff.

        Backoff between attempts is capped at `max_wait` seconds.
        """

        # BUG(3): input-validation gap — a non-positive timeout is silently
        # accepted instead of raising, and would be passed straight to
        # `_send` as-is.

        attempt = 0
        while True:  # BUG(1): no maximum attempt count — retries forever
            attempt += 1
            response = self._send(path, timeout)

            if not _is_retryable(response.status):
                if response.status >= 400:
                    raise ApiError(f"request to {path} failed with status {response.status}")
                return response.body

            # BUG(2): the server's Retry-After header is available on the
            # response but never read — we always use our own backoff
            # instead of honoring what the server asked for.
            delay = _backoff_delay(attempt, max_wait)
            time.sleep(delay)
