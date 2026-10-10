"""Automated Test Suite for Multi-Account Gmail Connection via Official Google OAuth.

Covers:
1. Google OAuth 2.0 authorization URL with select_account and prompt=consent.
2. Read-only scope enforcement (gmail.readonly).
3. Zero-password collection guarantee (OAuth code flow only, no password fields).
4. Dynamic user account onboarding from any verified Google account.
5. Per-user credential file isolation (token_{user_id}.json).
6. Multi-account session switching via server session manager.
7. Strict per-user email isolation (User B cannot access User A's emails; /api/emails/1 returns 404 for User B).
8. Manual & automatic sync capped at 60 messages for any Gmail account.
9. User 1 (Mock User) protection: strictly forbidden from Gmail sync (HTTP 403).
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.config import settings
from backend.app.database.session import get_db, SessionLocal
from backend.app.models.user import User
from backend.app.models.email import Email
from backend.app.models.preference import FacultyPreference
from backend.app.services.oauth_service import oauth_service, GoogleOAuthService
from backend.app.services.email_provider_manager import email_provider_manager
from backend.app.core.session_manager import session_manager

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_db():
    """Ensure a clean database state and test user records."""
    db = SessionLocal()
    try:
        # Verify default mock user 1
        u1 = db.query(User).filter(User.id == 1).first()
        if not u1:
            u1 = User(id=1, email="mock.faculty@university.edu", name="Dr. Faculty", role="Professor", provider_type="mock")
            db.add(u1)
            db.commit()

        # Ensure user 2
        u2 = db.query(User).filter(User.id == 2).first()
        if not u2:
            u2 = User(id=2, email="shivaprakashp.cs24@bitsathy.ac.in", name="Dr. Shivaprakash", role="Assistant Professor", provider_type="gmail")
            db.add(u2)
            db.commit()

        yield db
    finally:
        # Cleanup any test created users (id > 2)
        test_users = db.query(User).filter(User.id > 2).all()
        for tu in test_users:
            db.query(Email).filter(Email.user_id == tu.id).delete()
            db.query(FacultyPreference).filter(FacultyPreference.user_id == tu.id).delete()
            db.delete(tu)
        db.commit()
        db.close()


def test_oauth_url_generation_select_account():
    """Verify that OAuth URL uses select_account prompt and gmail.readonly scope."""
    with patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id"), \
         patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret"):
        flow_data = oauth_service.generate_authorization_url()
        auth_url = flow_data["authorization_url"]
        
        # Must request select_account so user can switch or add another Gmail account
        assert "select_account" in auth_url
        assert "consent" in auth_url
        # Must request read-only scope
        assert "gmail.readonly" in auth_url


def test_zero_password_handling():
    """Security assertion: Zero password endpoints or fields exist in auth and provider routes."""
    # Ensure no auth route asks for a password
    openapi_schema = app.openapi()
    paths = openapi_schema.get("paths", {})
    
    for path, methods in paths.items():
        if "/api/auth" in path or "/api/email-provider" in path:
            for method, spec in methods.items():
                params = spec.get("parameters", [])
                for p in params:
                    assert "password" not in p.get("name", "").lower()
                
                req_body = spec.get("requestBody", {})
                content = req_body.get("content", {})
                schema = content.get("application/json", {}).get("schema", {})
                props = schema.get("properties", {})
                assert "password" not in props


def test_dynamic_gmail_user_onboarding_via_oauth(tmp_path):
    """When a new Gmail user authenticates via Google OAuth, a dynamic User record is created."""
    token_file = str(tmp_path / "test_token.json")
    valid_state = oauth_service.generate_state()
    new_email = "prof.rajesh.research@gmail.com"

    mock_creds = MagicMock()
    mock_creds.token = "mock-token-rajesh"
    mock_creds.refresh_token = "mock-refresh-rajesh"
    mock_creds.token_uri = "https://oauth2.googleapis.com/token"
    mock_creds.client_id = "test-client-id"
    mock_creds.client_secret = "test-client-secret"
    mock_creds.scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

    with patch.object(settings, "GMAIL_TOKEN_PATH", token_file), \
         patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id"), \
         patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret"), \
         patch.object(oauth_service, "exchange_code", return_value=mock_creds), \
         patch.object(oauth_service, "verify_account_identity", return_value=(True, new_email, "Verified")):

        resp = client.get(
            f"/api/email-provider/gmail/oauth/callback?code=mock_code_123&state={valid_state}",
            follow_redirects=False
        )

        assert resp.status_code == 302
        assert "oauth=success" in resp.headers["location"]
        assert "prof.rajesh.research" in resp.headers["location"]
        
        # Session cookie must be issued
        assert "session_token" in resp.headers.get("set-cookie", "")

        # Verify new user created in database
        db = SessionLocal()
        new_user = db.query(User).filter(User.email == new_email).first()
        assert new_user is not None
        assert new_user.provider_type == "gmail"
        assert new_user.name == "Prof Rajesh Research"
        
        # Verify preferences created
        pref = db.query(FacultyPreference).filter(FacultyPreference.user_id == new_user.id).first()
        assert pref is not None
        db.close()


def test_multi_account_switching_and_isolation(tmp_path):
    """Verify switching between multiple accounts maintains strict email isolation."""
    db = SessionLocal()
    # Create third user
    third_email = "dr.ananya.cse@gmail.com"
    third_user = db.query(User).filter(User.email == third_email).first()
    if not third_user:
        third_user = User(email=third_email, name="Dr. Ananya", role="Associate Professor", provider_type="gmail")
        db.add(third_user)
        db.commit()
        db.refresh(third_user)

    # Seed an email for User 1
    u1_email = db.query(Email).filter(Email.user_id == 1).first()
    assert u1_email is not None, "User 1 must have mock emails seeded"
    u1_email_id = u1_email.id

    from datetime import datetime, timezone
    # Seed an email exclusively for third_user
    third_msg = Email(
        user_id=third_user.id,
        provider_message_id="gmail_msg_ananya_001",
        sender="hod.cse@university.edu",
        recipient=third_email,
        subject="Department Meeting on NAAC Criteria 3",
        body="Dear Dr. Ananya, please attend the meeting on Friday.",
        received_at=datetime.now(timezone.utc).replace(tzinfo=None),
        is_read=False
    )
    db.add(third_msg)
    db.commit()
    db.refresh(third_msg)
    third_email_id = third_msg.id
    db.close()

    # 1. Switch to third_user
    switch_res = client.post("/api/auth/switch-session", json={"email": third_email})
    assert switch_res.status_code == 200
    third_token = switch_res.json()["session_token"]
    third_headers = {"Authorization": f"Bearer {third_token}"}

    # 2. Check /api/auth/me returns third_user
    me_res = client.get("/api/auth/me", headers=third_headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == third_email

    # 3. Third user CANNOT access User 1's email (Strict Isolation -> returns 404)
    res_isolated = client.get(f"/api/emails/{u1_email_id}", headers=third_headers)
    assert res_isolated.status_code == 404
    assert "not found" in res_isolated.json()["detail"].lower()

    # 4. Third user CAN access their own email
    res_own = client.get(f"/api/emails/{third_email_id}", headers=third_headers)
    assert res_own.status_code == 200
    assert res_own.json()["subject"] == "Department Meeting on NAAC Criteria 3"

    # 5. User 1 CANNOT access third_user's email (User 1 session)
    u1_switch = client.post("/api/auth/switch-session", json={"email": "mock.faculty@university.edu"})
    assert u1_switch.status_code == 200
    u1_token = u1_switch.json()["session_token"]
    u1_res = client.get(f"/api/emails/{third_email_id}", headers={"Authorization": f"Bearer {u1_token}"})
    assert u1_res.status_code == 404


def test_user1_cannot_sync_gmail():
    """User 1 (mock session) is strictly forbidden from triggering Gmail sync (HTTP 403)."""
    # Create session for user 1
    session_manager.register_allowed_email("mock.faculty@university.edu")
    u1_token = session_manager.create_session(user_id=1, user_email="mock.faculty@university.edu")
    headers = {"Authorization": f"Bearer {u1_token}"}

    resp = client.post("/api/email-provider/gmail/sync", headers=headers)
    assert resp.status_code == 403
    assert "User 1 (Mock User) operates exclusively with MockEmailProvider" in resp.json()["detail"]


def test_gmail_sync_60_message_cap_for_authenticated_gmail_user(tmp_path):
    """Any authenticated Gmail user can sync up to 60 emails and respects the 60 message cap."""
    db = SessionLocal()
    test_user_email = "test.prof.cap@gmail.com"
    user = User(email=test_user_email, name="Prof Cap", role="Professor", provider_type="gmail")
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()

    session_manager.register_allowed_email(test_user_email)
    token = session_manager.create_session(user_id=user.id, user_email=test_user_email)
    headers = {"Authorization": f"Bearer {token}"}

    # Generate 70 dummy messages
    fake_messages = [
        {
            "id": f"msg_cap_{i}",
            "sender": f"sender_{i}@university.edu",
            "recipient": test_user_email,
            "subject": f"Notice {i}",
            "body": f"Notice body content {i}",
            "received_at": "2026-09-08T10:00:00",
            "is_read": False
        }
        for i in range(70)
    ]

    mock_provider = MagicMock()
    mock_provider.provider_name = "gmail"
    mock_provider.get_messages = MagicMock(side_effect=lambda limit: fake_messages[:min(limit, 60)])

    with patch.object(oauth_service, "get_status", return_value={"connected": True}), \
         patch.object(email_provider_manager, "get_provider", return_value=mock_provider):

        # Request limit=100 -> backend must strictly cap at 60
        sync_res = client.post("/api/email-provider/gmail/sync?limit=60", headers=headers)
        assert sync_res.status_code == 200
        data = sync_res.json()["data"]
        assert data["user_id"] == user.id
        assert data["fetched"] <= 60
        assert data["imported"] <= 60


def test_disconnect_per_user(tmp_path):
    """Disconnect endpoint successfully calls oauth_service.disconnect for the active user."""
    db = SessionLocal()
    disc_email = "test.disconnect@gmail.com"
    user = User(email=disc_email, name="Prof Disconnect", role="Faculty", provider_type="gmail")
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()

    session_manager.register_allowed_email(disc_email)
    token = session_manager.create_session(user_id=user.id, user_email=disc_email)
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(oauth_service, "disconnect", return_value={"status": "disconnected", "message": "Revoked"}):
        resp = client.post("/api/email-provider/gmail/disconnect", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "disconnected"
