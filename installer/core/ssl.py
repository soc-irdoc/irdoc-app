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


# CSP, X-Frame-Options, nosniff, Referrer-Policy and Permissions-Policy ship in
# the frontend image (frontend/nginx/irdoc-security-headers.conf), so they are
# updated by upgrades instead of being frozen into the host config (#57).
SECURITY_HEADERS_SNIPPET = "/etc/nginx/snippets/irdoc-security-headers.conf"


NGINX_MODES = ("import", "selfsigned", "lb_terminate", "lb_reencrypt", "behind_lb")

_TLS_SETTINGS = """
    ssl_certificate     /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 10m;
"""


_MIN_LB_PREFIX = {4: 8, 6: 32}


def normalise_lb_subnets(lb_subnets: list[str] | None) -> list[str]:
    """Validate load-balancer addresses/subnets; a bare IP becomes a /32 or /128."""
    result = []
    for raw in lb_subnets or []:
        value = raw.strip()
        if not value and len(lb_subnets) > 1:
            continue  # stray comma in a list
        try:
            net = ipaddress.ip_network(value, strict=False)
        except ValueError:
            raise ValueError(f"Not an IP address or subnet: {raw!r}") from None
        # A trusted range this wide (0.0.0.0/0, ::/0, ...) would let clients
        # set their own IP again: list the load balancer's own addresses.
        if net.prefixlen < _MIN_LB_PREFIX[net.version]:
            raise ValueError(
                f"{value} is too broad to trust: list the load balancer's own addresses "
                f"(at most a /{_MIN_LB_PREFIX[net.version]} subnet)"
            )
        result.append(str(net))
    return result


def _real_ip_block(subnets: list[str]) -> str:
    """Trust X-Forwarded-For only from the load balancer (#160)."""
    if not subnets:
        return """
    # Client IPs: list the load balancer's addresses to see real client IPs in
    # the audit log. Until then they show as the load balancer's address.
    # set_real_ip_from <load balancer IP or subnet>;
    # real_ip_header X-Forwarded-For;
    # real_ip_recursive on;
"""
    lines = "".join(f"    set_real_ip_from {net};\n" for net in subnets)
    return f"""
    # Client IPs: trust X-Forwarded-For only from the load balancer.
{lines}    real_ip_header X-Forwarded-For;
    real_ip_recursive on;
"""


def generate_nginx_conf(mode: str, lb_subnets: list[str] | None = None) -> str:
    """Generate nginx.conf content for one of NGINX_MODES.

    - import / selfsigned: nginx serves HTTPS with the cert in docker/ssl.
    - lb_terminate: a load balancer terminates TLS and forwards plain HTTP to
      port 80. lb_subnets are the addresses its connections come from.
    - lb_reencrypt: a load balancer terminates TLS and re-encrypts to port 443.
    - behind_lb: older name for lb_terminate.
    """
    if mode not in NGINX_MODES:
        raise ValueError(f"Unknown nginx mode: {mode!r}")
    if mode == "behind_lb":
        mode = "lb_terminate"
    subnets = normalise_lb_subnets(lb_subnets)

    upstream = "upstream backend {\n    server irdoc-backend:8000;\n}\n\n"
    proto = "$scheme"
    if mode == "lb_terminate":
        # The LB says whether the client used https; nginx itself only sees http.
        upstream += """map $http_x_forwarded_proto $irdoc_forwarded_proto {
    default $scheme;
    https   https;
}

"""
        proto = "$irdoc_forwarded_proto"

    # X-Real-IP is what the backend uses as the client IP (#160). nginx sets
    # both headers from $remote_addr, overwriting whatever the client sent.
    shared_locations = f"""
    root /usr/share/nginx/html;
    index index.html;

    location /api/ {{
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto {proto};
        client_max_body_size 55m;
    }}

    location /socket.io/ {{
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
    }}

    location / {{
        try_files $uri $uri/ /index.html;
    }}"""

    headers = f"""
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    include {SECURITY_HEADERS_SNIPPET};"""

    real_ip = _real_ip_block(subnets) if mode in ("lb_terminate", "lb_reencrypt") else ""

    if mode == "lb_terminate":
        return upstream + f"""server {{
    listen 80;
    server_name _;
{headers}
{real_ip}{shared_locations}
}}
"""

    # import, selfsigned, lb_reencrypt: HTTPS on 443, port 80 redirects.
    return upstream + f"""server {{
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}}

server {{
    listen 443 ssl;
    server_name _;
{_TLS_SETTINGS}{headers}
{real_ip}{shared_locations}
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
