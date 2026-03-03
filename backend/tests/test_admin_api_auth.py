"""관리자 API 헤더 인증 테스트."""

from collections import deque

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.admin_routes import admin_router
from app.api.routes import router
from app.cache import cache
from app.config import settings
from app.rules.product_loader import clear_cache


@pytest.fixture(autouse=True)
def reset_in_memory_cache():
    """테스트 간 캐시 오염 방지."""
    cache.policy_products.clear()
    cache.bank_rates.clear()
    cache.bank_avg_rates.clear()
    cache.hf_news.clear()
    cache.fetch_last_success.clear()
    cache.fetch_logs = deque(maxlen=100)
    clear_cache()
    yield
    cache.policy_products.clear()
    cache.bank_rates.clear()
    cache.bank_avg_rates.clear()
    cache.hf_news.clear()
    cache.fetch_last_success.clear()
    cache.fetch_logs = deque(maxlen=100)
    clear_cache()


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.include_router(admin_router, prefix="/api/admin")
    return TestClient(app)


def test_admin_status_requires_header(monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", "test-admin-key")
    response = _client().get("/api/admin/status")
    assert response.status_code == 401
    assert response.json()["detail"] == "관리자 인증에 실패했어요."


def test_admin_status_rejects_invalid_header(monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", "test-admin-key")
    response = _client().get("/api/admin/status", headers={"X-Admin-Key": "wrong-key"})
    assert response.status_code == 401
    assert response.json()["detail"] == "관리자 인증에 실패했어요."


def test_admin_status_returns_503_when_key_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", "")
    response = _client().get("/api/admin/status", headers={"X-Admin-Key": "any"})
    assert response.status_code == 503
    assert response.json()["detail"] == "관리자 인증키가 설정되지 않았어요."


def test_refresh_all_accepts_valid_header(monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", "test-admin-key")

    async def fake_run_all_fetchers():
        return {"didimdol": "success", "bogeumjari": "success"}

    monkeypatch.setattr("app.fetchers.scheduler.run_all_fetchers", fake_run_all_fetchers)

    response = _client().post("/api/admin/refresh-all", headers={"X-Admin-Key": "test-admin-key"})
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "results": {"didimdol": "success", "bogeumjari": "success"},
    }
