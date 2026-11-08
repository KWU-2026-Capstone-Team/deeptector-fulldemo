"""Public-deployment switches: game API off, per-IP session issuance limit."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "data" / "test.sqlite3",
        storage_dir=tmp_path / "storage",
        model_dir=tmp_path / "models",
        inference_mode="demo",
    )


def test_games_enabled_by_default(settings):
    assert settings.games_enabled is True
    with TestClient(create_app(settings)) as client:
        token = client.post("/api/v1/sessions").json()["token"]
        response = client.get("/api/v1/games", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200


def test_games_disabled_removes_game_api(settings):
    with TestClient(create_app(replace(settings, games_enabled=False))) as client:
        token = client.post("/api/v1/sessions").json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        assert client.get("/api/v1/games", headers=headers).status_code == 404
        assert client.post("/api/v1/games", json={"rounds": 3}, headers=headers).status_code == 404
        assert not any(path.startswith("/api/v1/games") for path in client.get("/openapi.json").json()["paths"])
        # Analysis API is unaffected.
        assert client.get("/api/v1/analyses", headers=headers).status_code == 200


def test_session_rate_limit_per_ip(settings):
    with TestClient(create_app(replace(settings, session_rate_per_ip_hour=2))) as client:
        assert client.post("/api/v1/sessions").status_code == 201
        assert client.post("/api/v1/sessions").status_code == 201
        limited = client.post("/api/v1/sessions")
        assert limited.status_code == 429
        assert limited.json()["error"]["code"] == "RATE_LIMITED"


def test_session_rate_limit_uses_trusted_proxy_header(settings):
    limited = replace(settings, session_rate_per_ip_hour=1, client_ip_header="cf-connecting-ip")
    with TestClient(create_app(limited)) as client:
        first = {"CF-Connecting-IP": "198.51.100.1", "X-Forwarded-For": "1.1.1.1"}
        assert client.post("/api/v1/sessions", headers=first).status_code == 201
        # A spoofed X-Forwarded-For does not reset the limit for the same real client.
        spoofed = {"CF-Connecting-IP": "198.51.100.1", "X-Forwarded-For": "9.9.9.9"}
        assert client.post("/api/v1/sessions", headers=spoofed).status_code == 429
        assert client.post("/api/v1/sessions", headers={"CF-Connecting-IP": "198.51.100.2"}).status_code == 201


def test_session_rate_limit_off_by_default(settings):
    with TestClient(create_app(settings)) as client:
        assert all(client.post("/api/v1/sessions").status_code == 201 for _ in range(5))


def test_env_flags(monkeypatch):
    monkeypatch.setenv("DEEPTECTOR_ENABLE_GAMES", "0")
    monkeypatch.setenv("DEEPTECTOR_SESSION_RATE_PER_IP_HOUR", "20")
    configured = Settings.from_env()
    assert configured.games_enabled is False
    assert configured.session_rate_per_ip_hour == 20
    monkeypatch.setenv("DEEPTECTOR_ENABLE_GAMES", "maybe")
    with pytest.raises(ValueError):
        Settings.from_env()
