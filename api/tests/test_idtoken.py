"""OIDC ID-token validation + account binding tests (issue 029 / REQ-AUTH-018)."""

from __future__ import annotations

import pytest

from pingpals_api.auth.idtoken import IdTokenError, account_key, validate_id_token
from pingpals_api.auth.oidc import TransactionState

CLIENT = "client-123"
ISS = "https://accounts.google.com"


def _txn(nonce="nonce-abc", ua="ua-1") -> TransactionState:
    return TransactionState("st", "verifier", nonce, ISS, "https://app/cb", ua, 1000.0)


class StubVerifier:
    """Returns preset claims (signature assumed valid) or raises to simulate a bad signature."""

    def __init__(self, claims: dict | None, raises: bool = False) -> None:
        self._claims = claims
        self._raises = raises

    def verify(self, id_token: str, expected_iss: str) -> dict:
        if self._raises:
            raise IdTokenError("bad signature")
        return dict(self._claims or {})


def _claims(**over):
    base = {
        "iss": ISS, "aud": CLIENT, "exp": 2000, "iat": 1000,
        "nonce": "nonce-abc", "sub": "google-sub-1",
        "email": "a@example.com", "email_verified": True,
    }
    base.update(over)
    return base


def _now():
    return 1500.0


def test_valid_token_resolves_immutable_identity() -> None:
    ident = validate_id_token("jwt", _txn(), CLIENT, StubVerifier(_claims()), "ua-1", now=_now)
    assert account_key(ident) == (ISS, "google-sub-1")  # AC-01/AC-03
    assert ident.email == "a@example.com"


def test_bad_signature_rejected() -> None:
    with pytest.raises(IdTokenError):  # AC-02
        validate_id_token("jwt", _txn(), CLIENT, StubVerifier(None, raises=True), "ua-1", now=_now)


@pytest.mark.parametrize("claims", [
    _claims(aud="other-client"),
    _claims(exp=1000),                 # expired vs now=1500
    _claims(nonce="wrong"),
    _claims(iss="https://evil.example"),
])
def test_claim_mismatches_rejected(claims) -> None:
    with pytest.raises(IdTokenError):  # AC-02
        validate_id_token("jwt", _txn(), CLIENT, StubVerifier(claims), "ua-1", now=_now)


def test_ua_binding_mismatch_rejected() -> None:
    with pytest.raises(IdTokenError):
        validate_id_token("jwt", _txn(ua="ua-1"), CLIENT, StubVerifier(_claims()), "ua-OTHER",
                          now=_now)


def test_absent_sub_denied() -> None:
    claims = _claims()
    del claims["sub"]
    with pytest.raises(IdTokenError):  # AC-05
        validate_id_token("jwt", _txn(), CLIENT, StubVerifier(claims), "ua-1", now=_now)


def test_unverified_email_denied() -> None:
    with pytest.raises(IdTokenError):  # AC-05
        validate_id_token("jwt", _txn(), CLIENT, StubVerifier(_claims(email_verified=False)),
                          "ua-1", now=_now)


def test_email_absent_is_ok_identity_still_resolves() -> None:
    claims = _claims()
    del claims["email"]
    del claims["email_verified"]
    ident = validate_id_token("jwt", _txn(), CLIENT, StubVerifier(claims), "ua-1", now=_now)
    assert ident.email is None
    assert account_key(ident) == (ISS, "google-sub-1")  # AC-04 identity is (iss, sub), not email
