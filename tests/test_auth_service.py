import pytest
from app.services.auth_service import hash_password, verify_password, create_token, decode_token


class TestPasswordHash:
    def test_hash_and_verify(self):
        hashed = hash_password("test123")
        assert verify_password("test123", hashed)

    def test_wrong_password(self):
        hashed = hash_password("test123")
        assert not verify_password("wrong", hashed)

    def test_hash_is_random(self):
        """每次 hash 产生不同的结果（因为有 salt）。"""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2


class TestJWT:
    def test_create_and_decode(self):
        token = create_token(user_id=42, role="team")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["role"] == "team"

    def test_decode_invalid(self):
        assert decode_token("not.a.real.token") is None

    def test_decode_empty(self):
        assert decode_token("") is None

    def test_decode_gibberish(self):
        assert decode_token("gibberish") is None
