"""Tests for Stage 19A — Google OAuth 2.0 and College Gmail Account Connection.

Validates:
1. System starts and functions in mock mode without Google credentials.
2. Authorization URL generation with read-only scope and CSRF state.
3. CSRF state validation (single-use, expiration, invalid token rejection).
4. Strict college account verification (shivaprakashp.cs24@bitsathy.ac.in, case-insensitive).
5. Unauthorized accounts rejected safely without storing credentials.
6. Safe status endpoint without secret or token leakage.
7. Disconnection and token revocation flow.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.config import settings
from backend.app.services.oauth_service import oauth_service, GoogleOAuthService
from backend.app.services.gmail_provider import GmailProvider
from backend.app.services.mock_email_provider import MockEmailProvider

client = TestClient(app)

TEST_COLLEGE_EMAIL = "shivaprakashp.cs24@bitsathy.ac.in"

# -----------------------------------------------------------------------------
# 1. Startup & Mock Isolation Tests
# -----------------------------------------------------------------------------

def test_system_starts_without_google_credentials():
    """Verify application health and unauthenticated safety when credentials are absent."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["email_provider"] == "mock"

def test_mock_provider_remains_active_and_functional():
    """Verify MockEmailProvider is unaffected by Stage 19A additions."""
    provider = MockEmailProvider()
    assert provider.is_authenticated() is True
    assert provider.provider_name == "mock"
    messages = provider.get_messages(limit=5)
    assert len(messages) > 0

# -----------------------------------------------------------------------------
# 2. Authorization URL & CSRF State Tests
# -----------------------------------------------------------------------------

def test_connect_endpoint_unconfigured_error():
    """When GOOGLE_CLIENT_ID is not configured, connect endpoint returns clean 400 error."""
    with patch.object(settings, "GOOGLE_CLIENT_ID", ""), \
         patch.object(settings, "GMAIL_CLIENT_ID", ""):
        resp = client.get("/api/email-provider/gmail/connect")
        assert resp.status_code == 400
        assert "Google OAuth credentials not configured" in resp.json()["detail"]

def test_oauth_state_generation_and_validation():
    """Verify CSRF state is random, validates once (single-use), and rejects invalid tokens."""
    service = GoogleOAuthService()
    state = service.generate_state()
    assert isinstance(state, str)
    assert len(state) >= 32

    # First validation succeeds (consuming state)
    assert service.validate_state(state) is True

    # Second validation fails (single-use protection)
    assert service.validate_state(state) is False

    # Invalid state fails
    assert service.validate_state("non_existent_state") is False
    assert service.validate_state("") is False
    assert service.validate_state(None) is False

def test_connect_endpoint_generates_valid_oauth_url():
    """When configured, /api/email-provider/gmail/connect returns valid authorization URL."""
    with patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id-123.apps.googleusercontent.com"), \
         patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret-456"):
        resp = client.get("/api/email-provider/gmail/connect")
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "success"
        assert "authorization_url" in data
        assert "state" in data
        assert data["target_account"] == TEST_COLLEGE_EMAIL
        assert data["scope"] == "https://www.googleapis.com/auth/gmail.readonly"

        auth_url = data["authorization_url"]
        assert "accounts.google.com" in auth_url
        assert "test-client-id-123" in auth_url
        assert "https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.readonly" in auth_url

# -----------------------------------------------------------------------------
# 3. Callback Error & Account Verification Tests
# -----------------------------------------------------------------------------

def test_callback_user_denied_redirects_with_error():
    """If user denies OAuth consent on Google, callback redirects cleanly to settings."""
    resp = client.get(
        "/api/email-provider/gmail/oauth/callback?error=access_denied",
        follow_redirects=False
    )
    assert resp.status_code == 302
    assert "oauth=error" in resp.headers["location"]
    assert "reason=access_denied" in resp.headers["location"]

def test_callback_missing_parameters_rejected():
    """Callback without code or state raises HTTP 400."""
    resp = client.get("/api/email-provider/gmail/oauth/callback")
    assert resp.status_code == 400
    assert "Missing authorization code or state" in resp.json()["detail"]

def test_callback_invalid_state_rejected():
    """Callback with forged or expired state raises HTTP 400."""
    resp = client.get("/api/email-provider/gmail/oauth/callback?code=mock_code&state=fake_state")
    assert resp.status_code == 400
    assert "Invalid or expired OAuth state" in resp.json()["detail"]

def test_callback_successful_college_account_verification(tmp_path):
    """When authenticated account matches shivaprakashp.cs24@bitsathy.ac.in, connection succeeds."""
    token_file = str(tmp_path / "test_gmail_token.json")
    valid_state = oauth_service.generate_state()

    mock_creds = MagicMock()
    mock_creds.token = "mock-access-token"
    mock_creds.refresh_token = "mock-refresh-token"
    mock_creds.token_uri = "https://oauth2.googleapis.com/token"
    mock_creds.client_id = "test-client-id"
    mock_creds.client_secret = "test-client-secret"
    mock_creds.scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

    with patch.object(settings, "GMAIL_TOKEN_PATH", token_file), \
         patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id"), \
         patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret"), \
         patch.object(oauth_service, "exchange_code", return_value=mock_creds), \
         patch.object(oauth_service, "verify_account_identity", return_value=(True, TEST_COLLEGE_EMAIL, "Verified")):

        resp = client.get(
            f"/api/email-provider/gmail/oauth/callback?code=mock_valid_code&state={valid_state}",
            follow_redirects=False
        )

        assert resp.status_code == 302
        assert "oauth=success" in resp.headers["location"]
        assert "shivaprakashp.cs24" in resp.headers["location"]

        # Credentials must be saved to token file
        assert os.path.exists(token_file)
        with open(token_file, "r") as f:
            saved_data = json.load(f)
            assert saved_data["account_email"] == TEST_COLLEGE_EMAIL
            assert saved_data["refresh_token"] == "mock-refresh-token"

def test_callback_case_insensitive_matching(tmp_path):
    """Verify that case variations like SHIVAPRAKASHP.CS24@BITSATHY.AC.IN are accepted."""
    service = GoogleOAuthService()
    mock_creds = MagicMock()

    with patch("googleapiclient.discovery.build") as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.users().getProfile().execute.return_value = {
            "emailAddress": "SHIVAPRAKASHP.CS24@BITSATHY.AC.IN"
        }

        is_match, email, msg = service.verify_account_identity(mock_creds)
        assert is_match is True
        assert email == TEST_COLLEGE_EMAIL

def test_callback_rejects_wrong_account(tmp_path):
    """When a different Google account is authenticated, connection is rejected and credentials discarded."""
    token_file = str(tmp_path / "should_not_exist_token.json")
    valid_state = oauth_service.generate_state()

    mock_creds = MagicMock()

    with patch.object(settings, "GMAIL_TOKEN_PATH", token_file), \
         patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id"), \
         patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret"), \
         patch.object(oauth_service, "exchange_code", return_value=mock_creds), \
         patch.object(oauth_service, "verify_account_identity", return_value=(False, "unauthorized.user@gmail.com", "Mismatch")):

        resp = client.get(
            f"/api/email-provider/gmail/oauth/callback?code=mock_code&state={valid_state}",
            follow_redirects=False
        )

        assert resp.status_code == 302
        assert "oauth=error" in resp.headers["location"]
        assert "reason=wrong_account" in resp.headers["location"]

        # Credentials MUST NOT be saved
        assert not os.path.exists(token_file)

# -----------------------------------------------------------------------------
# 4. Telemetry & Disconnect Tests
# -----------------------------------------------------------------------------

def test_status_endpoint_never_exposes_secrets():
    """Verify status response returns connection telemetry without leaking secrets or tokens."""
    resp = client.get("/api/email-provider/gmail/status")
    assert resp.status_code == 200
    data = resp.json()

    # Required safe fields
    assert "connected" in data
    assert "provider" in data
    assert data["provider"] == "gmail"
    assert "scope" in data
    assert "configured" in data
    assert "college_account" in data

    # STRICT SECURITY ASSERTIONS: Secrets and verifiers must NEVER appear in response
    forbidden_keys = [
        "client_secret",
        "access_token",
        "refresh_token",
        "authorization_code",
        "code",
        "token",
        "code_verifier",
        "verifier"
    ]
    for key in forbidden_keys:
        assert key not in data, f"Security violation: '{key}' exposed in status response!"

def test_disconnect_flow(tmp_path):
    """Verify /api/email-provider/gmail/disconnect clears credentials and resets state."""
    token_file = str(tmp_path / "dummy_token.json")
    with open(token_file, "w") as f:
        json.dump({"account_email": TEST_COLLEGE_EMAIL, "token": "abc"}, f)

    assert os.path.exists(token_file)

    with patch.object(settings, "GMAIL_TOKEN_PATH", token_file):
        resp = client.post("/api/email-provider/gmail/disconnect")
        assert resp.status_code == 200
        assert resp.json()["status"] == "disconnected"
        assert not os.path.exists(token_file)

# -----------------------------------------------------------------------------
# 5. PKCE Code Verifier & Security Tests (Stage 19A Bug Fix)
# -----------------------------------------------------------------------------

def test_authorization_generates_and_stores_pkce_verifier():
    """Verify authorization generates PKCE challenge, stores verifier internally, and protects response."""
    with patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com"), \
         patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret"):
        resp = client.get("/api/email-provider/gmail/connect")
        assert resp.status_code == 200
        data = resp.json()

        # URL contains PKCE challenge parameters
        auth_url = data["authorization_url"]
        assert "code_challenge=" in auth_url
        assert "code_challenge_method=S256" in auth_url

        state = data["state"]
        # Code verifier must be stored internally for this state
        assert state in oauth_service._active_states
        stored_verifier = oauth_service._active_states[state]["code_verifier"]
        assert stored_verifier is not None
        assert len(stored_verifier) >= 43

        # Code verifier must NEVER be exposed in the API response
        assert "code_verifier" not in data
        assert stored_verifier not in json.dumps(data)

def test_callback_retrieves_matching_pkce_verifier(tmp_path):
    """Verify callback retrieves the exact PKCE code_verifier generated during connect."""
    state_file = str(tmp_path / ".test_pkce_states.json")
    service = GoogleOAuthService(persistence_file=state_file)

    with patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com"), \
         patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret"):
        res = service.generate_authorization_url()
        state = res["state"]

        # Validate state (simulating callback step 1)
        assert service.validate_state(state) is True

        # Retrieve matching verifier (simulating callback step 2)
        verifier = service.get_and_consume_verifier(state)
        assert verifier is not None
        assert len(verifier) >= 43

def test_token_exchange_supplies_correct_verifier(tmp_path):
    """Verify exchange_code retrieves stored verifier and sets flow.code_verifier."""
    state_file = str(tmp_path / ".test_pkce_states.json")
    service = GoogleOAuthService(persistence_file=state_file)

    state = service.generate_state()
    test_verifier = "test-pkce-verifier-string-at-least-43-chars-long-123456789"
    service.store_code_verifier(state, test_verifier)

    # Validate state (moves to pending)
    assert service.validate_state(state) is True

    with patch("google_auth_oauthlib.flow.Flow.from_client_config") as mock_flow_factory:
        mock_flow = MagicMock()
        mock_flow.credentials = MagicMock()
        mock_flow_factory.return_value = mock_flow

        creds = service.exchange_code(code="auth_code_123", state=state)

        # Flow must have received the exact matching PKCE code_verifier
        assert mock_flow.code_verifier == test_verifier
        mock_flow.fetch_token.assert_called_once_with(code="auth_code_123")
        assert creds == mock_flow.credentials

def test_state_and_verifier_cannot_be_reused(tmp_path):
    """Verify state and verifier cannot be replayed or reused."""
    state_file = str(tmp_path / ".test_pkce_states.json")
    service = GoogleOAuthService(persistence_file=state_file)

    state = service.generate_state()
    service.store_code_verifier(state, "unique_verifier_xyz_123456789012345678901234567890")

    # 1. First state validation succeeds
    assert service.validate_state(state) is True

    # 2. Second state validation FAILS (anti-replay)
    assert service.validate_state(state) is False

    # 3. First verifier consumption succeeds
    v1 = service.get_and_consume_verifier(state)
    assert v1 == "unique_verifier_xyz_123456789012345678901234567890"

    # 4. Second verifier consumption FAILS (cannot be consumed twice)
    v2 = service.get_and_consume_verifier(state)
    assert v2 is None

def test_pkce_verifier_persistence_across_restarts(tmp_path):
    """Verify PKCE state survives simulated server restarts."""
    state_file = str(tmp_path / ".test_pkce_states.json")
    service1 = GoogleOAuthService(persistence_file=state_file)

    state = service1.generate_state()
    expected_verifier = "persistent_verifier_abc_123456789012345678901234567890"
    service1.store_code_verifier(state, expected_verifier)

    # Simulate restart by creating new service instance reading the same file
    service2 = GoogleOAuthService(persistence_file=state_file)
    assert service2.validate_state(state) is True
    assert service2.get_and_consume_verifier(state) == expected_verifier

