"""Integration tests for inbound webhook endpoint."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_api_key
from app.models.api_key import APIKey


@pytest.fixture
async def api_key_headers(db_session: AsyncSession, admin_user):
    user, org = admin_user
    raw_key, key_prefix, key_hash = generate_api_key()
    api_key = APIKey(
        org_id=org.id,
        created_by=user.id,
        name="Test Webhook Key",
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=["incidents:create"],
    )
    db_session.add(api_key)
    await db_session.flush()
    return {"Authorization": f"ApiKey {raw_key}"}


@pytest.mark.asyncio
async def test_create_incident_via_webhook(client: AsyncClient, api_key_headers):
    response = await client.post(
        "/api/v1/external/incidents",
        json={
            "title": "SDP Ticket #4421 - Suspicious Login",
            "severity": "high",
            "external_ref": "SDP-2026-4421",
            "external_source": "servicedesk_plus",
            "external_url": "https://sdp.example.com/requests/4421",
            "description": "User reported inability to log in after suspicious activity.",
            "reported_by": "user@company.com",
        },
        headers=api_key_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["incident_ref"].startswith("INC-")
    assert data["external_ref"] == "SDP-2026-4421"
    assert "workspace_url" in data


@pytest.mark.asyncio
async def test_webhook_requires_api_key(client: AsyncClient):
    response = await client.post(
        "/api/v1/external/incidents",
        json={"title": "No auth", "severity": "high"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_wrong_scope(client: AsyncClient, admin_user, db_session: AsyncSession):
    _, org = admin_user
    user, _ = admin_user
    raw_key, key_prefix, key_hash = generate_api_key()
    api_key = APIKey(
        org_id=org.id,
        created_by=user.id,
        name="Read-only key",
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=["incidents:read"],  # Wrong scope
    )
    db_session.add(api_key)
    await db_session.flush()

    response = await client.post(
        "/api/v1/external/incidents",
        json={"title": "Should fail", "severity": "high"},
        headers={"Authorization": f"ApiKey {raw_key}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_invalid_severity(client: AsyncClient, api_key_headers):
    response = await client.post(
        "/api/v1/external/incidents",
        json={"title": "Bad severity", "severity": "sev5"},  # invalid
        headers=api_key_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_webhook_accepts_legacy_severity(client: AsyncClient, api_key_headers):
    """Senders written before #109 still post sev1-sev4."""
    response = await client.post(
        "/api/v1/external/incidents",
        json={"title": "Legacy sender", "severity": "sev1"},
        headers=api_key_headers,
    )
    assert response.status_code == 201


@pytest.mark.asyncio
@pytest.mark.parametrize("url", [
    "javascript:alert(document.cookie)",
    "JavaScript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "//evil.example.com/x",
    "not a url",
])
async def test_webhook_rejects_non_http_external_url(client: AsyncClient, api_key_headers, url):
    # external_url is rendered as a link in the UI: http(s) only
    response = await client.post(
        "/api/v1/external/incidents",
        json={"title": "x", "external_source": "jira", "external_ref": "SEC-1", "external_url": url},
        headers=api_key_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_webhook_accepts_https_external_url(client: AsyncClient, api_key_headers):
    response = await client.post(
        "/api/v1/external/incidents",
        json={"title": "x", "external_source": "jira", "external_ref": "SEC-1",
              "external_url": "https://jira.example.com/browse/SEC-1"},
        headers=api_key_headers,
    )
    assert response.status_code == 201


# --- incident_number: the ticket's number becomes the incident's (#156) ---

def _ref(n: str) -> str:
    from datetime import UTC, datetime
    return f"INC-{datetime.now(UTC).year}-{n}"


@pytest.mark.asyncio
@pytest.mark.parametrize("number,expected", [
    ("123456", "123456"),
    (123456, "123456"),   # JSON number
    ("42", "0042"),       # padded like generated refs
    ("007", "0007"),
])
async def test_webhook_incident_number_sets_ref(client: AsyncClient, api_key_headers, number, expected):
    response = await client.post(
        "/api/v1/external/incidents",
        json={"title": "Ticket", "incident_number": number},
        headers=api_key_headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["incident_ref"] == _ref(expected)


@pytest.mark.asyncio
@pytest.mark.parametrize("number", ["12a", "", "0", "000", "-5", -5, "1" * 22, "12 34", True])
async def test_webhook_incident_number_validation(client: AsyncClient, api_key_headers, number):
    response = await client.post(
        "/api/v1/external/incidents",
        json={"title": "Ticket", "incident_number": number},
        headers=api_key_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_webhook_incident_number_max_length_fits(client: AsyncClient, api_key_headers):
    response = await client.post(
        "/api/v1/external/incidents",
        json={"title": "Ticket", "incident_number": "9" * 21},
        headers=api_key_headers,
    )
    assert response.status_code == 201, response.text
    assert len(response.json()["incident_ref"]) == 30


@pytest.mark.asyncio
async def test_webhook_incident_number_duplicate_409(
    client: AsyncClient, api_key_headers, db_session: AsyncSession
):
    from sqlalchemy import func, select

    from app.models.incident import Incident

    first = await client.post(
        "/api/v1/external/incidents",
        json={"title": "Ticket", "incident_number": "555"},
        headers=api_key_headers,
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/external/incidents",
        json={"title": "Retry", "incident_number": "0555"},  # same number, normalised
        headers=api_key_headers,
    )
    assert second.status_code == 409
    detail = second.json()["detail"]
    assert detail["incident_ref"] == _ref("0555")
    assert detail["incident_id"] == first.json()["incident_id"]  # same org: link to it

    count = await db_session.scalar(
        select(func.count()).select_from(Incident).where(Incident.incident_ref == _ref("0555"))
    )
    assert count == 1


@pytest.mark.asyncio
async def test_webhook_incident_number_duplicate_other_org_hides_id(
    client: AsyncClient, api_key_headers, db_session: AsyncSession
):
    from app.models.incident import Incident
    from app.models.organization import Organization

    other = Organization(name="Other Org", slug="other-org-156")
    db_session.add(other)
    await db_session.flush()
    db_session.add(Incident(org_id=other.id, incident_ref=_ref("0777"), title="Theirs"))
    await db_session.flush()

    response = await client.post(
        "/api/v1/external/incidents",
        json={"title": "Ticket", "incident_number": "777"},
        headers=api_key_headers,
    )
    assert response.status_code == 409
    assert "incident_id" not in response.json()["detail"]


@pytest.mark.asyncio
async def test_webhook_incident_number_without_external_ref_has_no_badge(
    client: AsyncClient, api_key_headers, db_session: AsyncSession
):
    from sqlalchemy import func, select

    from app.models.incident import IncidentExternalRef

    response = await client.post(
        "/api/v1/external/incidents",
        json={"title": "Ticket", "incident_number": "123456"},
        headers=api_key_headers,
    )
    assert response.status_code == 201
    count = await db_session.scalar(
        select(func.count()).select_from(IncidentExternalRef)
        .where(IncidentExternalRef.incident_id == response.json()["incident_id"])
    )
    assert count == 0


@pytest.mark.asyncio
async def test_generated_refs_skip_numbers_taken_by_webhook(client: AsyncClient, api_key_headers):
    taken = await client.post(
        "/api/v1/external/incidents",
        json={"title": "Ticket", "incident_number": "2"},
        headers=api_key_headers,
    )
    assert taken.status_code == 201
    refs = {taken.json()["incident_ref"]}
    for _ in range(3):
        r = await client.post(
            "/api/v1/external/incidents", json={"title": "Auto"}, headers=api_key_headers
        )
        assert r.status_code == 201, r.text
        refs.add(r.json()["incident_ref"])
    assert len(refs) == 4  # no collisions with INC-YYYY-0002
