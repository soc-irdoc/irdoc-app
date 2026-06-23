import datetime
from pathlib import Path
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.serialization import pkcs12
import os, stat

from installer.core.ssl import parse_pfx, generate_self_signed, generate_nginx_conf, write_certs


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


def test_generate_nginx_conf_import_has_ssl_block():
    conf = generate_nginx_conf("import")
    assert "listen 443 ssl" in conf
    assert "ssl_certificate" in conf
    assert "/etc/nginx/ssl/cert.pem" in conf


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
    assert stat.S_IMODE(os.stat(key_file).st_mode) == 0o600
