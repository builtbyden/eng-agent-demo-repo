from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from api_client import ApiClient, ApiError, Response, _backoff_delay


def test_get_returns_body_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ApiClient("https://example.invalid")
    monkeypatch.setattr(client, "_send", lambda path, timeout: Response(status=200, body={"ok": True}))
    assert client.get("/widgets") == {"ok": True}


def test_get_raises_on_non_retryable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ApiClient("https://example.invalid")
    monkeypatch.setattr(client, "_send", lambda path, timeout: Response(status=404, body={}))
    with pytest.raises(ApiError):
        client.get("/missing")


def test_get_passes_path_through(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def fake_send(path: str, timeout: float) -> Response:
        seen["path"] = path
        return Response(status=200, body={})

    client = ApiClient("https://example.invalid")
    monkeypatch.setattr(client, "_send", fake_send)
    client.get("/orders/42")
    assert seen["path"] == "/orders/42"


def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    recorded: list[float] = []

    def fake_sleep(seconds: float) -> None:
        recorded.append(seconds)

    monkeypatch.setattr("api_client.time.sleep", fake_sleep)
    return recorded


def test_get_retries_on_429_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    _no_sleep(monkeypatch)
    calls = {"n": 0}

    def fake_send(path: str, timeout: float) -> Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return Response(status=429, body={})
        return Response(status=200, body={"ok": True})

    client = ApiClient("https://example.invalid")
    monkeypatch.setattr(client, "_send", fake_send)
    assert client.get("/widgets") == {"ok": True}
    assert calls["n"] == 3


def test_get_retries_on_503_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    _no_sleep(monkeypatch)
    calls = {"n": 0}

    def fake_send(path: str, timeout: float) -> Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return Response(status=503, body={})
        return Response(status=200, body={"ok": True})

    client = ApiClient("https://example.invalid")
    monkeypatch.setattr(client, "_send", fake_send)
    assert client.get("/widgets") == {"ok": True}
    assert calls["n"] == 3


def test_get_raises_after_max_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    _no_sleep(monkeypatch)
    calls = {"n": 0}

    def fake_send(path: str, timeout: float) -> Response:
        calls["n"] += 1
        return Response(status=503, body={})

    client = ApiClient("https://example.invalid")
    monkeypatch.setattr(client, "_send", fake_send)
    with pytest.raises(ApiError):
        client.get("/widgets", max_attempts=4)
    assert calls["n"] == 4


def test_get_honors_retry_after_on_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded = _no_sleep(monkeypatch)
    calls = {"n": 0}

    def fake_send(path: str, timeout: float) -> Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return Response(status=429, body={}, headers={"Retry-After": "2"})
        return Response(status=200, body={"ok": True})

    client = ApiClient("https://example.invalid")
    monkeypatch.setattr(client, "_send", fake_send)
    assert client.get("/widgets") == {"ok": True}
    assert recorded == [2.0]


def test_backoff_delay_never_exceeds_max_wait() -> None:
    for attempt in range(1, 50):
        assert _backoff_delay(attempt, max_wait=30.0) <= 30.0
