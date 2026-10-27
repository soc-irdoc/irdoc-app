"""Integration tests for incident CRUD."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_incident(client: AsyncClient, auth_headers):
    response = await client.post(
        "/api/v1/incidents",
        json={"title": "Test Incident", "severity": "high"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["title"] == "Test Incident"
    assert data["severity"] == "high"
    assert data["incident_ref"].startswith("INC-")


@pytest.mark.asyncio
async def test_list_incidents(client: AsyncClient, auth_headers):
    await client.post(
        "/api/v1/incidents",
        json={"title": "Incident A", "severity": "critical"},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/incidents",
        json={"title": "Incident B", "severity": "medium"},
        headers=auth_headers,
    )
    response = await client.get("/api/v1/incidents", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 2


@pytest.mark.asyncio
async def test_get_incident(client: AsyncClient, auth_headers):
    create = await client.post(
        "/api/v1/incidents",
        json={"title": "Get Me", "severity": "high"},
        headers=auth_headers,
    )
    iid = create.json()["data"]["id"]
    response = await client.get(f"/api/v1/incidents/{iid}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["id"] == iid


@pytest.mark.asyncio
async def test_update_incident(client: AsyncClient, auth_headers):
    create = await client.post(
        "/api/v1/incidents",
        json={"title": "Update Me", "severity": "high"},
        headers=auth_headers,
    )
    iid = create.json()["data"]["id"]
    response = await client.put(
        f"/api/v1/incidents/{iid}",
        json={"status": "contained", "executive_summary": "Contained quickly."},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "contained"
    assert data["contained_at"] is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("title", ["", "   "])
async def test_blank_title_rejected(client: AsyncClient, auth_headers, title):
    """#125: an incident can be renamed, but never to nothing."""
    create = await client.post(
        "/api/v1/incidents",
        json={"title": "Keep Me", "severity": "high"},
        headers=auth_headers,
    )
    iid = create.json()["data"]["id"]

    response = await client.put(f"/api/v1/incidents/{iid}", json={"title": title}, headers=auth_headers)
    assert response.status_code == 422

    create = await client.post("/api/v1/incidents", json={"title": title}, headers=auth_headers)
    assert create.status_code == 422


@pytest.mark.asyncio
async def test_filter_by_status(client: AsyncClient, auth_headers):
    await client.post("/api/v1/incidents", json={"title": "Open", "severity": "high"}, headers=auth_headers)
    r2 = await client.post("/api/v1/incidents", json={"title": "Closed", "severity": "medium"}, headers=auth_headers)
    iid = r2.json()["data"]["id"]
    await client.put(f"/api/v1/incidents/{iid}", json={"status": "closed"}, headers=auth_headers)

    response = await client.get("/api/v1/incidents?status=closed", headers=auth_headers)
    assert response.json()["meta"]["total"] == 1


@pytest.mark.asyncio
async def test_incident_ref_sequential(client: AsyncClient, auth_headers):
    r1 = await client.post("/api/v1/incidents", json={"title": "A", "severity": "critical"}, headers=auth_headers)
    r2 = await client.post("/api/v1/incidents", json={"title": "B", "severity": "critical"}, headers=auth_headers)
    ref1 = r1.json()["data"]["incident_ref"]
    ref2 = r2.json()["data"]["incident_ref"]
    # Both should be INC-YYYY-NNNN format
    assert ref1 != ref2
    assert ref1.startswith("INC-")


@pytest.mark.asyncio
async def test_rich_text_fields_round_trip(client: AsyncClient, auth_headers):
    """New rich text fields are persisted and returned correctly."""
    # Create incident
    res = await client.post(
        "/api/v1/incidents",
        json={"title": "Rich Text Test", "severity": "high"},
        headers=auth_headers,
    )
    assert res.status_code == 201
    inc_id = res.json()["data"]["id"]

    # Verify new fields default to null on creation
    assert res.json()["data"]["notes"] is None
    assert res.json()["data"]["lessons_learned"] is None
    assert res.json()["data"]["actions_todo"] is None

    html_notes = "<p>Test <strong>notes</strong></p>"
    html_lessons = "<p>Lessons <em>learned</em></p>"
    # Include data-type="taskItem" as Tiptap actually serialises it; the
    # sanitiser must preserve both data-type and data-checked on <li>.
    html_actions = '<ul data-type="taskList"><li data-type="taskItem" data-checked="false"><p>Action 1</p></li></ul>'

    # Update with rich text fields
    res = await client.put(
        f"/api/v1/incidents/{inc_id}",
        json={
            "notes": html_notes,
            "lessons_learned": html_lessons,
            "actions_todo": html_actions,
        },
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["notes"] == html_notes
    assert data["lessons_learned"] == html_lessons
    assert data["actions_todo"] == html_actions

    # Verify fields survive a GET
    res = await client.get(f"/api/v1/incidents/{inc_id}", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["notes"] == html_notes
    assert data["lessons_learned"] == html_lessons
    assert data["actions_todo"] == html_actions


@pytest.mark.asyncio
async def test_rich_text_fields_sanitize_xss(client: AsyncClient, auth_headers):
    """Dangerous HTML in rich text fields is stripped by bleach on save."""
    res = await client.post(
        "/api/v1/incidents",
        json={"title": "XSS Test", "severity": "medium"},
        headers=auth_headers,
    )
    assert res.status_code == 201
    inc_id = res.json()["data"]["id"]

    res = await client.put(
        f"/api/v1/incidents/{inc_id}",
        json={
            # <script> tag is stripped; bleach leaves its text content behind
            # as inert plain text (not re-parsed as markup), so this is not
            # executable even though the literal string "alert" survives.
            "notes": "<p>Safe</p><script>alert(1)</script>",
            # Event handler on an allowed tag should be removed
            "lessons_learned": '<p onclick="alert(1)">Click me</p>',
            # <img> is now allowed but dangerous attributes must be stripped
            "actions_todo": '<p>Text</p><img src="x" onerror="alert(1)">',
        },
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "<script>" not in data["notes"]
    assert 'onclick' not in data["lessons_learned"]
    assert "onerror" not in data["actions_todo"]
    # The src attribute is safe and the tag itself is now allowed
    assert 'src="x"' in data["actions_todo"]


@pytest.mark.asyncio
async def test_rich_text_font_size_round_trip(client: AsyncClient, auth_headers):
    """font-size style on <span> is preserved; other CSS properties are stripped."""
    res = await client.post(
        "/api/v1/incidents",
        json={"title": "Font Size Test", "severity": "medium"},
        headers=auth_headers,
    )
    assert res.status_code == 201
    inc_id = res.json()["data"]["id"]

    res = await client.put(
        f"/api/v1/incidents/{inc_id}",
        json={
            "notes": '<p><span data-font-size="16px">big text</span></p>',
        },
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert 'data-font-size="16px"' in data["notes"]

    # Disallowed attributes on span must be stripped, data-font-size preserved
    res = await client.put(
        f"/api/v1/incidents/{inc_id}",
        json={
            "notes": '<p><span data-font-size="14px" style="color: red">styled</span></p>',
        },
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "color" not in data["notes"]
    assert "red" not in data["notes"]
    assert 'data-font-size="14px"' in data["notes"]


async def _create(client, headers, title):
    r = await client.post("/api/v1/incidents", json={"title": title, "severity": "high"}, headers=headers)
    return r.json()["data"]


@pytest.mark.asyncio
async def test_search_matches_incident_ref(client: AsyncClient, auth_headers):
    # Regression (#64): search only matched the title.
    a = await _create(client, auth_headers, "Phishing wave")
    await _create(client, auth_headers, "Ransomware on file server")

    for term in (a["incident_ref"], a["incident_ref"].lower(), a["incident_ref"][-4:]):
        r = await client.get("/api/v1/incidents", params={"search": term}, headers=auth_headers)
        refs = [i["incident_ref"] for i in r.json()["data"]]
        assert refs == [a["incident_ref"]], term


@pytest.mark.asyncio
async def test_search_still_matches_title(client: AsyncClient, auth_headers):
    await _create(client, auth_headers, "Phishing wave")
    await _create(client, auth_headers, "Ransomware on file server")
    r = await client.get("/api/v1/incidents", params={"search": "ransom"}, headers=auth_headers)
    assert [i["title"] for i in r.json()["data"]] == ["Ransomware on file server"]


@pytest.mark.asyncio
async def test_search_treats_like_wildcards_literally(client: AsyncClient, auth_headers):
    await _create(client, auth_headers, "Phishing wave")
    for term in ("%", "_"):
        r = await client.get("/api/v1/incidents", params={"search": term}, headers=auth_headers)
        assert r.json()["meta"]["total"] == 0, term


@pytest.mark.asyncio
@pytest.mark.parametrize("legacy, new", [("sev1", "critical"), ("sev2", "high"), ("SEV3", "medium"), ("sev4", "low")])
async def test_legacy_severity_is_mapped(client: AsyncClient, auth_headers, legacy, new):
    r = await client.post("/api/v1/incidents", json={"title": "Legacy", "severity": legacy}, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["data"]["severity"] == new


@pytest.mark.asyncio
async def test_update_with_legacy_severity(client: AsyncClient, auth_headers):
    r = await client.post("/api/v1/incidents", json={"title": "Bump", "severity": "low"}, headers=auth_headers)
    inc_id = r.json()["data"]["id"]
    r = await client.put(f"/api/v1/incidents/{inc_id}", json={"severity": "sev1"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["data"]["severity"] == "critical"


@pytest.mark.asyncio
async def test_unknown_severity_rejected(client: AsyncClient, auth_headers):
    r = await client.post("/api/v1/incidents", json={"title": "Bad", "severity": "sev5"}, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_filter_by_legacy_severity(client: AsyncClient, auth_headers):
    await client.post("/api/v1/incidents", json={"title": "Crit", "severity": "critical"}, headers=auth_headers)
    await client.post("/api/v1/incidents", json={"title": "Low", "severity": "low"}, headers=auth_headers)
    for value in ("critical", "sev1"):
        r = await client.get(f"/api/v1/incidents?severity={value}", headers=auth_headers)
        titles = [i["title"] for i in r.json()["data"]]
        assert titles == ["Crit"]
