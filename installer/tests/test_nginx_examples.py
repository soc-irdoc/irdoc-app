"""docker/nginx/examples/*.conf are the installer's own output plus a header
comment, so a fix in the generator can't miss the examples (#160)."""
from pathlib import Path

import pytest

from installer.core.ssl import generate_nginx_conf

EXAMPLES = Path(__file__).resolve().parents[2] / "docker" / "nginx" / "examples"
PLACEHOLDER_LB = ["192.0.2.0/24"]


def _body(name: str) -> str:
    text = (EXAMPLES / name).read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    first_code = next(i for i, line in enumerate(lines) if line.strip() and not line.startswith("#"))
    return "".join(lines[first_code:])


@pytest.mark.parametrize("name,mode,subnets", [
    ("https.conf", "import", None),
    ("demo-https.conf", "import", None),
    ("lb-reencrypt.conf", "lb_reencrypt", PLACEHOLDER_LB),
    ("lb-terminate.conf", "lb_terminate", PLACEHOLDER_LB),
])
def test_example_matches_generator(name, mode, subnets):
    assert _body(name) == generate_nginx_conf(mode, lb_subnets=subnets)


def test_lb_examples_tell_the_operator_to_replace_the_placeholder():
    for name in ("lb-reencrypt.conf", "lb-terminate.conf"):
        assert "REPLACE 192.0.2.0/24" in (EXAMPLES / name).read_text(encoding="utf-8")
