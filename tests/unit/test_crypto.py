import pytest
from packages.core.security.crypto import encrypt_token, decrypt_token


def test_token_encryption_and_decryption():
    raw_token = "ya29.a0AfH6SMD_example_google_oauth_token_12345"
    encrypted = encrypt_token(raw_token)

    assert encrypted != raw_token
    assert len(encrypted) > len(raw_token)

    decrypted = decrypt_token(encrypted)
    assert decrypted == raw_token


def test_empty_token_encryption():
    assert encrypt_token("") == ""
    assert decrypt_token("") == ""

