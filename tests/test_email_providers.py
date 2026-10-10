"""Comprehensive Tests for Email Provider Architecture (Stage 13).

Validates:
1. BaseEmailProvider abstract interface contracts.
2. MockEmailProvider offline, deterministic synthetic message retrieval and search.
3. GmailProvider credential validation, unauthenticated safety, and payload parsing.
4. EmailProviderManager automatic fallback to Mock when Gmail is unauthenticated.
5. Database synchronization idempotency and AI pipeline integration.
6. REST API endpoints (/api/email-provider/status and /api/email-provider/sync).
"""

import base64
import pytest
from datetime import datetime
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.app.config import settings
from backend.app.database.session import Base, get_db
from backend.app.models.email import Email
from backend.app.services.base_email_provider import BaseEmailProvider
from backend.app.services.mock_email_provider import MockEmailProvider
from backend.app.services.gmail_provider import GmailProvider
from backend.app.services.email_provider_manager import EmailProviderManager

client = TestClient(app)

# In-memory SQLite fixture for provider sync tests
@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# --------------------------------------------------------------------------
# 1. Base Provider Contract Tests
# --------------------------------------------------------------------------

def test_base_email_provider_cannot_be_instantiated():
    """Verify BaseEmailProvider is abstract and cannot be directly instantiated."""
    with pytest.raises(TypeError):
        BaseEmailProvider()

# --------------------------------------------------------------------------
# 2. Mock Email Provider Tests
# --------------------------------------------------------------------------

def test_mock_email_provider_defaults():
    """Test MockEmailProvider properties and default synthetic dataset."""
    provider = MockEmailProvider()
    assert provider.provider_name == "mock"
    assert provider.is_authenticated() is True

    messages = provider.get_messages(limit=10)
    assert len(messages) > 0
    assert len(messages) <= 10

    first = messages[0]
    assert "id" in first
    assert "sender" in first
    assert "recipient" in first
    assert "subject" in first
    assert "body" in first
    assert isinstance(first["received_at"], datetime)
    assert isinstance(first["is_read"], bool)

def test_mock_email_provider_search_filter():
    """Test query filtering in MockEmailProvider."""
    provider = MockEmailProvider()
    # Query for 'marks' or 'assessment' which exists in the seeded dataset
    results = provider.get_messages(query="marks")
    assert len(results) > 0
    for msg in results:
        text = (msg["subject"] + " " + msg["body"] + " " + msg["sender"]).lower()
        assert "marks" in text

    # Non-existent query
    empty_results = provider.get_messages(query="xyz999nonexistentquery")
    assert len(empty_results) == 0

def test_mock_email_provider_get_message_by_id():
    """Test retrieving single message by synthetic ID."""
    provider = MockEmailProvider()
    messages = provider.get_messages(limit=5)
    target_id = messages[0]["id"]

    found = provider.get_message_by_id(target_id)
    assert found is not None
    assert found["id"] == target_id

    # Non-existent ID returns None
    assert provider.get_message_by_id("invalid-id-000") is None

def test_mock_email_provider_add_message():
    """Test appending dynamic custom message to mock provider."""
    provider = MockEmailProvider(custom_messages=[])
    assert len(provider.get_messages()) == 0

    new_id = provider.add_message({
        "sender": "registrar@university.edu",
        "subject": "Senate Meeting Notice",
        "body": "The academic senate will convene tomorrow at 2 PM."
    })

    assert new_id.startswith("mock-msg-")
    messages = provider.get_messages()
    assert len(messages) == 1
    assert messages[0]["sender"] == "registrar@university.edu"

# --------------------------------------------------------------------------
# 3. Gmail Provider Tests
# --------------------------------------------------------------------------

def test_gmail_provider_unconfigured_safe_defaults():
    """Test GmailProvider is unauthenticated without credentials and does not crash."""
    provider = GmailProvider(
        client_id="",
        client_secret="",
        refresh_token="",
        credentials_path="",
        token_path=""
    )
    assert provider.provider_name == "gmail"
    assert provider.is_configured is False
    assert provider.is_authenticated() is False

    # Calling get_messages when unauthenticated must raise PermissionError
    with pytest.raises(PermissionError) as exc_info:
        provider.get_messages()
    assert "not authenticated" in str(exc_info.value)

    with pytest.raises(PermissionError):
        provider.get_message_by_id("msg_123")

def test_gmail_provider_parse_payload():
    """Test parsing of standard Gmail API REST JSON message payload."""
    provider = GmailProvider()

    raw_subject = "Urgent: Academic Council Agenda"
    raw_body_text = "Please find attached the minutes and agenda for upcoming Academic Council."
    encoded_body = base64.urlsafe_b64encode(raw_body_text.encode("utf-8")).decode("ascii")

    raw_message = {
        "id": "gmail_test_999",
        "internalDate": "1757152800000",
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "headers": [
                {"name": "Subject", "value": raw_subject},
                {"name": "From", "value": "council@university.edu"},
                {"name": "To", "value": "hod.cse@university.edu"},
                {"name": "Date", "value": "Sun, 06 Sep 2026 10:00:00 +0000"}
            ],
            "body": {
                "data": encoded_body
            }
        }
    }

    parsed = provider._parse_gmail_payload(raw_message)
    assert parsed["id"] == "gmail_test_999"
    assert parsed["subject"] == raw_subject
    assert parsed["sender"] == "council@university.edu"
    assert parsed["recipient"] == "hod.cse@university.edu"
    assert parsed["body"] == raw_body_text
    assert parsed["is_read"] is False

def test_gmail_provider_with_mocked_service():
    """Test GmailProvider message retrieval with injected mock API client."""
    mock_service = MagicMock()
    mock_messages_resource = MagicMock()
    mock_service.users.return_value.messages.return_value = mock_messages_resource

    # Mock list call
    mock_messages_resource.list.return_value.execute.return_value = {
        "messages": [{"id": "msg_001"}, {"id": "msg_002"}]
    }

    raw_body = base64.urlsafe_b64encode(b"Meeting agenda details").decode("ascii")
    mock_messages_resource.get.return_value.execute.return_value = {
        "id": "msg_001",
        "labelIds": ["INBOX"],
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test Gmail Subject"},
                {"name": "From", "value": "tester@gmail.com"},
                {"name": "To", "value": "faculty@university.edu"},
                {"name": "Date", "value": "Sun, 06 Sep 2026 12:00:00 +0000"}
            ],
            "body": {"data": raw_body}
        }
    }

    provider = GmailProvider(gmail_service=mock_service)
    assert provider.is_authenticated() is True

    messages = provider.get_messages(limit=2)
    assert len(messages) == 2
    assert messages[0]["subject"] == "Test Gmail Subject"
    assert messages[0]["body"] == "Meeting agenda details"
    assert messages[0]["is_read"] is True

# --------------------------------------------------------------------------
# 4. Email Provider Manager Tests
# --------------------------------------------------------------------------

def test_provider_manager_default_resolution():
    """Verify manager provides MockEmailProvider by default."""
    manager = EmailProviderManager(default_provider_name="mock")
    provider = manager.get_provider()
    assert isinstance(provider, MockEmailProvider)
    assert provider.provider_name == "mock"

def test_provider_manager_fallback_when_gmail_unauthenticated():
    """Verify manager gracefully falls back to MockEmailProvider when Gmail is unauthenticated."""
    manager = EmailProviderManager(default_provider_name="gmail")
    # Even though default is 'gmail', because credentials are empty it must fallback
    provider = manager.get_provider()
    assert isinstance(provider, MockEmailProvider)
    assert provider.provider_name == "mock"

    status = manager.get_status()
    # If settings.EMAIL_PROVIDER is "mock", test explicit gmail override
    manager_explicit = EmailProviderManager()
    provider_explicit = manager_explicit.get_provider(provider_type="gmail")
    assert isinstance(provider_explicit, MockEmailProvider)

def test_provider_manager_get_status():
    """Verify telemetry dictionary structure."""
    manager = EmailProviderManager()
    status = manager.get_status()
    assert "configured_provider" in status
    assert "active_provider" in status
    assert "is_authenticated" in status
    assert "available_providers" in status
    assert "fallback_active" in status
    assert "gmail_configured" in status
    assert "gmail_authenticated" in status
    assert "mock" in status["available_providers"]
    assert "gmail" in status["available_providers"]

def test_provider_manager_sync_emails_idempotency(test_db):
    """Verify sync_emails imports new records and skips duplicates."""
    manager = EmailProviderManager()

    # Initial sync with small limit
    res1 = manager.sync_emails(db=test_db, limit=3, run_ai_pipeline=False)
    assert res1["status"] == "success"
    assert res1["imported"] == 3
    assert res1["skipped"] == 0
    assert test_db.query(Email).count() == 3

    # Second sync with same dataset must skip all 3
    res2 = manager.sync_emails(db=test_db, limit=3, run_ai_pipeline=False)
    assert res2["status"] == "success"
    assert res2["imported"] == 0
    assert res2["skipped"] == 3
    assert test_db.query(Email).count() == 3

# --------------------------------------------------------------------------
# 5. REST API Integration Tests
# --------------------------------------------------------------------------

def test_api_email_provider_status_endpoint():
    """Verify GET /api/email-provider/status returns valid architecture status."""
    res = client.get("/api/email-provider/status")
    assert res.status_code == 200
    data = res.json()
    assert "configured_provider" in data
    assert "active_provider" in data
    assert "available_providers" in data
    assert data["is_authenticated"] is True  # Mock provider is authenticated

def test_api_email_provider_sync_endpoint():
    """Verify POST /api/email-provider/sync triggers ingestion."""
    res = client.post("/api/email-provider/sync?limit=2")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "data" in data
    assert "fetched" in data["data"]
    assert "imported" in data["data"]
    assert "skipped" in data["data"]

def test_api_health_includes_email_provider():
    """Verify /api/health endpoint includes email_provider telemetry."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert "email_provider" in data
    assert data["email_provider"] in ["mock", "gmail"]
