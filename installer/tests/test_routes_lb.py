"""Wizard: 'Behind a load balancer?' in the HTTPS step (Refs #161)."""
import pytest

from installer.wizard import state


@pytest.fixture(autouse=True)
def _reset_state():
    state.https_mode = None
    state.public_url = ""
    state.lb_subnets = []
    state.base_url = ""
    state.cert_pem = state.key_pem = None
    yield


def _confirm_prereqs(tmp_path, monkeypatch):
    from installer import wizard as wiz
    monkeypatch.setattr(wiz, "DOCKER_DIR", tmp_path)
    (tmp_path / "nginx").mkdir()
    (tmp_path / "ssl").mkdir()
    state.db_password = "dbpw"
    state.redis_password = "rpw"
    state.secret_key = "sk" * 16
    state.access_token_expire_minutes = 15
    state.refresh_token_expire_days = 30
    state.license_key = ""


@pytest.mark.asyncio
async def test_page_offers_both_lb_modes(client):
    text = (await client.get("/https-mode")).text
    assert "lb_terminate" in text and "lb_reencrypt" in text


@pytest.mark.asyncio
async def test_terminate_sets_public_url_and_subnets(client):
    resp = await client.post("/https-mode/set", data={
        "mode": "lb_terminate", "public_url": "https://irdoc.example.com/",
        "lb_subnets": "10.20.0.0/24, 10.30.0.5",
    }, follow_redirects=False)
    assert resp.status_code == 302 and resp.headers["location"] == "/core-config"
    assert state.https_mode == "lb_terminate"
    assert state.base_url == "https://irdoc.example.com"
    assert state.lb_subnets == ["10.20.0.0/24", "10.30.0.5/32"]


@pytest.mark.asyncio
async def test_core_config_prefills_the_public_url(client):
    await client.post("/https-mode/set", data={
        "mode": "lb_terminate", "public_url": "https://irdoc.example.com", "lb_subnets": "10.0.0.0/8",
    })
    assert 'value="https://irdoc.example.com"' in (await client.get("/core-config")).text


@pytest.mark.asyncio
@pytest.mark.parametrize("data,error", [
    ({"public_url": "http://irdoc.example.com", "lb_subnets": "10.0.0.0/8"}, "https://"),
    ({"public_url": "", "lb_subnets": "10.0.0.0/8"}, "https://"),
    ({"public_url": "https://irdoc.example.com", "lb_subnets": "10.0.0.0/33"}, "10.0.0.0/33"),
    # Required: without it every user shares the LB's IP, in the audit log and the login rate limit
    ({"public_url": "https://irdoc.example.com", "lb_subnets": "  "}, "load balancer"),
])
async def test_bad_lb_input_is_shown_not_saved(client, data, error):
    resp = await client.post("/https-mode/set", data={"mode": "lb_terminate", **data}, follow_redirects=False)
    assert resp.status_code == 200
    assert error in resp.text
    assert state.https_mode is None


@pytest.mark.asyncio
async def test_reencrypt_goes_to_a_prefilled_self_signed_form(client):
    resp = await client.post("/https-mode/set", data={
        "mode": "lb_reencrypt", "public_url": "https://irdoc.example.com",
        "lb_subnets": "10.20.0.0/24", "lb_cert": "selfsigned",
    }, follow_redirects=False)
    assert resp.headers["location"] == "/https-mode/selfsigned"
    page = (await client.get("/https-mode/selfsigned")).text
    assert "irdoc.example.com" in page  # public FQDN offered as a SAN


@pytest.mark.asyncio
async def test_reencrypt_keeps_its_mode_after_generating_the_cert(client):
    await client.post("/https-mode/set", data={
        "mode": "lb_reencrypt", "public_url": "https://irdoc.example.com",
        "lb_subnets": "10.20.0.0/24", "lb_cert": "selfsigned",
    })
    await client.post("/https-mode/generate-selfsigned", data={
        "common_name": "irdoc01.corp.local", "san": "irdoc.example.com", "for_lb": "1",
    })
    assert state.https_mode == "lb_reencrypt"
    assert state.cert_pem


@pytest.mark.asyncio
async def test_plain_self_signed_is_unaffected(client):
    await client.post("/https-mode/set", data={"mode": "selfsigned"})
    await client.post("/https-mode/generate-selfsigned", data={"common_name": "irdoc.local", "san": ""})
    assert state.https_mode == "selfsigned"


@pytest.mark.asyncio
async def test_legacy_behind_lb_value_maps_to_terminate(client):
    await client.post("/https-mode/set", data={
        "mode": "behind_lb", "public_url": "https://irdoc.example.com", "lb_subnets": "10.0.0.0/8",
    })
    assert state.https_mode == "lb_terminate"


@pytest.mark.asyncio
async def test_confirm_writes_lb_nginx_conf_and_secure_cookies(client, tmp_path, monkeypatch):
    _confirm_prereqs(tmp_path, monkeypatch)
    state.https_mode = "lb_terminate"
    state.lb_subnets = ["10.20.0.0/24"]
    state.base_url = "https://irdoc.example.com"
    await client.post("/review/confirm", follow_redirects=False)
    conf = (tmp_path / "nginx" / "local" / "nginx.conf").read_text()
    assert "set_real_ip_from 10.20.0.0/24;" in conf
    env = (tmp_path / ".env").read_text()
    assert "BASE_URL=https://irdoc.example.com" in env
    assert "COOKIE_SECURE=true" in env


@pytest.mark.asyncio
@pytest.mark.parametrize("mode,port", [("lb_terminate", "80"), ("lb_reencrypt", "443")])
async def test_success_page_explains_the_lb_setup(client, mode, port):
    state.https_mode = mode
    state.base_url = "https://irdoc.example.com"
    state.lb_subnets = ["10.20.0.0/24"]
    text = (await client.get("/success")).text
    assert "Health check" in text
    assert f":{port}" in text
    assert "10.20.0.0/24" in text  # firewall: only from the LB
