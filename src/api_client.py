"""A tiny synthetic HTTP client used only as a demo/eval fixture.

`_send` is the seam: real code would perform an HTTP request here. Tests
monkeypatch it to return canned `Response` objects — nothing in this module
touches the network.
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


def _is_retryable(status: int) -> bool:
    return status in (429, 503)


def _backoff_delay(attempt: int, max_wait: float) -> float:
    """Exponential backoff, capped at `max_wait` seconds between attempts."""

    return min(0.5 * (2 ** (attempt - 1)), max_wait)


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def _send(self, path: str, timeout: float) -> Response:  # pragma: no cover - real I/O seam
        raise NotImplementedError("real network I/O — replace/monkeypatch in tests")

    def get(
        self,
        path: str,
        *,
        timeout: float = 5.0,
        max_wait: float = 30.0,
        max_attempts: int = 5,
    ) -> dict:
        """Fetch `path`, retrying on 429/503 with exponential backoff.

        Backoff between attempts is capped at `max_wait` seconds. A server's
        `Retry-After` header, when present, is honored instead of the
        computed backoff (still bounded by `max_wait`). After `max_attempts`
        attempts, raises `ApiError` instead of retrying again.
        """

        # BUG(3): input-validation gap — a non-positive timeout is silently
        # accepted instead of raising, and would be passed straight to
        # `_send` as-is.

        attempt = 0
        while True:
            attempt += 1
            response = self._send(path, timeout)

            if not _is_retryable(response.status):
                if response.status >= 400:
                    raise ApiError(f"request to {path} failed with status {response.status}")
                return response.body

            if attempt >= max_attempts:
                raise ApiError(
                    f"request to {path} failed after {max_attempts} attempts "
                    f"with status {response.status}"
                )

            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                delay = min(float(retry_after), max_wait)
            else:
                delay = _backoff_delay(attempt, max_wait)
            time.sleep(delay)
