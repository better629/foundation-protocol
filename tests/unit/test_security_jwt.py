from __future__ import annotations

import time
import unittest

from fp.security.jwt_auth import JWTAuthenticator, encode_hs256_jwt


class SecurityJWTTests(unittest.TestCase):
    def test_hs256_jwt_authenticator_accepts_valid_token(self) -> None:
        now = int(time.time())
        token = encode_hs256_jwt(
            {
                "sub": "fp:agent:alice",
                "iss": "fp-test",
                "aud": "fp-network",
                "exp": now + 60,
                "iat": now,
            },
            "secret-1",
        )
        authenticator = JWTAuthenticator(secret="secret-1", issuer="fp-test", audience="fp-network")

        principal = authenticator.authenticate(f"Bearer {token}")
        self.assertIsNotNone(principal)
        self.assertEqual(principal.principal_id, "fp:agent:alice")

    def test_hs256_jwt_authenticator_rejects_wrong_signature_and_expired_token(self) -> None:
        now = int(time.time())
        valid = encode_hs256_jwt({"sub": "fp:agent:alice", "exp": now + 10}, "right-secret")
        expired = encode_hs256_jwt({"sub": "fp:agent:alice", "exp": now - 1}, "right-secret")
        authenticator = JWTAuthenticator(secret="right-secret")

        self.assertIsNone(authenticator.authenticate(f"Bearer {valid}.tampered"))
        self.assertIsNone(authenticator.authenticate(f"Bearer {expired}"))


if __name__ == "__main__":
    unittest.main()
