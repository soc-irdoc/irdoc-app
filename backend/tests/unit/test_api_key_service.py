"""Unit tests for API key creation and verification."""
import pytest
from app.core.security import generate_api_key, verify_api_key_hash, API_KEY_PREFIX


def test_key_format():
    raw_key, prefix, hash_ = generate_api_key()
    assert raw_key.startswith(API_KEY_PREFIX)
    assert len(raw_key) == len(API_KEY_PREFIX) + 64  # prefix + 32 hex bytes
    assert prefix == raw_key[:16]


def test_key_hash_verification():
    raw_key, _, key_hash = generate_api_key()
    assert verify_api_key_hash(raw_key, key_hash) is True


def test_wrong_key_fails_verification():
    _, _, key_hash = generate_api_key()
    wrong_key, _, _ = generate_api_key()
    assert verify_api_key_hash(wrong_key, key_hash) is False


def test_keys_are_unique():
    keys = [generate_api_key()[0] for _ in range(10)]
    assert len(set(keys)) == 10


def test_prefix_matches_key():
    raw_key, prefix, _ = generate_api_key()
    assert raw_key.startswith(prefix)
