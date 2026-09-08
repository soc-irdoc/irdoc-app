"""Unit tests for IOC auto-detection regex patterns."""
from app.services.ioc_service import auto_detect


def test_detect_ip():
    results = auto_detect("Attacker came from 192.168.1.100 and also 10.0.0.1")
    values = [r.value for r in results]
    assert "192.168.1.100" in values
    assert "10.0.0.1" in values
    types = {r.value: r.ioc_type for r in results}
    assert types["192.168.1.100"] == "ip"


def test_detect_email():
    results = auto_detect("Phishing from attacker@evil.com to victim@company.com")
    values = [r.value for r in results]
    assert "attacker@evil.com" in values
    assert "victim@company.com" in values


def test_detect_sha256():
    sha = "a" * 64
    results = auto_detect(f"Malware hash: {sha}")
    values = [r.value for r in results]
    assert sha in values
    types = {r.value: r.ioc_type for r in results}
    assert types[sha] == "hash"


def test_detect_md5():
    md5 = "b" * 32
    results = auto_detect(f"File hash: {md5}")
    values = [r.value for r in results]
    assert md5 in values


def test_detect_url():
    results = auto_detect("C2 callback to https://evil.example.com/callback?id=1")
    values = [r.value for r in results]
    assert any("https://evil.example.com" in v for v in values)


def test_detect_no_false_positives_on_clean_text():
    results = auto_detect("The quick brown fox jumps over the lazy dog.")
    assert len(results) == 0


def test_deduplication():
    text = "IP 1.2.3.4 appeared at 1.2.3.4 again"
    results = auto_detect(text)
    values = [r.value for r in results]
    assert values.count("1.2.3.4") == 1


def test_mixed_iocs():
    text = "Sender: bad@evil.com, C2: https://c2.evil.com, hash: " + "a" * 64
    results = auto_detect(text)
    types = {r.ioc_type for r in results}
    assert "email" in types
    assert "url" in types
    assert "hash" in types
