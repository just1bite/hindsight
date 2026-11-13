"""Tests for single admin authentication in Hindsight API."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hindsight_api.auth import AuthMiddleware, auth_router


def create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(auth_router)

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    @app.get("/v1/default/banks")
    def list_banks():
        return [{"id": "test-bank"}]

    @app.get("/mcp/test-bank/")
    def mcp_endpoint():
        return {"mcp": "ok"}

    app.add_middleware(AuthMiddleware)
    return app


def test_auth_disabled_by_default(monkeypatch):
    monkeypatch.delenv("AUTH_ENABLED", raising=False)
    monkeypatch.delenv("HINDSIGHT_API_AUTH_ENABLED", raising=False)

    app = create_test_app()
    client = TestClient(app)

    # Protected endpoint works without auth
    res = client.get("/v1/default/banks")
    assert res.status_code == 200
    assert res.json() == [{"id": "test-bank"}]


def test_auth_enabled_flow(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_USERNAME", "admin")
    monkeypatch.setenv("AUTH_PASSWORD", "secret123")
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret-key")

    app = create_test_app()
    client = TestClient(app)

    # 1. Exempt routes work
    res = client.get("/health")
    assert res.status_code == 200

    # 2. Protected routes return 401
    res = client.get("/v1/default/banks")
    assert res.status_code == 401
    assert "Unauthorized" in res.json().get("detail", "")

    # 3. Login with wrong credentials fails
    res = client.post("/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert res.status_code == 401

    # 4. Login with correct credentials succeeds
    res = client.post("/auth/login", json={"username": "admin", "password": "secret123"})
    assert res.status_code == 200
    data = res.json()
    token = data["access_token"]
    assert token
    assert data["username"] == "admin"

    # 5. Protected route succeeds with Bearer token
    res = client.get("/v1/default/banks", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json() == [{"id": "test-bank"}]

    # 6. /auth/me returns current user
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["username"] == "admin"

    # 7. Protected route succeeds with cookie
    res = client.get("/v1/default/banks", cookies={"access_token": token})
    assert res.status_code == 200

    # 8. MCP route allowed by default
    res = client.get("/mcp/test-bank/")
    assert res.status_code == 200


def test_auth_api_key_access(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_API_KEY", "my-static-api-key")
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret-key")

    app = create_test_app()
    client = TestClient(app)

    # Access using static API key
    res = client.get("/v1/default/banks", headers={"Authorization": "Bearer my-static-api-key"})
    assert res.status_code == 200

    res = client.get("/v1/default/banks", headers={"X-API-Key": "my-static-api-key"})
    assert res.status_code == 200
