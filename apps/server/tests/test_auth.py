import pytest

from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_login_and_current_user(client):
    http, first_tenant_id, _, _ = client
    response = await http.post("/api/v1/auth/login", json={"tenant_code": "first", "username": "admin", "password": "correct-password"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    current = await http.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert current.status_code == 200
    assert current.json()["tenant_id"] == first_tenant_id
    assert current.json()["tenant_code"] == "first"
    assert "password_hash" not in current.json()


@pytest.mark.asyncio
async def test_wrong_tenant_or_password_is_rejected(client):
    http, _, _, _ = client
    for tenant_code, password in [("second", "correct-password"), ("first", "wrong"), ("missing", "correct-password")]:
        response = await http.post("/api/v1/auth/login", json={"tenant_code": tenant_code, "username": "admin", "password": password})
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_valid_tenant_scoped_token(client):
    http, _, second_tenant_id, first_user_id = client
    assert (await http.get("/api/v1/auth/me")).status_code == 401
    assert (await http.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})).status_code == 401
    cross_tenant_token = create_access_token(first_user_id, second_tenant_id)
    assert (await http.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {cross_tenant_token}"})).status_code == 401
