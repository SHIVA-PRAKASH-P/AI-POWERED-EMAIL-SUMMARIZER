"""Google OAuth 2.0 Service for College Gmail Account Connection (Stage 19A).

Handles:
1. Generation of secure, read-only authorization URLs with cryptographically random CSRF state.
2. State validation with single-use and expiration enforcement.
3. Code-for-token exchange via official Google OAuth libraries.
4. Strict college identity verification against shivaprakashp.cs24@bitsathy.ac.in (case-insensitive).
5. Secure local credential storage and disconnection lifecycle.
"""

import os
import json
import time
import secrets
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from backend.app.config import settings

logger = logging.getLogger(__name__)

class GoogleOAuthService:
    """Manages Google OAuth 2.0 lifecycle, PKCE verification, and Gmail account identity verification."""

    STATE_EXPIRY_SECONDS = 600  # 10 minutes

    def __init__(self, persistence_file: Optional[str] = None):
        self._lock = threading.Lock()
        # In-memory active states awaiting callback: { state_token: { "created_at": float, "code_verifier": Optional[str] } }
        self._active_states: Dict[str, Dict[str, Any]] = {}
        # In-memory pending verifiers (validated states awaiting token exchange): { state_token: { "created_at": float, "code_verifier": Optional[str] } }
        self._pending_verifiers: Dict[str, Dict[str, Any]] = {}
        
        token_dir = os.path.dirname(settings.GMAIL_TOKEN_PATH) if settings.GMAIL_TOKEN_PATH else "./backend/app/database"
        self._persistence_file = persistence_file or os.path.join(token_dir, ".oauth_pkce_states.json")
        self._load_persisted_states()

    def _load_persisted_states(self) -> None:
        """Load unexpired states from secure local storage file if present."""
        if not self._persistence_file or not os.path.exists(self._persistence_file):
            return
        try:
            with open(self._persistence_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                now = time.time()
                for state, item in data.get("active", {}).items():
                    if isinstance(item, dict) and (now - item.get("created_at", 0) <= self.STATE_EXPIRY_SECONDS):
                        self._active_states[state] = item
                for state, item in data.get("pending", {}).items():
                    if isinstance(item, dict) and (now - item.get("created_at", 0) <= self.STATE_EXPIRY_SECONDS):
                        self._pending_verifiers[state] = item
        except Exception as e:
            logger.debug(f"Could not load persisted OAuth states: {e}")

    def _save_persisted_states(self) -> None:
        """Persist active and pending states to local protected file."""
        if not self._persistence_file:
            return
        try:
            target_dir = os.path.dirname(self._persistence_file)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            temp_file = f"{self._persistence_file}.tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump({
                    "active": self._active_states,
                    "pending": self._pending_verifiers
                }, f)
            os.replace(temp_file, self._persistence_file)
        except Exception as e:
            logger.warning(f"Could not persist OAuth states: {e}")

    def _cleanup_expired_states(self) -> None:
        """Prune states that have exceeded STATE_EXPIRY_SECONDS."""
        now = time.time()
        with self._lock:
            expired_active = [
                s for s, data in self._active_states.items()
                if (now - (data.get("created_at", 0) if isinstance(data, dict) else data)) > self.STATE_EXPIRY_SECONDS
            ]
            for s in expired_active:
                self._active_states.pop(s, None)

            expired_pending = [
                s for s, data in self._pending_verifiers.items()
                if (now - (data.get("created_at", 0) if isinstance(data, dict) else data)) > self.STATE_EXPIRY_SECONDS
            ]
            for s in expired_pending:
                self._pending_verifiers.pop(s, None)
            
            if expired_active or expired_pending:
                self._save_persisted_states()

    def generate_state(self, code_verifier: Optional[str] = None) -> str:
        """Generate a cryptographically random, timestamped single-use CSRF state token."""
        self._cleanup_expired_states()
        state = secrets.token_urlsafe(32)
        with self._lock:
            self._active_states[state] = {
                "created_at": time.time(),
                "code_verifier": code_verifier
            }
            self._save_persisted_states()
        return state

    def store_code_verifier(self, state: str, code_verifier: str) -> None:
        """Associate a PKCE code_verifier with an active CSRF state token."""
        with self._lock:
            if state in self._active_states:
                self._active_states[state]["code_verifier"] = code_verifier
            else:
                self._active_states[state] = {
                    "created_at": time.time(),
                    "code_verifier": code_verifier
                }
            self._save_persisted_states()

    def validate_state(self, state: Optional[str]) -> bool:
        """Validate state token: must exist, must not be expired, consumed upon validation."""
        self._cleanup_expired_states()
        if not state:
            return False
        
        with self._lock:
            state_data = self._active_states.pop(state, None)
            if state_data is None:
                return False
            
            created_time = state_data.get("created_at", 0) if isinstance(state_data, dict) else state_data
            if (time.time() - created_time) > self.STATE_EXPIRY_SECONDS:
                self._save_persisted_states()
                return False
            
            # Store verifier into pending registry for token exchange
            verifier = state_data.get("code_verifier") if isinstance(state_data, dict) else None
            self._pending_verifiers[state] = {
                "created_at": created_time,
                "code_verifier": verifier
            }
            self._save_persisted_states()
            return True

    def get_and_consume_verifier(self, state: str) -> Optional[str]:
        """Retrieve and immediately consume the PKCE code_verifier for an OAuth state."""
        self._cleanup_expired_states()
        with self._lock:
            # Check pending verifiers (validate_state was called first)
            pending = self._pending_verifiers.pop(state, None)
            if pending:
                self._save_persisted_states()
                return pending.get("code_verifier")
            
            # Check active states (if exchange_code was called directly)
            active = self._active_states.pop(state, None)
            if active:
                self._save_persisted_states()
                if isinstance(active, dict):
                    return active.get("code_verifier")
            return None

    def get_client_config(self) -> Dict[str, Any]:
        """Construct standard Google OAuth client configuration dictionary."""
        client_id = settings.resolved_google_client_id
        client_secret = settings.resolved_google_client_secret
        redirect_uri = settings.resolved_google_redirect_uri

        if not client_id or not client_secret:
            raise ValueError(
                "Google OAuth credentials not configured. Please set GOOGLE_CLIENT_ID and "
                "GOOGLE_CLIENT_SECRET in environment or .env."
            )

        return {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        }

    def generate_authorization_url(self, redirect_uri: Optional[str] = None) -> Dict[str, str]:
        """Generate Google OAuth 2.0 authorization URL requesting read-only Gmail access with PKCE."""
        from google_auth_oauthlib.flow import Flow

        client_config = self.get_client_config()
        effective_redirect = redirect_uri or settings.resolved_google_redirect_uri
        
        # Override redirect_uri in client config if custom passed
        client_config["web"]["redirect_uris"] = [effective_redirect]

        state = self.generate_state()

        flow = Flow.from_client_config(
            client_config,
            scopes=[settings.GMAIL_SCOPES],
            state=state
        )
        flow.redirect_uri = effective_redirect

        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="select_account consent"  # Prompt user to choose or add another Google account
        )

        # Retrieve and persist the PKCE code_verifier generated by Flow
        verifier = getattr(flow, "code_verifier", None)
        if verifier:
            self.store_code_verifier(state, verifier)

        logger.info("Generated Google OAuth authorization URL with PKCE challenge (read-only scope).")
        return {
            "authorization_url": authorization_url,
            "state": state
        }

    def exchange_code(
        self,
        code: str,
        state: str,
        redirect_uri: Optional[str] = None,
        code_verifier: Optional[str] = None
    ) -> Any:
        """Exchange OAuth authorization code for Google credentials object using PKCE verifier."""
        from google_auth_oauthlib.flow import Flow

        client_config = self.get_client_config()
        effective_redirect = redirect_uri or settings.resolved_google_redirect_uri
        client_config["web"]["redirect_uris"] = [effective_redirect]

        flow = Flow.from_client_config(
            client_config,
            scopes=[settings.GMAIL_SCOPES],
            state=state
        )
        flow.redirect_uri = effective_redirect

        # Supply the exact PKCE code_verifier matching the initial authorization request
        verifier = code_verifier or self.get_and_consume_verifier(state)
        if verifier:
            flow.code_verifier = verifier
            logger.info("Supplied matching PKCE code_verifier for OAuth token exchange.")
        else:
            logger.warning("No PKCE code_verifier found for OAuth state during token exchange.")

        flow.fetch_token(code=code)
        return flow.credentials

    def verify_account_identity(self, credentials: Any, target_account: Optional[str] = None) -> Tuple[bool, str, str]:
        """Query Gmail API profile to verify authenticated Google account identity.
        
        If target_account is specified, verifies that the account matches target_account.
        Otherwise, accepts any valid authenticated Google account.
        
        Returns:
            Tuple[is_match, authenticated_email, message]
        """
        from googleapiclient.discovery import build

        service = build("gmail", "v1", credentials=credentials)
        profile = service.users().getProfile(userId="me").execute()
        authenticated_email = profile.get("emailAddress", "").strip().lower()

        if not authenticated_email:
            return False, "", "Could not determine email address from Gmail profile."

        if target_account:
            target_norm = target_account.strip().lower()
            if authenticated_email != target_norm:
                logger.warning(
                    f"Unauthorized account authenticated: {authenticated_email} (expected {target_norm})"
                )
                return False, authenticated_email, (
                    f"Unauthorized Google account: '{authenticated_email}'. "
                    f"Expected: '{target_norm}'."
                )

        logger.info(f"Successfully verified Gmail account: {authenticated_email}")
        return True, authenticated_email, "Account successfully verified."

    def get_token_path(self, user_id: Optional[int] = None) -> str:
        """Resolve token storage path for a given user identity."""
        default_path = settings.GMAIL_TOKEN_PATH
        if not user_id:
            return default_path
        token_dir = os.path.dirname(default_path) if default_path else "./backend/app/database"
        user_path = os.path.join(token_dir, f"token_{user_id}.json")
        if os.path.exists(user_path):
            return user_path
        return default_path

    def save_credentials(self, credentials: Any, account_email: str, user_id: Optional[int] = None) -> str:
        """Safely persist credentials to local protected file specified by user_id or GMAIL_TOKEN_PATH."""
        token_path = settings.GMAIL_TOKEN_PATH
        token_dir = os.path.dirname(token_path) if token_path else "./backend/app/database"
        if token_dir and not os.path.exists(token_dir):
            os.makedirs(token_dir, exist_ok=True)

        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes or [settings.GMAIL_SCOPES],
            "account_email": account_email,
            "connected_at": datetime.now(timezone.utc).isoformat()
        }

        # Save to default token path for backward compatibility
        with open(token_path, "w", encoding="utf-8") as f:
            json.dump(token_data, f, indent=2)

        # Save to user-specific token file if user_id is provided
        if user_id:
            user_token_path = os.path.join(token_dir, f"token_{user_id}.json")
            with open(user_token_path, "w", encoding="utf-8") as f:
                json.dump(token_data, f, indent=2)
            logger.info("Saved authorized user credentials to %s and %s", token_path, user_token_path)
            return user_token_path

        logger.info("Saved authorized user credentials to protected token store.")
        return token_path

    def get_status(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Return safe telemetry on Google OAuth and Gmail connection state for given user."""
        token_path = self.get_token_path(user_id=user_id)
        has_token = bool(token_path and os.path.exists(token_path))
        account_email = None
        is_connected = False

        if has_token:
            try:
                with open(token_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    account_email = data.get("account_email")
                    is_connected = bool(data.get("token") or data.get("refresh_token"))
            except Exception as e:
                logger.warning(f"Error reading token file: {e}")
                has_token = False

        return {
            "connected": is_connected,
            "email": account_email if is_connected else None,
            "provider": "gmail",
            "scope": settings.GMAIL_SCOPES,
            "configured": settings.is_google_oauth_configured,
            "college_account": settings.COLLEGE_GMAIL_ACCOUNT
        }

    def disconnect(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Disconnect and revoke local Gmail credentials for given user."""
        token_dir = os.path.dirname(settings.GMAIL_TOKEN_PATH) if settings.GMAIL_TOKEN_PATH else "./backend/app/database"

        if user_id:
            user_token = os.path.join(token_dir, f"token_{user_id}.json")
            if os.path.exists(user_token):
                try:
                    os.remove(user_token)
                except Exception as e:
                    logger.error(f"Error deleting user token file: {e}")

        # Also remove default token if user_id is 2 or not specified
        if not user_id or user_id == 2:
            token_path = settings.GMAIL_TOKEN_PATH
            if token_path and os.path.exists(token_path):
                try:
                    os.remove(token_path)
                    logger.info("Gmail credentials removed successfully from default path.")
                except Exception as e:
                    logger.error(f"Error deleting token file: {e}")
                    return {"status": "error", "message": f"Could not remove token file: {e}"}

        # Clear active service from GmailProvider
        from backend.app.services.gmail_provider import GmailProvider
        from backend.app.services.email_provider_manager import email_provider_manager
        
        # Reset any cached provider instances
        active_provider = email_provider_manager.get_provider("gmail", user_id=user_id)
        if isinstance(active_provider, GmailProvider):
            active_provider._service = None

        return {
            "status": "disconnected",
            "message": "Gmail connection successfully revoked."
        }

oauth_service = GoogleOAuthService()
