"""Session management tests (issue 030 / REQ-AUTH-019)."""

from __future__ import annotations

from pingpals_api.app import create_app
from pingpals_api.auth.session import COOKIE_NAME, SessionManager, apply_session_cookie
from pingpals_api.config import SECRET_KEY_NAME, MappingSecretStore, TestConfig


class Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def test_privilege_transition_issues_fresh_id_and_invalidates_prior() -> None:
    mgr = SessionManager(now=Clock())
    anon = mgr.begin_anonymous()
    promoted = mgr.promote(anon.sid, "alice")
    assert promoted.sid != anon.sid          # AC-03 fresh id
    assert promoted.authenticated is True
    assert mgr.validate(anon.sid) is None     # AC-04 pre-auth id never valid afterwards
    assert mgr.validate(promoted.sid).user_id == "alice"


def test_idle_and_absolute_expiry() -> None:
    clock = Clock()
    mgr = SessionManager(idle_seconds=100, absolute_seconds=1000, now=clock)
    s = mgr.promote(None, "alice")
    clock.t += 101
    assert mgr.validate(s.sid) is None        # AC-02 idle expiry

    clock.t = 1000.0
    s2 = mgr.promote(None, "bob")
    clock.t += 1001
    assert mgr.validate(s2.sid) is None        # AC-02 absolute expiry


def test_server_side_revocation() -> None:
    mgr = SessionManager(now=Clock())
    s = mgr.promote(None, "alice")
    assert mgr.revoke(s.sid) is True
    assert mgr.validate(s.sid) is None         # AC-02 revoked rejected next request


def test_revoke_all_for_user() -> None:
    mgr = SessionManager(now=Clock())
    a1 = mgr.promote(None, "alice")
    a2 = mgr.promote(None, "alice")
    b = mgr.promote(None, "bob")
    assert mgr.revoke_all_for_user("alice") == 2
    assert mgr.validate(a1.sid) is None and mgr.validate(a2.sid) is None
    assert mgr.validate(b.sid) is not None


def test_rotate_keeps_user_changes_id() -> None:
    mgr = SessionManager(now=Clock())
    s = mgr.promote(None, "alice")
    rotated = mgr.rotate(s.sid)
    assert rotated.sid != s.sid and rotated.user_id == "alice"
    assert mgr.validate(s.sid) is None


def test_cookie_is_httponly_secure_samesite() -> None:
    app = create_app(TestConfig(), MappingSecretStore({SECRET_KEY_NAME: "x" * 40}))

    @app.get("/setsession")
    def _set():  # type: ignore[no-untyped-def]
        from flask import make_response

        resp = make_response({"ok": True})
        apply_session_cookie(resp, "sid-abc", secure=True)
        return resp

    resp = app.test_client().get("/setsession")
    cookie = resp.headers.get("Set-Cookie", "")
    assert COOKIE_NAME in cookie  # AC-01
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=Lax" in cookie
