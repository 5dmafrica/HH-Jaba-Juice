import pytest
from fastapi.testclient import TestClient

from backend import server


client = TestClient(server.app)


def test_get_effective_role_prefers_active_role():
    user = {
        "role": "super_admin",
        "active_role": "admin",
    }

    assert server.get_effective_role(user) == "admin"


def test_add_approved_domain_normalizes_input(monkeypatch):
    actor = {
        "user_id": "sa_1",
        "email": "mavin@5dm.africa",
        "name": "Super Admin",
        "role": "super_admin",
    }
    executed = []

    async def fake_get_super_admin_user(request):
        return actor

    async def fake_fetchone(sql, params=None):
        if "SELECT * FROM approved_domains" in sql:
            return None
        if "SELECT domain, is_active" in sql:
            return {
                "domain": "newdomain.africa",
                "is_active": 1,
                "added_by": "Super Admin",
                "disabled_by": None,
                "created_at": "2026-03-30T00:00:00",
                "updated_at": "2026-03-30T00:00:00",
                "disabled_at": None,
            }
        return None

    async def fake_execute(sql, params=None):
        executed.append((sql, params))
        return 1

    async def fake_audit(*args, **kwargs):
        return None

    monkeypatch.setattr(server, "get_super_admin_user", fake_get_super_admin_user)
    monkeypatch.setattr(server, "db_fetchone", fake_fetchone)
    monkeypatch.setattr(server, "db_execute", fake_execute)
    monkeypatch.setattr(server, "create_admin_audit_log", fake_audit)

    response = client.post("/api/admin/domains", json={"domain": "@NewDomain.Africa"})

    assert response.status_code == 200
    assert response.json()["domain"] == "newdomain.africa"
    assert any("INSERT INTO approved_domains" in sql for sql, _ in executed)


def test_disable_last_active_domain_is_blocked(monkeypatch):
    actor = {
        "user_id": "sa_1",
        "email": "mavin@5dm.africa",
        "name": "Super Admin",
        "role": "super_admin",
    }

    async def fake_get_super_admin_user(request):
        return actor

    async def fake_fetchone(sql, params=None):
        return {
            "domain": "5dm.africa",
            "is_active": 1,
        }

    async def fake_count(sql, params=None):
        return 1

    monkeypatch.setattr(server, "get_super_admin_user", fake_get_super_admin_user)
    monkeypatch.setattr(server, "db_fetchone", fake_fetchone)
    monkeypatch.setattr(server, "db_count", fake_count)

    response = client.delete("/api/admin/domains/5dm.africa")

    assert response.status_code == 400
    assert response.json()["detail"] == "At least one approved domain must remain active"


def test_update_user_role_persists_new_role(monkeypatch):
    actor = {
        "user_id": "sa_1",
        "email": "mavin@5dm.africa",
        "name": "Super Admin",
        "role": "super_admin",
    }
    state = {
        "target": {
            "user_id": "user_1",
            "email": "user@5dm.africa",
            "name": "Regular User",
            "role": "user",
            "active_role": "user",
        }
    }
    executed = []

    async def fake_get_super_admin_user(request):
        return actor

    async def fake_fetchone(sql, params=None):
        if "SELECT * FROM users WHERE user_id=%s" in sql:
            return dict(state["target"])
        return None

    async def fake_execute(sql, params=None):
        executed.append((sql, params))
        if sql.startswith("UPDATE users SET role=%s"):
            state["target"]["role"] = params[0]
            state["target"]["active_role"] = params[1]
        return 1

    async def fake_audit(*args, **kwargs):
        return None

    monkeypatch.setattr(server, "get_super_admin_user", fake_get_super_admin_user)
    monkeypatch.setattr(server, "db_fetchone", fake_fetchone)
    monkeypatch.setattr(server, "db_execute", fake_execute)
    monkeypatch.setattr(server, "create_admin_audit_log", fake_audit)

    response = client.put("/api/admin/users/user_1/role", json={"role": "admin"})

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert any("UPDATE users SET role=%s, active_role=%s" in sql for sql, _ in executed)
    assert any("UPDATE user_sessions SET impersonated_role=NULL" in sql for sql, _ in executed)


def test_cannot_remove_last_super_admin(monkeypatch):
    actor = {
        "user_id": "sa_1",
        "email": "mavin@5dm.africa",
        "name": "Super Admin",
        "role": "super_admin",
    }

    async def fake_get_super_admin_user(request):
        return actor

    async def fake_fetchone(sql, params=None):
        return {
            "user_id": "sa_2",
            "email": "owner@5dm.africa",
            "name": "Owner",
            "role": "super_admin",
            "active_role": "super_admin",
        }

    async def fake_count(sql, params=None):
        return 1

    monkeypatch.setattr(server, "get_super_admin_user", fake_get_super_admin_user)
    monkeypatch.setattr(server, "db_fetchone", fake_fetchone)
    monkeypatch.setattr(server, "db_count", fake_count)

    response = client.put("/api/admin/users/sa_2/role", json={"role": "admin"})

    assert response.status_code == 400
    assert response.json()["detail"] == "At least one super admin must remain assigned"