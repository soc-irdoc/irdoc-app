import datetime
from pathlib import Path
import pytest
import platform
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.serialization import pkcs12
import os, stat

from installer.core.ssl import (
    SECURITY_HEADERS_SNIPPET, parse_pfx, generate_self_signed, generate_nginx_conf, write_certs,
)


def _make_test_pfx(passphrase: bytes = b"testpass") -> bytes:
    """Create a minimal test PFX in memory."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test.example.com")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        name=b"test", key=key, cert=cert, cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(passphrase),
    )


def test_parse_pfx_returns_pem_strings():
    pfx_bytes = _make_test_pfx()
    cert_pem, key_pem, cn, expiry = parse_pfx(pfx_bytes, "testpass")
    assert "BEGIN CERTIFICATE" in cert_pem
    assert "BEGIN" in key_pem
    assert cn == "test.example.com"
    assert "2027" in expiry or "2026" in expiry  # ~1 year from now


def test_parse_pfx_wrong_passphrase_raises():
    pfx_bytes = _make_test_pfx()
    with pytest.raises(ValueError, match="passphrase"):
        parse_pfx(pfx_bytes, "wrongpassword")


def test_generate_self_signed_returns_valid_pem():
    cert_pem, key_pem = generate_self_signed("myhost.local", ["192.168.1.1"])
    assert "BEGIN CERTIFICATE" in cert_pem
    assert "BEGIN" in key_pem
    cert = x509.load_pem_x509_certificate(cert_pem.encode())
    assert cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value == "myhost.local"


def test_generate_nginx_conf_behind_lb_has_no_ssl():
    conf = generate_nginx_conf("behind_lb")
    assert "ssl" not in conf.lower()
    assert "listen 80" in conf
    assert "X-Forwarded-Proto" in conf
    assert "Strict-Transport-Security" in conf
    assert "irdoc-security-headers.conf" in conf


def test_generate_nginx_conf_import_has_ssl_block():
    conf = generate_nginx_conf("import")
    assert "listen 443 ssl" in conf
    assert "ssl_certificate" in conf
    assert "/etc/nginx/ssl/cert.pem" in conf
    assert "irdoc-security-headers.conf" in conf


def test_generate_nginx_conf_includes_security_headers_snippet():
    """#57: the headers come from the snippet in the frontend image, so upgrades
    update them. The CSP itself is pinned in test_nginx_migrate.py."""
    for mode in ("import", "behind_lb"):
        conf = generate_nginx_conf(mode)
        assert f"include {SECURITY_HEADERS_SNIPPET};" in conf
        assert "Content-Security-Policy" not in conf
        assert "Strict-Transport-Security" in conf  # depends on mode, stays here


def test_generate_nginx_conf_selfsigned_same_as_import():
    conf_import = generate_nginx_conf("import")
    conf_self = generate_nginx_conf("selfsigned")
    assert conf_import == conf_self


def test_write_certs_sets_permissions(tmp_path):
    write_certs(tmp_path, "CERT", "KEY")
    cert_file = tmp_path / "cert.pem"
    key_file = tmp_path / "key.pem"
    assert cert_file.read_text() == "CERT"
    assert key_file.read_text() == "KEY"
    if platform.system() != "Windows":
        mode = stat.S_IMODE(os.stat(key_file).st_mode)
        assert mode == 0o600


# ─── Load balancer modes (#160) ─────────────────────────────────────────────

def test_lb_terminate_trusts_only_the_given_subnets():
    conf = generate_nginx_conf("lb_terminate", lb_subnets=["10.20.0.0/24", "192.0.2.10"])
    assert "listen 80;" in conf and "listen 443" not in conf
    assert "set_real_ip_from 10.20.0.0/24;" in conf
    assert "set_real_ip_from 192.0.2.10/32;" in conf
    assert "real_ip_header X-Forwarded-For;" in conf
    assert "real_ip_recursive on;" in conf
    assert "0.0.0.0/0" not in conf


def test_lb_terminate_passes_the_lbs_scheme():
    conf = generate_nginx_conf("lb_terminate", lb_subnets=["10.0.0.0/8"])
    assert "map $http_x_forwarded_proto $irdoc_forwarded_proto" in conf
    assert "proxy_set_header X-Forwarded-Proto $irdoc_forwarded_proto;" in conf


def test_lb_reencrypt_serves_tls_and_trusts_the_lb():
    conf = generate_nginx_conf("lb_reencrypt", lb_subnets=["10.20.0.0/24"])
    assert "listen 443 ssl;" in conf
    assert "return 301 https://$host$request_uri;" in conf
    assert "set_real_ip_from 10.20.0.0/24;" in conf
    assert "proxy_set_header X-Forwarded-Proto $scheme;" in conf


def test_lb_mode_without_subnets_trusts_no_forwarded_header():
    conf = generate_nginx_conf("lb_terminate")
    assert "set_real_ip_from" not in conf.replace("# set_real_ip_from", "")
    assert "real_ip_header" not in conf.replace("# real_ip_header", "")


def test_legacy_behind_lb_no_longer_trusts_everyone():
    # The old mode trusted X-Forwarded-For from 0.0.0.0/0: any client could set its own IP.
    assert "0.0.0.0/0" not in generate_nginx_conf("behind_lb")


@pytest.mark.parametrize("bad", ["10.0.0.0/33", "not-a-subnet", "10.0.0.0/8; evil", ""])
def test_invalid_lb_subnet_is_rejected(bad):
    with pytest.raises(ValueError):
        generate_nginx_conf("lb_terminate", lb_subnets=[bad])


@pytest.mark.parametrize("mode", ["import", "selfsigned", "lb_terminate", "lb_reencrypt", "behind_lb"])
def test_client_ip_headers_are_overwritten_not_appended(mode):
    # The backend takes the client IP from X-Real-IP; X-Forwarded-For must not
    # carry the client's own value along.
    conf = generate_nginx_conf(mode)
    assert "$proxy_add_x_forwarded_for" not in conf
    assert conf.count("proxy_set_header X-Real-IP $remote_addr;") == 2  # /api/ and /socket.io/


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError):
        generate_nginx_conf("plain")
