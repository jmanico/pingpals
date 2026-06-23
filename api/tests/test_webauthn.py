"""WebAuthn registration + assertion tests (issues 031/032 / REQ-AUTH-020/021)."""

from __future__ import annotations

import pytest

from pingpals_api.auth.session import SessionManager
from pingpals_api.auth.webauthn import (
    AssertionInput,
    ChallengeStore,
    CredentialStore,
    RegistrationInput,
    WebAuthnError,
    WebAuthnRelyingParty,
)

RP_ID = "pingpals.example"
ORIGIN = "https://app.pingpals.example"


def _rp(verify=lambda pk, sig, data: True) -> WebAuthnRelyingParty:
    return WebAuthnRelyingParty(RP_ID, ORIGIN, ChallengeStore(), CredentialStore(), verify)


def _register(rp: WebAuthnRelyingParty, user="alice", cred="cred-1", count=0):
    challenge = rp.begin_registration(user, authenticated=True)
    return rp.complete_registration(RegistrationInput(
        user_id=user, rp_id=RP_ID, origin=ORIGIN, challenge=challenge,
        credential_id=cred, public_key=b"pk", uv=True, sign_count=count,
    ))


def test_registration_requires_authenticated_session() -> None:
    rp = _rp()
    with pytest.raises(WebAuthnError):  # AC-03
        rp.begin_registration("alice", authenticated=False)


def test_registration_binds_credential_to_user() -> None:
    rp = _rp()
    cred = _register(rp)
    assert cred.user_id == "alice" and cred.credential_id == "cred-1"  # AC-02


def test_registration_rejects_reused_challenge() -> None:
    rp = _rp()
    challenge = rp.begin_registration("alice", authenticated=True)
    inp = RegistrationInput("alice", RP_ID, ORIGIN, challenge, "c1", b"pk", True, 0)
    rp.complete_registration(inp)
    with pytest.raises(WebAuthnError):  # AC-04 reused challenge
        rp.complete_registration(inp)


def test_registration_rejects_origin_mismatch() -> None:
    rp = _rp()
    challenge = rp.begin_registration("alice", authenticated=True)
    with pytest.raises(WebAuthnError):  # AC-04
        rp.complete_registration(
            RegistrationInput("alice", RP_ID, "https://evil.example", challenge, "c1", b"pk",
                              True, 0)
        )


def _assert_input(rp, user="alice", cred="cred-1", count=1, uv=True, origin=ORIGIN, rp_id=RP_ID):
    challenge = rp.begin_assertion(user)
    return AssertionInput(user, rp_id, origin, challenge, cred, uv, count, b"sig", b"data")


def test_valid_assertion_succeeds_and_increments_counter() -> None:
    rp = _rp()
    _register(rp, count=0)
    cred = rp.verify_assertion(_assert_input(rp, count=1))  # AC-01
    assert cred.user_id == "alice"
    # counter advanced -> a replay at the same count is rejected
    with pytest.raises(WebAuthnError):
        rp.verify_assertion(_assert_input(rp, count=1))


def test_assertion_rejects_absent_uv() -> None:
    rp = _rp()
    _register(rp)
    with pytest.raises(WebAuthnError):  # AC-03
        rp.verify_assertion(_assert_input(rp, uv=False))


def test_assertion_rejects_non_incrementing_counter() -> None:
    rp = _rp()
    _register(rp, count=5)
    with pytest.raises(WebAuthnError):  # AC-03 cloned/replayed authenticator
        rp.verify_assertion(_assert_input(rp, count=5))


def test_assertion_rejects_origin_or_rpid_mismatch() -> None:
    rp = _rp()
    _register(rp)
    with pytest.raises(WebAuthnError):  # AC-03
        rp.verify_assertion(_assert_input(rp, origin="https://evil.example"))
    with pytest.raises(WebAuthnError):
        rp.verify_assertion(_assert_input(rp, rp_id="evil.example"))


def test_assertion_must_resolve_to_one_owned_credential() -> None:
    rp = _rp()
    _register(rp, user="alice", cred="cred-1")
    # bob has no credential -> denied
    with pytest.raises(WebAuthnError):  # AC-04
        rp.verify_assertion(_assert_input(rp, user="bob", cred="cred-1"))


def test_failed_signature_rejected() -> None:
    rp = _rp(verify=lambda pk, sig, data: False)  # default-deny verifier
    _register(rp, count=0)
    with pytest.raises(WebAuthnError):
        rp.verify_assertion(_assert_input(rp, count=1))


def test_mfa_stepup_rotates_session() -> None:
    # AC-02 (issue 032 + 030): a successful step-up rotates the session id.
    rp = _rp()
    _register(rp)
    mgr = SessionManager()
    session = mgr.promote(None, "alice")
    rp.verify_assertion(_assert_input(rp, count=1))
    rotated = mgr.rotate(session.sid)
    assert rotated.sid != session.sid and mgr.validate(session.sid) is None
