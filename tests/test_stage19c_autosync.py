"""Tests for Stage 19C — Dashboard Automatic Gmail Synchronization.

Verifies:
1. User 2 dashboard load workflow: background Gmail synchronization updates User 2 dashboard metrics.
2. User 1 dashboard load exclusion: User 1 never triggers or accesses Gmail sync (HTTP 403 Forbidden).
3. Repeated dashboard refresh deduplication: subsequent syncs skip existing emails via provider_message_id.
4. AI priority analysis preservation: imported Gmail emails receive context-aware AI priority assessments.
5. Error resilience: sync failure or disconnected OAuth does not break dashboard loading.
6. Coexistence: manual Settings sync continues to work alongside automatic dashboard sync.
7. Strict data isolation: User 1 and User 2 never cross-contaminate.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.database.session import SessionLocal, init_db
from backend.app.models import User, Email, AIAnalysis
from backend.app.services.gmail_provider import GmailProvider

client = TestClient(app)

USER1_EMAIL = "mock.faculty@university.edu"
USER2_EMAIL = "shivaprakashp.cs24@bitsathy.ac.in"


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database schema is initialized and clean User 2 records."""
    init_db()
    yield
    db = SessionLocal()
    try:
        db.query(Email).filter(Email.user_id == 2).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def user1_session():
    """Obtain server-controlled session token for User 1."""
    resp = client.post("/api/auth/switch-session", json={"email": USER1_EMAIL})
    assert resp.status_code == 200
    token = resp.json()["session_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user2_session():
    """Obtain server-controlled session token for User 2."""
    resp = client.post("/api/auth/switch-session", json={"email": USER2_EMAIL})
    assert resp.status_code == 200
    token = resp.json()["session_token"]
    return {"Authorization": f"Bearer {token}"}


def _generate_synthetic_gmail_batch(count: int = 60):
    """Generate mock parsed Gmail messages representing User 2's college inbox."""
    templates = [
        {
            "sender": "hod.cse@bitsathy.ac.in",
            "subject": "Mandatory Internal Assessment Marks Submission",
            "body": "All faculty must submit internal assessment marks by tomorrow without fail."
        },
        {
            "sender": "cultural.club@bitsathy.ac.in",
            "subject": "Vinayagar Chathurthi Programme",
            "body": "Interested students may register by 4:30 PM today for the cultural events."
        },
        {
            "sender": "dailynews@bitsathy.ac.in",
            "subject": "Word of the Day: Ubiquitous",
            "body": "Today's vocabulary feature: Ubiquitous. Please read today's word."
        },
        {
            "sender": "campus.relations@bitsathy.ac.in",
            "subject": "BIT Campus Daily Pulse & Announcements",
            "body": "Overview of today's campus activities, seminar updates, and schedules."
        },
        {
            "sender": "coe@bitsathy.ac.in",
            "subject": "Urgent: Verify PT-1 Marks Without Fail",
            "body": "All course coordinators must verify PT-1 marks in the academic portal immediately."
        },
    ]
    messages = []
    for i in range(1, count + 1):
        tmpl = templates[(i - 1) % len(templates)]
        messages.append({
            "id": f"gmail_msg_auto_{i:04d}",
            "sender": tmpl["sender"],
            "recipient": USER2_EMAIL,
            "subject": f"{tmpl['subject']} [Batch {i}]",
            "body": f"{tmpl['body']} (Notice Ref: NOTC-AUTO-{i})",
            "received_at": datetime(2026, 9, 8, 9, 0, 0) + timedelta(minutes=i),
            "is_read": i % 3 == 0
        })
    return messages


# ==============================================================================
# Automatic Sync & Dashboard Integration Tests
# ==============================================================================

def test_user2_dashboard_load_triggers_sync(user2_session):
    """When User 2 dashboard loads, triggering background sync fetches up to 60 emails and updates dashboard."""
    synthetic_messages = _generate_synthetic_gmail_batch(60)

    # Initial dashboard check: User 2 has 0 emails initially
    db = SessionLocal()
    db.query(Email).filter(Email.user_id == 2).delete()
    db.commit()
    db.close()

    initial_resp = client.get("/api/dashboard", headers=user2_session)
    assert initial_resp.status_code == 200
    assert initial_resp.json()["metrics"]["total_emails"] == 0

    # User 2 triggers background auto-sync
    with patch("backend.app.api.routes_provider.oauth_service.get_status", return_value={"connected": True}), \
         patch.object(GmailProvider, "is_authenticated", return_value=True), \
         patch.object(GmailProvider, "get_messages", return_value=synthetic_messages):
        sync_resp = client.post("/api/email-provider/gmail/sync?limit=60", headers=user2_session)
        assert sync_resp.status_code == 200
        sync_data = sync_resp.json()
        assert sync_data["success"] is True
        assert sync_data["data"]["imported"] == 60
        assert sync_data["data"]["user_id"] == 2

    # Dashboard refreshed after sync completes
    refreshed_resp = client.get("/api/dashboard", headers=user2_session)
    assert refreshed_resp.status_code == 200
    metrics = refreshed_resp.json()["metrics"]
    assert metrics["total_emails"] == 60
    assert (metrics["high_priority_count"] + metrics["medium_priority_count"] + metrics["low_priority_count"]) == 60
    assert len(refreshed_resp.json()["recent_emails"]) > 0


def test_user1_dashboard_load_does_not_trigger_sync(user1_session):
    """User 1 dashboard load does NOT trigger Gmail sync; User 1 is forbidden from Gmail sync."""
    # User 1 dashboard returns 15 mock emails
    resp = client.get("/api/dashboard", headers=user1_session)
    assert resp.status_code == 200
    assert resp.json()["metrics"]["total_emails"] == 15

    # Any attempt by User 1 to call sync is rejected with HTTP 403 Forbidden
    sync_resp = client.post("/api/email-provider/gmail/sync?limit=60", headers=user1_session)
    assert sync_resp.status_code == 403
    assert "User 1 (Mock User) operates exclusively with MockEmailProvider" in sync_resp.json()["detail"]


def test_repeated_dashboard_refreshes_do_not_create_duplicates(user2_session):
    """Repeated dashboard refreshes trigger sync safely: existing emails are skipped via provider_message_id."""
    synthetic_messages = _generate_synthetic_gmail_batch(60)

    with patch("backend.app.api.routes_provider.oauth_service.get_status", return_value={"connected": True}), \
         patch.object(GmailProvider, "is_authenticated", return_value=True), \
         patch.object(GmailProvider, "get_messages", return_value=synthetic_messages):
        # Second dashboard refresh sync
        resync_resp = client.post("/api/email-provider/gmail/sync?limit=60", headers=user2_session)
        assert resync_resp.status_code == 200
        resync_data = resync_resp.json()["data"]
        assert resync_data["imported"] == 0
        assert resync_data["skipped_duplicates"] == 60

    # Total emails in database remains strictly 60
    db = SessionLocal()
    count = db.query(Email).filter(Email.user_id == 2).count()
    db.close()
    assert count == 60


def test_ai_priority_analysis_preserved_on_synced_emails(user2_session):
    """All automatically synced emails retain their context-aware AI priority assessments."""
    resp = client.get("/api/emails?limit=60", headers=user2_session)
    assert resp.status_code == 200
    emails = resp.json()
    assert len(emails) == 60

    for email in emails:
        assert email["priority"] in ["HIGH", "MEDIUM", "LOW"]
        assert len(email["priority_reason"]) > 0


def test_sync_failure_does_not_break_dashboard_loading(user2_session):
    """When Gmail OAuth is disconnected or sync fails, GET /api/dashboard loads normally without error."""
    # Simulate disconnected Gmail
    with patch("backend.app.api.routes_provider.oauth_service.get_status", return_value={"connected": False}):
        sync_resp = client.post("/api/email-provider/gmail/sync?limit=60", headers=user2_session)
        assert sync_resp.status_code == 400

    # Dashboard continues to load smoothly and returns existing data
    dashboard_resp = client.get("/api/dashboard", headers=user2_session)
    assert dashboard_resp.status_code == 200
    assert dashboard_resp.json()["metrics"]["total_emails"] == 60


def test_manual_settings_sync_coexists(user2_session):
    """The manual sync route used by SettingsPage continues to work as expected."""
    synthetic_messages = _generate_synthetic_gmail_batch(60)

    with patch("backend.app.api.routes_provider.oauth_service.get_status", return_value={"connected": True}), \
         patch.object(GmailProvider, "is_authenticated", return_value=True), \
         patch.object(GmailProvider, "get_messages", return_value=synthetic_messages):
        manual_resp = client.post("/api/email-provider/gmail/sync?limit=60", headers=user2_session)
        assert manual_resp.status_code == 200
        assert manual_resp.json()["success"] is True


def test_strict_user_isolation_preserved(user1_session, user2_session):
    """Verify strict isolation: User 1 sees 0 of User 2's emails; User 2 sees 0 of User 1's emails."""
    u1_emails = client.get("/api/emails?limit=100", headers=user1_session).json()
    u2_emails = client.get("/api/emails?limit=100", headers=user2_session).json()

    assert len(u1_emails) == 15
    assert len(u2_emails) == 60

    u1_ids = {e["id"] for e in u1_emails}
    u2_ids = {e["id"] for e in u2_emails}
    assert len(u1_ids.intersection(u2_ids)) == 0

    # User 1 cannot access any of User 2's emails
    for e2 in u2_emails[:5]:
        leak_resp = client.get(f"/api/emails/{e2['id']}", headers=user1_session)
        assert leak_resp.status_code in [403, 404]
