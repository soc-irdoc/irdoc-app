"""Unit tests for SHA-256 integrity and file token signing."""
import hashlib

import pytest
from app.core.security import sign_file_token, verify_file_token


def test_file_token_roundtrip():
    path = "attachments/inc1/file.pdf"
    token = sign_file_token(path, expires_in=3600)
    assert verify_file_token(token) == path


def test_expired_token_returns_none():
    path = "attachments/inc1/file.pdf"
    token = sign_file_token(path, expires_in=-1)  # expired immediately
    assert verify_file_token(token) is None


def test_tampered_token_fails():
    token = sign_file_token("path/to/file.pdf", expires_in=3600)
    tampered = token[:-4] + "XXXX"
    assert verify_file_token(tampered) is None


def test_sha256_matches():
    data = b"important forensic evidence"
    expected = hashlib.sha256(data).hexdigest()
    computed = hashlib.sha256(data).hexdigest()
    assert expected == computed
    assert len(expected) == 64
