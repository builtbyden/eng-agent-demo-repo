from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from api_client import ApiClient, ApiError, Response


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


def test_get_retries_on_429_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        Response(status=429, body={}),
        Response(status=429, body={}),
        Response(status=200, body={"ok": True}),
    ]
    calls = {"count": 0}

    def fake_send(path: str, timeout: float) -> Response:
        calls["count"] += 1
        return responses[calls["count"] - 1]

    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    client = ApiClient("https://example.invalid")
    monkeypatch.setattr(client, "_send", fake_send)

    assert client.get("/widgets") == {"ok": True}
    assert calls["count"] == 3


def test_get_retries_on_503_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        Response(status=503, body={}),
        Response(status=200, body={"ok": True}),
    ]
    calls = {"count": 0}

    def fake_send(path: str, timeout: float) -> Response:
        calls["count"] += 1
        return responses[calls["count"] - 1]

    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    client = ApiClient("https://example.invalid")
    monkeypatch.setattr(client, "_send", fake_send)

    assert client.get("/widgets") == {"ok": True}
    assert calls["count"] == 2


def test_get_raises_after_exhausting_max_attempts_on_429(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def fake_send(path: str, timeout: float) -> Response:
        calls["count"] += 1
        return Response(status=429, body={})

    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    client = ApiClient("https://example.invalid")
    monkeypatch.setattr(client, "_send", fake_send)

    with pytest.raises(ApiError):
        client.get("/widgets", max_attempts=3)
    assert calls["count"] == 3


def test_get_raises_after_exhausting_max_attempts_on_503(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def fake_send(path: str, timeout: float) -> Response:
        calls["count"] += 1
        return Response(status=503, body={})

    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    client = ApiClient("https://example.invalid")
    monkeypatch.setattr(client, "_send", fake_send)

    with pytest.raises(ApiError):
        client.get("/widgets", max_attempts=3)
    assert calls["count"] == 3


def test_get_honors_retry_after_header_over_computed_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        Response(status=429, body={}, headers={"Retry-After": "2"}),
        Response(status=200, body={"ok": True}),
    ]
    calls = {"count": 0}
    sleeps: list[float] = []

    def fake_send(path: str, timeout: float) -> Response:
        calls["count"] += 1
        return responses[calls["count"] - 1]

    monkeypatch.setattr(time, "sleep", lambda seconds: sleeps.append(seconds))
    client = ApiClient("https://example.invalid")
    monkeypatch.setattr(client, "_send", fake_send)

    client.get("/widgets", max_wait=30.0)
    assert sleeps == [2.0]


def test_get_caps_delay_at_max_wait_even_with_large_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        Response(status=503, body={}, headers={"Retry-After": "9999"}),
        Response(status=200, body={"ok": True}),
    ]
    calls = {"count": 0}
    sleeps: list[float] = []

    def fake_send(path: str, timeout: float) -> Response:
        calls["count"] += 1
        return responses[calls["count"] - 1]

    monkeypatch.setattr(time, "sleep", lambda seconds: sleeps.append(seconds))
    client = ApiClient("https://example.invalid")
    monkeypatch.setattr(client, "_send", fake_send)

    client.get("/widgets", max_wait=5.0)
    assert sleeps == [5.0]
