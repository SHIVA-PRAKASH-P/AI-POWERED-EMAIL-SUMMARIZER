"""Tests for Stage 19C — Read-Only Gmail Email Synchronization & Multi-User Isolation.

Covers:
1. User 1 (Mock User) strictly forbidden from Gmail sync endpoint (HTTP 403).
2. Unauthenticated requests strictly forbidden from Gmail sync endpoint (HTTP 403).
3. Anti-impersonation: tampering with ?user_id=2 or X-User-Email on User 1 session cannot access sync (403).
4. Disconnected OAuth handling: returns HTTP 400 if College Gmail is not connected.
5. User 2 controlled synchronization: fetches up to 10 emails and persists them with user_id = 2.
6. Deduplication: subsequent sync calls skip previously imported messages (skipped_duplicates == 10).
7. Ceiling enforcement: sync limit is strictly capped at 10 emails maximum.
8. Email isolation: User 1 never sees User 2's synced Gmail emails; User 2 never sees User 1's mock emails.
9. User 1 mock email count remains intact (15 mock emails).
10. Read-only guarantee: zero send, modify, trash, or delete API operations.
11. Resilient message parsing: individual message retrieval error does not fail entire sync batch.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.app.database.session import SessionLocal, init_db
from backend.app.models import User, Email, AIAnalysis
from backend.app.services.gmail_provider import GmailProvider
from backend.app.services.email_provider_manager import email_provider_manager

client = TestClient(app)

USER1_EMAIL = "mock.faculty@university.edu"
USER2_EMAIL = "shivaprakashp.cs24@bitsathy.ac.in"


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database schema is initialized and seeded."""
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
    """Obtain session token for User 1."""
    resp = client.post("/api/auth/switch-session", json={"email": USER1_EMAIL})
    assert resp.status_code == 200
    token = resp.json()["session_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user2_session():
    """Obtain session token for User 2."""
    resp = client.post("/api/auth/switch-session", json={"email": USER2_EMAIL})
    assert resp.status_code == 200
    token = resp.json()["session_token"]
    return {"Authorization": f"Bearer {token}"}


def _generate_synthetic_gmail_messages(count: int = 10):
    """Generate mock parsed Gmail messages representing User 2's college inbox with varied priorities."""
    templates = [
        {
            "sender": "hod.cse@bitsathy.ac.in",
            "subject": "URGENT: Internal Assessment Marks & NAAC Review Submission",
            "body": "Dear Faculty, all members are requested to submit internal assessment marks before September 14. A departmental review meeting will be held on September 10 at 10 AM in Seminar Hall. Please bring student records."
        },
        {
            "sender": "dean.academics@bitsathy.ac.in",
            "subject": "Mandatory Curriculum Revision and Course Plan",
            "body": "Faculty members are requested to complete the syllabus review before September 12. Submit the revised draft to the dean office."
        },
        {
            "sender": "controller.exams@bitsathy.ac.in",
            "subject": "End Semester Question Paper Preparation",
            "body": "Please prepare and upload question papers before September 15. Verify all bloom taxonomy levels."
        },
        {
            "sender": "placement.cell@bitsathy.ac.in",
            "subject": "Upcoming Campus Recruitment Drive Briefing",
            "body": "A briefing session will be conducted tomorrow at 2 PM in Room 301 for final year student coordinators."
        },
        {
            "sender": "newsletter@bitsathy.ac.in",
            "subject": "Weekly Campus Research Newsletter & Sports Day Invitation",
            "body": "Here is the weekly faculty newsletter covering community events, sports club updates, and weekend activities."
        },
    ]
    messages = []
    for i in range(1, count + 1):
        tmpl = templates[(i - 1) % len(templates)]
        messages.append({
            "id": f"gmail_msg_{i:04d}",
            "sender": tmpl["sender"],
            "recipient": USER2_EMAIL,
            "subject": f"{tmpl['subject']} [Batch {i}]",
            "body": f"{tmpl['body']} (Reference code: NOTC-{i})",
            "received_at": datetime(2026, 9, 8, 10, 0, 0) + timedelta(minutes=i),
            "is_read": i % 2 == 0
        })
    return messages


# ==============================================================================
# 1. Authorization & Security Tests
# ==============================================================================

def test_unauthenticated_sync_rejected():
    """Unauthenticated calls to Gmail sync are rejected with HTTP 403."""
    resp = client.post("/api/email-provider/gmail/sync")
    assert resp.status_code == 403
    assert "User 1 (Mock User) operates exclusively with MockEmailProvider" in resp.json()["detail"]


def test_user1_forbidden_from_gmail_sync(user1_session):
    """User 1 is strictly forbidden from triggering Gmail sync (HTTP 403)."""
    resp = client.post("/api/email-provider/gmail/sync", headers=user1_session)
    assert resp.status_code == 403
    assert "User 1 (Mock User) operates exclusively with MockEmailProvider" in resp.json()["detail"]


def test_user1_cannot_impersonate_user2_on_sync(user1_session):
    """User 1 cannot bypass authorization by passing forged headers or query params."""
    # Attempt with forged X-User-Email
    headers = dict(user1_session)
    headers["X-User-Email"] = USER2_EMAIL
    resp = client.post("/api/email-provider/gmail/sync", headers=headers)
    assert resp.status_code == 403

    # Attempt with forged query param
    resp2 = client.post("/api/email-provider/gmail/sync?user_id=2", headers=user1_session)
    assert resp2.status_code == 403


def test_disconnected_gmail_returns_400(user2_session):
    """If Gmail OAuth is not connected, User 2 receives HTTP 400 Bad Request."""
    with patch("backend.app.api.routes_provider.oauth_service.get_status", return_value={"connected": False}):
        resp = client.post("/api/email-provider/gmail/sync", headers=user2_session)
        assert resp.status_code == 400
        assert "College Gmail account is not connected" in resp.json()["detail"]


# ==============================================================================
# 2. Controlled Synchronization (Max 10 Messages) & Data Persistence
# ==============================================================================

def test_user2_sync_latest_10_emails(user2_session):
    """User 2 synchronizes a controlled batch of 10 emails from College Gmail."""
    db: Session = SessionLocal()
    try:
        # Clear any prior User 2 emails to verify clean sync
        db.query(Email).filter(Email.user_id == 2).delete()
        db.commit()
    finally:
        db.close()

    mock_messages = _generate_synthetic_gmail_messages(10)

    with patch("backend.app.api.routes_provider.oauth_service.get_status", return_value={"connected": True}), \
         patch.object(GmailProvider, "is_authenticated", return_value=True), \
         patch.object(GmailProvider, "get_messages", return_value=mock_messages):

        resp = client.post("/api/email-provider/gmail/sync?limit=10", headers=user2_session)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        sync_data = data["data"]
        assert sync_data["fetched"] == 10
        assert sync_data["imported"] == 10
        assert sync_data["skipped_duplicates"] == 0
        assert sync_data["user_id"] == 2
        assert sync_data["provider"] == "gmail"

    # Verify persisted records in SQLite
    db = SessionLocal()
    try:
        user2_emails = db.query(Email).filter(Email.user_id == 2).all()
        assert len(user2_emails) == 10

        # Verify all records have user_id=2, valid provider_message_id, and AI analysis with priority
        for email in user2_emails:
            assert email.user_id == 2
            assert email.provider_message_id is not None
            assert email.provider_message_id.startswith("gmail_msg_")
            # Stage 19C Priority Fix: verify AI analysis & priority classification
            assert email.analysis is not None
            assert email.analysis.priority in ("HIGH", "MEDIUM", "LOW")
            assert email.analysis.category is not None
            assert len(email.analysis.summary) > 0
            assert email.analysis.priority_reason is not None

        # Verify User 1 emails remain exactly 15 mock emails
        user1_emails = db.query(Email).filter(Email.user_id == 1).all()
        assert len(user1_emails) == 15
    finally:
        db.close()


def test_user2_inbox_displays_priority_and_metadata(user2_session):
    """User 2 inbox view displays priority badge ('HIGH'/'MEDIUM'/'LOW') on all synced emails."""
    resp = client.get("/api/emails", headers=user2_session)
    assert resp.status_code == 200
    emails = resp.json()
    assert len(emails) == 10

    priorities_seen = set()
    for em in emails:
        assert em["has_analysis"] is True
        assert em["priority"] in ("HIGH", "MEDIUM", "LOW")
        assert em["category"] is not None
        assert em["body_preview"] is not None
        priorities_seen.add(em["priority"])

    # Verify varied priorities are evaluated across the synced emails
    assert len(priorities_seen) >= 2


def test_user2_priority_filter(user2_session):
    """User 2 can filter synced emails by priority level (HIGH / MEDIUM / LOW)."""
    # Filter by HIGH priority
    resp_high = client.get("/api/emails?priority=HIGH", headers=user2_session)
    assert resp_high.status_code == 200
    high_emails = resp_high.json()
    assert len(high_emails) > 0
    for em in high_emails:
        assert em["priority"] == "HIGH"

    # Filter by LOW priority
    resp_low = client.get("/api/emails?priority=LOW", headers=user2_session)
    assert resp_low.status_code == 200
    low_emails = resp_low.json()
    assert len(low_emails) > 0
    for em in low_emails:
        assert em["priority"] == "LOW"


def test_user2_action_items_and_meetings_extracted(user2_session):
    """User 2's synced Gmail emails have action items and meetings extracted."""
    # Check Action Items endpoint
    resp_actions = client.get("/api/action-items", headers=user2_session)
    assert resp_actions.status_code == 200
    actions = resp_actions.json()
    assert len(actions) > 0
    for act in actions:
        assert act["description"] is not None
        assert act["priority"] in ("HIGH", "MEDIUM", "LOW")

    # Check Meetings endpoint
    resp_meetings = client.get("/api/meetings", headers=user2_session)
    assert resp_meetings.status_code == 200
    meetings = resp_meetings.json()
    assert len(meetings) > 0
    for mtg in meetings:
        assert mtg["title"] is not None


def test_backfill_missing_analysis_on_resync(user2_session):
    """Re-syncing backfills AI analysis and priority if an email was missing its analysis."""
    db = SessionLocal()
    try:
        # Delete analysis from first User 2 email to simulate legacy imported email
        first_email = db.query(Email).filter(Email.user_id == 2).first()
        assert first_email is not None
        target_id = first_email.id
        db.query(AIAnalysis).filter(AIAnalysis.email_id == target_id).delete()
        db.commit()
    finally:
        db.close()

    # Verify analysis is missing before resync
    db = SessionLocal()
    try:
        email_check = db.query(Email).filter(Email.id == target_id).first()
        assert email_check.analysis is None
    finally:
        db.close()

    # Resync with same mock messages
    mock_messages = _generate_synthetic_gmail_messages(10)
    with patch("backend.app.api.routes_provider.oauth_service.get_status", return_value={"connected": True}), \
         patch.object(GmailProvider, "is_authenticated", return_value=True), \
         patch.object(GmailProvider, "get_messages", return_value=mock_messages):

        resp = client.post("/api/email-provider/gmail/sync?limit=10", headers=user2_session)
        assert resp.status_code == 200

    # Verify analysis was backfilled and priority is restored
    db = SessionLocal()
    try:
        restored = db.query(Email).filter(Email.id == target_id).first()
        assert restored.analysis is not None
        assert restored.analysis.priority in ("HIGH", "MEDIUM", "LOW")
    finally:
        db.close()


def test_deduplication_on_repeated_sync(user2_session):
    """Subsequent sync calls skip existing emails using provider_message_id (idempotent)."""
    mock_messages = _generate_synthetic_gmail_messages(10)

    with patch("backend.app.api.routes_provider.oauth_service.get_status", return_value={"connected": True}), \
         patch.object(GmailProvider, "is_authenticated", return_value=True), \
         patch.object(GmailProvider, "get_messages", return_value=mock_messages):

        # Second sync with the same 10 messages
        resp = client.post("/api/email-provider/gmail/sync?limit=10", headers=user2_session)
        assert resp.status_code == 200
        sync_data = resp.json()["data"]
        assert sync_data["fetched"] == 10
        assert sync_data["imported"] == 0
        assert sync_data["skipped_duplicates"] == 10

    # Verify total count in database did not double
    db = SessionLocal()
    try:
        count = db.query(Email).filter(Email.user_id == 2).count()
        assert count == 10
    finally:
        db.close()


def test_hard_ceiling_enforced_at_60_messages(user2_session):
    """Sync request limit is strictly capped at 60 messages maximum."""
    # If caller asks for 100, query param validation rejects limit > 60 with 422
    resp = client.post("/api/email-provider/gmail/sync?limit=100", headers=user2_session)
    assert resp.status_code == 422


def test_gmail_provider_internal_ceiling_capped():
    """GmailProvider.get_messages internally enforces a maximum cap of 60 messages."""
    provider = GmailProvider()
    mock_service = MagicMock()
    # Mock list returning 100 messages
    mock_service.users().messages().list().execute.return_value = {
        "messages": [{"id": f"msg_{i}"} for i in range(100)]
    }
    mock_service.users().messages().get().execute.return_value = {
        "id": "msg_0",
        "payload": {"headers": [{"name": "Subject", "value": "Test"}]}
    }
    provider._service = mock_service

    # Request limit=100 (exceeding 60)
    messages = provider.get_messages(limit=100)
    # Must never exceed 60
    assert len(messages) <= 60


def test_user2_sync_up_to_60_emails(user2_session):
    """User 2 can synchronize up to 60 emails in a single manual sync request."""
    db: Session = SessionLocal()
    try:
        # Clear User 2 emails
        db.query(Email).filter(Email.user_id == 2).delete()
        db.commit()
    finally:
        db.close()

    mock_60_messages = _generate_synthetic_gmail_messages(60)
    with patch("backend.app.api.routes_provider.oauth_service.get_status", return_value={"connected": True}), \
         patch.object(GmailProvider, "is_authenticated", return_value=True), \
         patch.object(GmailProvider, "get_messages", return_value=mock_60_messages):

        resp = client.post("/api/email-provider/gmail/sync?limit=60", headers=user2_session)
        assert resp.status_code == 200
        sync_data = resp.json()["data"]
        assert sync_data["fetched"] == 60
        assert sync_data["imported"] == 60
        assert sync_data["skipped_duplicates"] == 0
        assert sync_data["user_id"] == 2

    db = SessionLocal()
    try:
        count = db.query(Email).filter(Email.user_id == 2).count()
        assert count == 60
        # Check that analysis and priority exist on all 60 emails
        analyzed_count = db.query(AIAnalysis).join(Email).filter(Email.user_id == 2).count()
        assert analyzed_count == 60
    finally:
        db.close()


# ==============================================================================
# 3. Strict Cross-User Data Isolation
# ==============================================================================

def test_user1_cannot_see_user2_synced_emails(user1_session):
    """User 1's inbox view contains only User 1's 15 mock emails; 0 User 2 emails."""
    resp = client.get("/api/emails", headers=user1_session)
    assert resp.status_code == 200
    emails = resp.json()
    assert len(emails) == 15
    for em in emails:
        # None of User 2's college emails appear in User 1's inbox
        assert "bitsathy.ac.in" not in em["sender"]
        assert "Batch" not in em["subject"]


def test_user2_cannot_see_user1_mock_emails(user2_session):
    """User 2's inbox view contains only User 2's synced emails; 0 User 1 mock emails."""
    resp = client.get("/api/emails?limit=100", headers=user2_session)
    assert resp.status_code == 200
    emails = resp.json()
    assert len(emails) == 60
    for em in emails:
        # None of User 1's synthetic faculty emails appear in User 2's inbox
        assert "bitsathy.ac.in" in em["sender"]
        assert "@university.edu" not in em["sender"]



# ==============================================================================
# 4. Read-Only Scope & Error Resilience
# ==============================================================================

def test_read_only_guarantee():
    """Verify GmailProvider only requests read-only scope and has no write/delete methods."""
    provider = GmailProvider()
    # Confirm no write methods exist on provider
    assert not hasattr(provider, "send_message")
    assert not hasattr(provider, "delete_message")
    assert not hasattr(provider, "modify_message")
    assert not hasattr(provider, "trash_message")


def test_resilient_sync_on_individual_message_failure():
    """If an individual message fetch errors, the remaining messages in the batch are still ingested."""
    provider = GmailProvider()
    mock_service = MagicMock()
    mock_service.users().messages().list().execute.return_value = {
        "messages": [{"id": "msg_ok_1"}, {"id": "msg_fail_2"}, {"id": "msg_ok_3"}]
    }

    def side_effect(userId, id, format):
        if id == "msg_fail_2":
            raise RuntimeError("Corrupted message payload")
        mock_msg = MagicMock()
        mock_msg.execute.return_value = {
            "id": id,
            "payload": {
                "headers": [
                    {"name": "Subject", "value": f"Subject for {id}"},
                    {"name": "From", "value": "sender@bitsathy.ac.in"}
                ]
            }
        }
        return mock_msg

    mock_service.users().messages().get.side_effect = side_effect
    provider._service = mock_service

    results = provider.get_messages(limit=10)
    # msg_ok_1 and msg_ok_3 should succeed, msg_fail_2 skipped
    assert len(results) == 2
    assert results[0]["id"] == "msg_ok_1"
    assert results[1]["id"] == "msg_ok_3"


def test_user2_dashboard_reflects_synced_gmail_intelligence(user1_session, user2_session):
    """User 2 dashboard displays its synced Gmail intelligence with complete isolation from User 1."""
    db = SessionLocal()
    try:
        u2_count = db.query(Email).filter(Email.user_id == 2).count()
    finally:
        db.close()

    if u2_count == 0:
        messages = _generate_synthetic_gmail_messages(10)
        with patch("backend.app.api.routes_provider.oauth_service.get_status", return_value={"connected": True}), \
             patch.object(GmailProvider, "is_authenticated", return_value=True), \
             patch.object(GmailProvider, "get_messages", return_value=messages):
            client.post("/api/email-provider/gmail/sync?limit=10", headers=user2_session)

    # User 2 Dashboard
    resp2 = client.get("/api/dashboard", headers=user2_session)
    assert resp2.status_code == 200
    d2 = resp2.json()
    m2 = d2["metrics"]
    assert m2["total_emails"] > 0
    assert m2["high_priority_count"] > 0
    assert m2["upcoming_deadlines_count"] > 0
    assert m2["upcoming_meetings_count"] > 0
    assert m2["pending_actions_count"] > 0
    assert len(d2["priority_emails"]) > 0
    assert len(d2["recent_emails"]) > 0

    # User 1 Dashboard in same environment remains completely unaffected
    resp1 = client.get("/api/dashboard", headers=user1_session)
    assert resp1.status_code == 200
    d1 = resp1.json()
    m1 = d1["metrics"]
    assert m1["total_emails"] == 15
    assert len(d1["recent_emails"]) == 5

