import datetime
import ipaddress
import os
import stat
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID


def parse_pfx(pfx_bytes: bytes, passphrase: str) -> tuple[str, str, str, str]:
    """Extract cert + key from PFX. Returns (cert_pem, key_pem, common_name, expiry_iso)."""
    try:
        private_key, certificate, _ = pkcs12.load_key_and_certificates(
            pfx_bytes, passphrase.encode()
        )
    except Exception:
        raise ValueError("Invalid PFX or wrong passphrase. Check the file and try again.")

    cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    cn = certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    common_name = cn[0].value if cn else "unknown"
    expiry_iso = certificate.not_valid_after_utc.strftime("%Y-%m-%d")

    return cert_pem, key_pem, common_name, expiry_iso


def generate_self_signed(common_name: str, san_list: list[str], days: int = 825) -> tuple[str, str]:
    """Generate a self-signed certificate. Returns (cert_pem, key_pem)."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])

    san_entries: list[x509.GeneralName] = [x509.DNSName(common_name)]
    for entry in san_list:
        entry = entry.strip()
        if not entry:
            continue
        try:
            san_entries.append(x509.IPAddress(ipaddress.ip_address(entry)))
        except ValueError:
            san_entries.append(x509.DNSName(entry))

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=days))
        .add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
        .sign(key, hashes.SHA256())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return cert_pem, key_pem


def generate_nginx_conf(mode: str) -> str:
    """Generate nginx.conf content for the given HTTPS mode."""
    upstream = "upstream backend {\n    server irdoc-backend:8000;\n}\n\n"

    shared_locations = """
    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 55m;
    }

    location /socket.io/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }"""

    security_headers = """
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none';" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;"""

    if mode == "behind_lb":
        return upstream + f"""server {{
    listen 80;
    server_name _;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
{security_headers}

    # Trust headers from upstream load balancer
    set_real_ip_from 0.0.0.0/0;
    real_ip_header X-Forwarded-For;
{shared_locations}
}}
"""
    else:
        # "import" or "selfsigned" — both use the same TLS config
        return upstream + f"""server {{
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}}

server {{
    listen 443 ssl;
    server_name _;

    ssl_certificate     /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 10m;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
{security_headers}
{shared_locations}
}}
"""


def write_certs(ssl_dir: Path, cert_pem: str, key_pem: str) -> None:
    """Write cert.pem and key.pem to ssl_dir with secure permissions."""
    ssl_dir.mkdir(parents=True, exist_ok=True)
    cert_path = ssl_dir / "cert.pem"
    key_path = ssl_dir / "key.pem"
    cert_path.write_text(cert_pem)
    # Create key.pem with 0o600 atomically — never exists with loose permissions
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(key_pem)
