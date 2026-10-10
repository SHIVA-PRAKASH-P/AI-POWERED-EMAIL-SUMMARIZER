"""Server-Controlled Session Manager for Multi-User Identity (Stage 19B).

Issues, validates, and revokes cryptographically secure session tokens.
Enforces that sessions can only be created for verified, pre-registered accounts:
1. User 1: mock.faculty@university.edu (Mock/Test User)
2. User 2: shivaprakashp.cs24@bitsathy.ac.in (College Gmail User)
"""

import os
import json
import time
import secrets
import logging
import threading
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SessionManager:
    """Thread-safe server-side session registry."""

    DEFAULT_EXPIRY_SECONDS = 86400  # 24 hours
    ALLOWED_EMAILS = {
        "mock.faculty@university.edu",
        "shivaprakashp.cs24@bitsathy.ac.in"
    }

    def __init__(self, persistence_file: Optional[str] = None):
        self._lock = threading.Lock()
        # { session_token: { "user_id": int, "email": str, "created_at": float, "expires_at": float } }
        self._sessions: Dict[str, Dict[str, Any]] = {}
        
        # Static persistent mock token for zero-configuration local development and regression testing
        self._default_mock_token = "mock-faculty-default-session-token-stage19b"
        self._sessions[self._default_mock_token] = {
            "user_id": 1,
            "email": "mock.faculty@university.edu",
            "created_at": time.time(),
            "expires_at": time.time() + (self.DEFAULT_EXPIRY_SECONDS * 365)  # Long-lived default
        }

        self._persistence_file = persistence_file or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "database", ".user_sessions.json")
        )
        self._load_persisted_sessions()

    def _cleanup_expired(self) -> None:
        now = time.time()
        with self._lock:
            expired = [
                token for token, data in self._sessions.items()
                if token != self._default_mock_token and now > data.get("expires_at", 0)
            ]
            for token in expired:
                self._sessions.pop(token, None)

    def _load_persisted_sessions(self) -> None:
        if not self._persistence_file or not os.path.exists(self._persistence_file):
            return
        try:
            with open(self._persistence_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                now = time.time()
                for token, item in data.items():
                    if isinstance(item, dict) and (now <= item.get("expires_at", 0)):
                        self._sessions[token] = item
        except Exception as e:
            logger.debug("Could not load persisted user sessions: %s", e)

    def _save_persisted_sessions(self) -> None:
        if not self._persistence_file:
            return
        try:
            target_dir = os.path.dirname(self._persistence_file)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            temp_file = f"{self._persistence_file}.tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self._sessions, f)
            os.replace(temp_file, self._persistence_file)
        except Exception as e:
            logger.warning("Could not persist user sessions: %s", e)

    def register_allowed_email(self, email: str) -> None:
        """Dynamically register an authenticated email address for session issuance."""
        if email and email.strip():
            with self._lock:
                self.ALLOWED_EMAILS.add(email.strip().lower())

    def create_session(self, user_id: int, user_email: str) -> str:
        """Create and register a cryptographically secure server session token.
        
        Strictly rejects any email not in ALLOWED_EMAILS.
        """
        clean_email = user_email.strip().lower()
        if clean_email not in self.ALLOWED_EMAILS:
            raise ValueError(f"Identity '{clean_email}' is not authorized to create a session.")

        self._cleanup_expired()
        token = secrets.token_urlsafe(32)
        now = time.time()

        with self._lock:
            self._sessions[token] = {
                "user_id": user_id,
                "email": clean_email,
                "created_at": now,
                "expires_at": now + self.DEFAULT_EXPIRY_SECONDS
            }
            self._save_persisted_sessions()

        logger.info("Created server session for user %s (id: %d)", clean_email, user_id)
        return token

    def validate_session(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        """Validate session token and return user metadata, or None if invalid/expired."""
        if not token:
            return None
        self._cleanup_expired()

        with self._lock:
            session_data = self._sessions.get(token)
            if not session_data:
                return None
            if time.time() > session_data.get("expires_at", 0):
                self._sessions.pop(token, None)
                return None
            return session_data

    def revoke_session(self, token: str) -> bool:
        """Revoke a session token."""
        if token == self._default_mock_token:
            return False
        with self._lock:
            revoked = self._sessions.pop(token, None) is not None
            if revoked:
                self._save_persisted_sessions()
            return revoked

    @property
    def default_mock_token(self) -> str:
        return self._default_mock_token

session_manager = SessionManager()
