"""Tests for Stage 19B — Multi-User Identity & Strict Data Isolation.

Covers:
1. User 1 (Mock User) & User 2 (College Gmail) identity resolution.
2. Server-controlled session management and rejection of unregistered emails.
3. Anti-impersonation: tampering with ?user_id=2 or forged X-User-Email is rejected/ignored.
4. Email isolation: User 1 sees 15 test emails, User 2 sees 0 emails.
5. Cross-user ID access: User 2 cannot retrieve User 1 email by ID (404).
6. Analysis isolation: User 2 cannot retrieve User 1 AI analysis by email_id (404).
7. Action items & deadlines isolation: User 2 sees 0 actions; User 2 cannot update User 1 action item (404).
8. Meetings isolation: User 2 sees 0 meetings.
9. Cross-email intelligence isolation: User 2 cannot access thread context for User 1 email (404); topic clusters are scoped.
10. Preference isolation: updating User 1 preferences does not touch User 2 preferences and vice-versa.
11. Provider status & security: User 1 sees mock provider; User 1 cannot initiate Gmail OAuth or disconnect Gmail (403).
12. Zero-credential / unauthenticated safety: requests without session tokens default safely to User 1 with zero regression.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.database.session import SessionLocal, init_db
from backend.app.models import User, Email, AIAnalysis, ActionItem, Meeting, FacultyPreference

client = TestClient(app)

USER1_EMAIL = "mock.faculty@university.edu"
USER2_EMAIL = "shivaprakashp.cs24@bitsathy.ac.in"


@pytest.fixture(scope="module", autouse=True)
def ensure_db():
    """Ensure database is initialized and seeded before tests run."""
    init_db()
    db = SessionLocal()
    try:
        db.query(Email).filter(Email.user_id == 2).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(Email).filter(Email.user_id == 2).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def user1_session():
    """Obtain a server-issued session token for User 1."""
    resp = client.post("/api/auth/switch-session", json={"email": USER1_EMAIL})
    assert resp.status_code == 200
    token = resp.json()["session_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user2_session():
    """Obtain a server-issued session token for User 2."""
    resp = client.post("/api/auth/switch-session", json={"email": USER2_EMAIL})
    assert resp.status_code == 200
    token = resp.json()["session_token"]
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. Identity Resolution & Session Management
# ==============================================================================

def test_unregistered_email_session_rejected():
    """Backend strictly rejects session requests for unregistered emails."""
    resp = client.post("/api/auth/switch-session", json={"email": "attacker@evil.com"})
    assert resp.status_code == 400
    assert "User not authorized" in resp.json()["detail"]


def test_user1_session_resolves_mock_user(user1_session):
    """User 1 session resolves to mock.faculty@university.edu."""
    resp = client.get("/api/auth/me", headers=user1_session)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["email"] == USER1_EMAIL
    assert data["provider_type"] == "mock"


def test_user2_session_resolves_college_user(user2_session):
    """User 2 session resolves to shivaprakashp.cs24@bitsathy.ac.in."""
    resp = client.get("/api/auth/me", headers=user2_session)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 2
    assert data["email"] == USER2_EMAIL
    assert data["provider_type"] == "gmail"


def test_unauthenticated_request_defaults_to_user1():
    """Backward compatibility: requests without credentials safely default to User 1."""
    client.cookies.clear()
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["email"] == USER1_EMAIL


def test_list_registered_users():
    """Auth endpoint lists the two pre-registered identities."""
    resp = client.get("/api/auth/users")
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) == 2
    emails = [u["email"] for u in users]
    assert USER1_EMAIL in emails
    assert USER2_EMAIL in emails


# ==============================================================================
# 2. Anti-Impersonation & Security Checks
# ==============================================================================

def test_anti_impersonation_forged_header_without_token():
    """Forged X-User-Email without a valid server token is ignored; defaults safely to User 1."""
    client.cookies.clear()
    resp = client.get("/api/auth/me", headers={"X-User-Email": USER2_EMAIL})
    assert resp.status_code == 200
    data = resp.json()
    # Must NOT be resolved to User 2 without session token!
    assert data["id"] == 1
    assert data["email"] == USER1_EMAIL


def test_anti_impersonation_query_param_tampering(user1_session):
    """Passing ?user_id=2 in query params does NOT override User 1's identity."""
    resp = client.get("/api/emails?user_id=2", headers=user1_session)
    assert resp.status_code == 200
    emails = resp.json()
    # User 1 should still see their 15 emails, not User 2's inbox
    assert len(emails) == 15


# ==============================================================================
# 3. Email Data Isolation
# ==============================================================================

def test_user1_sees_all_seeded_test_emails(user1_session):
    """User 1 owns and sees all 15 pre-existing test emails."""
    resp = client.get("/api/emails", headers=user1_session)
    assert resp.status_code == 200
    emails = resp.json()
    assert len(emails) == 15


def test_user2_sees_zero_emails_initially(user2_session):
    """User 2 inbox is completely empty and isolated from User 1."""
    resp = client.get("/api/emails", headers=user2_session)
    assert resp.status_code == 200
    emails = resp.json()
    assert len(emails) == 0


def test_user2_cannot_access_user1_email_by_id(user2_session):
    """User 2 attempting to view User 1's email ID receives HTTP 404."""
    # Email #1 belongs to User 1
    resp = client.get("/api/emails/1", headers=user2_session)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_user2_cannot_mark_user1_email_as_read(user2_session):
    """User 2 cannot mark User 1's email as read."""
    resp = client.patch("/api/emails/1/read", headers=user2_session)
    assert resp.status_code == 404


def test_search_isolation(user1_session, user2_session):
    """Search queries only return emails belonging to the authenticated user."""
    # Search for common academic keyword in User 1 inbox
    resp1 = client.get("/api/search?q=exam", headers=user1_session)
    assert resp1.status_code == 200
    assert len(resp1.json()) > 0

    # Same search in User 2 inbox returns 0 results
    resp2 = client.get("/api/search?q=exam", headers=user2_session)
    assert resp2.status_code == 200
    assert len(resp2.json()) == 0


# ==============================================================================
# 4. AI Analysis, Action Items & Meetings Isolation
# ==============================================================================

def test_user2_cannot_access_user1_analysis(user2_session):
    """User 2 cannot retrieve AI analysis for User 1's email."""
    resp = client.get("/api/analysis/1", headers=user2_session)
    assert resp.status_code == 404


def test_dashboard_metrics_isolation(user1_session, user2_session):
    """Dashboard metrics reflect only user-owned records."""
    resp1 = client.get("/api/dashboard", headers=user1_session)
    assert resp1.status_code == 200
    d1 = resp1.json()
    assert d1["metrics"]["total_emails"] == 15

    resp2 = client.get("/api/dashboard", headers=user2_session)
    assert resp2.status_code == 200
    d2 = resp2.json()
    assert d2["metrics"]["total_emails"] == 0
    assert d2["metrics"]["pending_actions_count"] == 0
    assert len(d2["priority_emails"]) == 0
    assert len(d2["upcoming_deadlines"]) == 0
    assert len(d2["upcoming_meetings"]) == 0
    assert len(d2["pending_tasks"]) == 0


def test_action_items_isolation(user1_session, user2_session):
    """Action items are strictly user-scoped."""
    resp1 = client.get("/api/action-items", headers=user1_session)
    assert resp1.status_code == 200
    actions1 = resp1.json()
    assert len(actions1) > 0

    resp2 = client.get("/api/action-items", headers=user2_session)
    assert resp2.status_code == 200
    actions2 = resp2.json()
    assert len(actions2) == 0


def test_user2_cannot_modify_user1_action_item(user1_session, user2_session):
    """User 2 cannot complete or modify User 1's action item."""
    # Get an existing action item from User 1
    resp1 = client.get("/api/action-items", headers=user1_session)
    action_id = resp1.json()[0]["id"]

    # Attempt to update via User 2
    resp2 = client.patch(
        f"/api/action-items/{action_id}",
        json={"completed": True},
        headers=user2_session
    )
    assert resp2.status_code == 404


def test_meetings_isolation(user1_session, user2_session):
    """Meetings list is strictly user-scoped."""
    resp1 = client.get("/api/meetings", headers=user1_session)
    assert resp1.status_code == 200
    assert len(resp1.json()) > 0

    resp2 = client.get("/api/meetings", headers=user2_session)
    assert resp2.status_code == 200
    assert len(resp2.json()) == 0


# ==============================================================================
# 5. Cross-Email Intelligence Isolation
# ==============================================================================

def test_cross_intelligence_isolation(user1_session, user2_session):
    """User 2 cannot access thread context for User 1 email."""
    resp = client.get("/api/emails/1/cross-intelligence", headers=user2_session)
    assert resp.status_code == 404


def test_topic_clusters_isolation(user1_session, user2_session):
    """Topic clusters are scoped strictly to the authenticated user's inbox."""
    resp1 = client.get("/api/cross-intelligence/clusters", headers=user1_session)
    assert resp1.status_code == 200
    assert resp1.json()["total_clusters"] > 0

    resp2 = client.get("/api/cross-intelligence/clusters", headers=user2_session)
    assert resp2.status_code == 200
    assert resp2.json()["total_clusters"] == 0


# ==============================================================================
# 6. Faculty Preferences Isolation
# ==============================================================================

def test_preferences_isolation(user1_session, user2_session):
    """User 1 and User 2 maintain independent preference records."""
    # Update User 1 preference
    resp1 = client.put(
        "/api/preferences",
        json={"faculty_name": "Prof. Mock User Unique Name", "priority_mode": "DEADLINE_HEAVY"},
        headers=user1_session
    )
    assert resp1.status_code == 200
    assert resp1.json()["faculty_name"] == "Prof. Mock User Unique Name"
    assert resp1.json()["priority_mode"] == "DEADLINE_HEAVY"

    # User 2 preference must NOT have changed
    resp2 = client.get("/api/preferences", headers=user2_session)
    assert resp2.status_code == 200
    assert resp2.json()["faculty_name"] != "Prof. Mock User Unique Name"

    # Update User 2 preference
    resp2_update = client.put(
        "/api/preferences",
        json={"faculty_name": "Shivaprakash P", "priority_mode": "AUTHORITY_FIRST"},
        headers=user2_session
    )
    assert resp2_update.status_code == 200
    assert resp2_update.json()["faculty_name"] == "Shivaprakash P"
    assert resp2_update.json()["priority_mode"] == "AUTHORITY_FIRST"

    # Re-verify User 1 unchanged
    resp1_check = client.get("/api/preferences", headers=user1_session)
    assert resp1_check.status_code == 200
    assert resp1_check.json()["faculty_name"] == "Prof. Mock User Unique Name"
    assert resp1_check.json()["priority_mode"] == "DEADLINE_HEAVY"


# ==============================================================================
# 7. Provider Status & Disconnect Permissions
# ==============================================================================

def test_provider_status_scoped_user1(user1_session):
    """User 1 provider status reports mock and isolated Gmail state."""
    resp = client.get("/api/email-provider/status", headers=user1_session)
    assert resp.status_code == 200
    data = resp.json()
    assert data["active_provider"] == "mock"
    assert data["is_mock"] is True
    assert data["user_id"] == 1
    assert data["gmail_oauth"]["is_connected"] is False


def test_user1_forbidden_from_gmail_connect(user1_session):
    """User 1 cannot initiate Gmail OAuth connection (returns 403)."""
    resp = client.get("/api/email-provider/gmail/connect", headers=user1_session)
    assert resp.status_code == 403
    assert "User 1 (Mock User) operates exclusively with MockEmailProvider" in resp.json()["detail"]


def test_user1_forbidden_from_gmail_disconnect(user1_session):
    """User 1 cannot disconnect or modify User 2's College Gmail connection (returns 403)."""
    resp = client.post("/api/email-provider/gmail/disconnect", headers=user1_session)
    assert resp.status_code == 403
    assert "User 1 (Mock User) cannot disconnect" in resp.json()["detail"]


def test_dashboard_priority_breakdown_and_isolation(user1_session, user2_session):
    """Verify Dashboard metrics include High/Medium/Low priority counts and preserve strict user scoping."""
    # User 1 Dashboard
    resp1 = client.get("/api/dashboard", headers=user1_session)
    assert resp1.status_code == 200
    d1 = resp1.json()
    m1 = d1["metrics"]
    assert "medium_priority_count" in m1
    assert "low_priority_count" in m1
    assert m1["total_emails"] == 15
    assert m1["high_priority_count"] >= 5
    assert m1["medium_priority_count"] >= 3
    assert m1["low_priority_count"] >= 1
    assert len(d1["priority_emails"]) > 0
    assert len(d1["upcoming_deadlines"]) > 0
    assert len(d1["upcoming_meetings"]) > 0
    assert len(d1["pending_tasks"]) > 0
    assert len(d1["recent_emails"]) == 5

    # User 2 Dashboard before sync (empty state verification)
    resp2 = client.get("/api/dashboard", headers=user2_session)
    assert resp2.status_code == 200
    d2 = resp2.json()
    m2 = d2["metrics"]
    assert m2["total_emails"] == 0
    assert m2["high_priority_count"] == 0
    assert m2["medium_priority_count"] == 0
    assert m2["low_priority_count"] == 0
    assert len(d2["priority_emails"]) == 0
    assert len(d2["upcoming_deadlines"]) == 0
    assert len(d2["upcoming_meetings"]) == 0
    assert len(d2["pending_tasks"]) == 0
    assert len(d2["recent_emails"]) == 0

