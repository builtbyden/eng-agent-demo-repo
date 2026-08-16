"""Passes today. Deliberately does not exercise the 429/503 retry path —
that gap is BUG(5) in src/api_client.py's docstring."""

from __future__ import annotations

import sys
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
