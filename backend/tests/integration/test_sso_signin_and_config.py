"""SSO sign-in end to end through /auth/oidc/callback, the Graph group lookup,
and the admin SSO config rules: secret on every save, enabling only after a
passing connection test (Refs #172)."""
import logging

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.api.v1 import admin as admin_api
from app.api.v1 import oidc
from app.models.audit import AuditLog
from app.models.organization import Organization
from app.models.sso_config import SSOConfig
from app.models.user import User
from app.services import sso_service

GROUP_SENIOR = "44444444-4444-4444-4444-444444444444"
TENANT = "55555555-5555-5555-5555-555555555555"
CLIENT = "66666666-6666-6666-6666-666666666666"


# ─── /auth/oidc/callback ─────────────────────────────────────────────────────

class _FakeTokenResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"id_token": "header.payload.sig", "access_token": "graph-token"}


class _FakeTokenClient:
    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, *a, **kw):
        return _FakeTokenResponse()


@pytest_asyncio.fixture
async def default_org_sso(db_session):
    org = Organization(name="Default Org", slug="default")
    db_session.add(org)
    await db_session.flush()
    cfg = SSOConfig(
        org_id=org.id, tenant_id=TENANT, client_id=CLIENT,
        client_secret=sso_service.encrypt_client_secret("s3cret"),
        role_mappings={GROUP_SENIOR: "senior_analyst"}, is_enabled=True,
    )
    db_session.add(cfg)
    await db_session.flush()
    return org, cfg


def _sign_in_with(monkeypatch, claims: dict):
    monkeypatch.setattr(oidc, "check_feature", lambda f: True)
    monkeypatch.setattr(oidc.httpx, "AsyncClient", _FakeTokenClient)

    async def fake_jwks(tenant_id):
        return {"keys": []}

    monkeypatch.setattr(oidc, "_fetch_jwks", fake_jwks)
    monkeypatch.setattr(oidc.jose_jwt, "decode", lambda *a, **kw: {"nonce": "n0nce", **claims})


async def _callback(client):
    client.cookies.set(oidc.STATE_COOKIE_NAME, "st4te|n0nce")
    return await client.get("/api/v1/auth/oidc/callback", params={"code": "c", "state": "st4te"})


async def _user(db_session, email):
    return (await db_session.execute(select(User).where(User.email == email))).scalar_one()


@pytest.mark.asyncio
async def test_new_user_in_mapped_group_signs_in_as_senior_analyst(
    client, db_session, default_org_sso, monkeypatch, caplog,
):
    _sign_in_with(monkeypatch, {"email": "new.senior@corp.test", "name": "New Senior", "groups": [GROUP_SENIOR]})

    with caplog.at_level(logging.INFO, logger="app.api.v1.oidc"):
        resp = await _callback(client)

    assert resp.status_code == 302
    assert (await _user(db_session, "new.senior@corp.test")).role == "senior_analyst"
    assert f"mapping {GROUP_SENIOR} -> senior_analyst" in caplog.text


@pytest.mark.asyncio
async def test_on_prem_group_names_in_token_warn_and_fall_back_to_analyst(
    client, db_session, default_org_sso, monkeypatch, caplog,
):
    _sign_in_with(monkeypatch, {"email": "onprem@corp.test", "name": "On Prem", "groups": ["SOC-Senior"]})

    with caplog.at_level(logging.INFO, logger="app.api.v1.oidc"):
        await _callback(client)

    assert (await _user(db_session, "onprem@corp.test")).role == "analyst"
    assert "names or SIDs, not Object IDs" in caplog.text


@pytest.mark.asyncio
async def test_graph_lookup_finds_the_group_the_token_names_differently(
    client, db_session, default_org_sso, monkeypatch,
):
    _, cfg = default_org_sso
    cfg.graph_group_lookup = True
    await db_session.flush()
    _sign_in_with(monkeypatch, {"email": "graph@corp.test", "name": "Via Graph", "groups": ["SOC-Senior"]})
    seen = {}

    async def fake_member_groups(access_token, group_ids):
        seen["token"], seen["ids"] = access_token, group_ids
        return {GROUP_SENIOR}

    monkeypatch.setattr(sso_service, "fetch_member_groups", fake_member_groups)

    await _callback(client)

    assert seen == {"token": "graph-token", "ids": [GROUP_SENIOR]}
    assert (await _user(db_session, "graph@corp.test")).role == "senior_analyst"


@pytest.mark.asyncio
async def test_graph_failure_does_not_block_sign_in(client, db_session, default_org_sso, monkeypatch, caplog):
    _, cfg = default_org_sso
    cfg.graph_group_lookup = True
    await db_session.flush()
    _sign_in_with(monkeypatch, {"email": "nograph@corp.test", "name": "No Graph", "groups": []})

    async def failing(access_token, group_ids):
        raise RuntimeError("403 Forbidden")

    monkeypatch.setattr(sso_service, "fetch_member_groups", failing)

    with caplog.at_level(logging.WARNING, logger="app.api.v1.oidc"):
        resp = await _callback(client)

    assert resp.status_code == 302
    assert (await _user(db_session, "nograph@corp.test")).role == "analyst"
    assert "Graph group lookup failed" in caplog.text


@pytest.mark.asyncio
async def test_login_url_asks_for_graph_scope_only_when_lookup_is_on(client, db_session, default_org_sso, monkeypatch):
    monkeypatch.setattr(oidc, "check_feature", lambda f: True)
    _, cfg = default_org_sso

    url = (await client.get("/api/v1/auth/oidc/login")).json()["data"]["redirect_url"]
    assert "User.Read" not in url

    cfg.graph_group_lookup = True
    await db_session.flush()
    url = (await client.get("/api/v1/auth/oidc/login")).json()["data"]["redirect_url"]
    assert "graph.microsoft.com/User.Read" in url


# ─── /admin/sso ──────────────────────────────────────────────────────────────

@pytest.fixture
def sso_licensed(monkeypatch):
    monkeypatch.setattr(admin_api, "check_feature", lambda f: True)


def _fake_check(ok: bool, calls: list | None = None):
    async def check(tenant_id, client_id, client_secret):
        if calls is not None:
            calls.append((tenant_id, client_id, client_secret))
        if ok:
            return {"ok": True, "step": "done", "message": "valid"}
        return {"ok": False, "step": "credentials", "message": "Invalid client secret. (AADSTS7000215)"}
    return check


BASE = {"tenant_id": TENANT, "client_id": CLIENT, "role_mappings": {GROUP_SENIOR: "senior_analyst"}}


@pytest.mark.asyncio
async def test_save_without_secret_is_rejected(client, auth_headers, sso_licensed):
    resp = await client.put("/api/v1/admin/sso", json={**BASE, "is_enabled": False}, headers=auth_headers)
    assert resp.status_code == 422

    resp = await client.put(
        "/api/v1/admin/sso", json={**BASE, "is_enabled": False, "client_secret": "  "}, headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_saving_disabled_does_not_run_the_test(client, auth_headers, sso_licensed, monkeypatch):
    calls: list = []
    monkeypatch.setattr(sso_service, "check_connection", _fake_check(False, calls))

    resp = await client.put(
        "/api/v1/admin/sso", json={**BASE, "is_enabled": False, "client_secret": "s"}, headers=auth_headers,
    )

    assert resp.status_code == 200
    assert calls == []


@pytest.mark.asyncio
async def test_enabling_with_failing_test_is_refused_and_saves_nothing(
    client, db_session, auth_headers, admin_user, sso_licensed, monkeypatch,
):
    monkeypatch.setattr(sso_service, "check_connection", _fake_check(False))

    resp = await client.put(
        "/api/v1/admin/sso", json={**BASE, "is_enabled": True, "client_secret": "bad"}, headers=auth_headers,
    )

    assert resp.status_code == 400
    assert "AADSTS7000215" in resp.json()["detail"]
    _, org = admin_user
    saved = (await db_session.execute(select(SSOConfig).where(SSOConfig.org_id == org.id))).scalar_one_or_none()
    assert saved is None


@pytest.mark.asyncio
async def test_enabling_with_passing_test_saves(client, auth_headers, sso_licensed, monkeypatch):
    calls: list = []
    monkeypatch.setattr(sso_service, "check_connection", _fake_check(True, calls))

    resp = await client.put(
        "/api/v1/admin/sso", json={**BASE, "is_enabled": True, "client_secret": "good"}, headers=auth_headers,
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["is_enabled"] is True
    assert "client_secret" not in data
    assert data["redirect_uri"].endswith("/api/v1/auth/oidc/callback")
    assert calls == [(TENANT, CLIENT, "good")]


@pytest.mark.asyncio
async def test_mapping_change_on_live_config_re_tests_credentials(client, auth_headers, sso_licensed, monkeypatch):
    monkeypatch.setattr(sso_service, "check_connection", _fake_check(True))
    await client.put(
        "/api/v1/admin/sso", json={**BASE, "is_enabled": True, "client_secret": "good"}, headers=auth_headers,
    )

    # is_enabled omitted: SSO stays on, so the credentials are checked again
    monkeypatch.setattr(sso_service, "check_connection", _fake_check(False))
    resp = await client.put(
        "/api/v1/admin/sso",
        json={"role_mappings": {GROUP_SENIOR: "admin"}, "client_secret": "rotated-wrong"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_invalid_role_in_mapping_is_rejected(client, auth_headers, sso_licensed):
    resp = await client.put(
        "/api/v1/admin/sso",
        json={**BASE, "role_mappings": {GROUP_SENIOR: "Senior Analyst"}, "client_secret": "s"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_tenant_id_must_be_a_guid_or_domain(client, auth_headers, sso_licensed, monkeypatch):
    monkeypatch.setattr(sso_service, "check_connection", _fake_check(True))
    for bad in ("../common", "x/y", "a?b=c", "tenant id"):
        resp = await client.post(
            "/api/v1/admin/sso/test",
            json={"tenant_id": bad, "client_id": CLIENT, "client_secret": "s"},
            headers=auth_headers,
        )
        assert resp.status_code == 422, bad
    ok = await client.post(
        "/api/v1/admin/sso/test",
        json={"tenant_id": "contoso.onmicrosoft.com", "client_id": CLIENT, "client_secret": "s"},
        headers=auth_headers,
    )
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_connection_test_endpoint_reports_and_audits(
    client, db_session, auth_headers, sso_licensed, monkeypatch,
):
    monkeypatch.setattr(sso_service, "check_connection", _fake_check(False))

    resp = await client.post(
        "/api/v1/admin/sso/test",
        json={"tenant_id": TENANT, "client_id": CLIENT, "client_secret": "bad-secret-value"},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["ok"] is False and data["step"] == "credentials"
    assert data["redirect_uri"].endswith("/api/v1/auth/oidc/callback")
    audit = (await db_session.execute(
        select(AuditLog).where(AuditLog.action == "sso.connection_tested")
    )).scalar_one()
    assert "bad-secret-value" not in str(audit.diff)


# ─── check_connection: Entra error mapping ───────────────────────────────────

class _Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


def _entra(token_status=200, token_body=None, disco_status=200):
    class Client:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url, **kw):
            if "openid-configuration" in url:
                return _Resp(disco_status, {"error_description": "AADSTS90002: Tenant 'x' not found."})
            return _Resp(200, {"keys": [{"kid": "k"}]})

        async def post(self, url, **kw):
            return _Resp(token_status, token_body or {"access_token": "t"})
    return Client


@pytest.mark.asyncio
async def test_check_connection_maps_invalid_secret(monkeypatch):
    body = {
        "error": "invalid_client",
        "error_description": "AADSTS7000215: Invalid client secret provided.\r\nTrace ID: abc",
    }
    monkeypatch.setattr(sso_service.httpx, "AsyncClient", _entra(token_status=401, token_body=body))

    result = await sso_service.check_connection(TENANT, CLIENT, "bad")

    assert result["ok"] is False and result["step"] == "credentials"
    assert "Invalid client secret" in result["message"] and "Trace ID" not in result["message"]


@pytest.mark.asyncio
async def test_check_connection_maps_unknown_tenant(monkeypatch):
    monkeypatch.setattr(sso_service.httpx, "AsyncClient", _entra(disco_status=400))

    result = await sso_service.check_connection(TENANT, CLIENT, "s")

    assert result == {
        "ok": False, "step": "tenant",
        "message": "Tenant not found. Check the Directory (Tenant) ID. (AADSTS90002)",
    }


@pytest.mark.asyncio
async def test_check_connection_ok(monkeypatch):
    monkeypatch.setattr(sso_service.httpx, "AsyncClient", _entra())
    assert (await sso_service.check_connection(TENANT, CLIENT, "s"))["ok"] is True
