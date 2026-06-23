"""Account-linking re-auth + session-binding tests (issue 034 / REQ-AUTH-023)."""

from __future__ import annotations

import pytest

from pingpals_api.auth.account_linking import LinkingCeremony, LinkingError


def test_link_requires_authenticated_session() -> None:
    c = LinkingCeremony()
    with pytest.raises(LinkingError):
        c.begin(session_id="", user_id="alice", reauth_verified=True)


def test_link_requires_fresh_reauth() -> None:
    c = LinkingCeremony()
    with pytest.raises(LinkingError):  # AC-01
        c.begin(session_id="sess-1", user_id="alice", reauth_verified=False)


def test_link_commits_to_initiating_session_user() -> None:
    c = LinkingCeremony()
    txn = c.begin(session_id="sess-1", user_id="alice", reauth_verified=True)
    assert c.complete(txn.state, callback_session_id="sess-1") == "alice"  # AC-02


def test_callback_in_different_session_rejected() -> None:
    c = LinkingCeremony()
    txn = c.begin(session_id="sess-1", user_id="alice", reauth_verified=True)
    with pytest.raises(LinkingError):  # AC-03
        c.complete(txn.state, callback_session_id="sess-ATTACKER")


def test_replayed_callback_rejected() -> None:
    c = LinkingCeremony()
    txn = c.begin(session_id="sess-1", user_id="alice", reauth_verified=True)
    c.complete(txn.state, callback_session_id="sess-1")
    with pytest.raises(LinkingError):  # AC-03/AC-04 replay -> single-use consumed
        c.complete(txn.state, callback_session_id="sess-1")


def test_forged_state_rejected() -> None:
    c = LinkingCeremony()
    with pytest.raises(LinkingError):  # AC-04 no per-session state binding
        c.complete("forged-state", callback_session_id="sess-1")
