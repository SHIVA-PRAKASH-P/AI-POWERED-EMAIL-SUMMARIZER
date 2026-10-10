"""Deterministic Synthetic Mock Email Provider for Faculty Email Summarizer.

Provides offline, realistic synthetic emails for development, testing, and zero-credential environments.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from backend.app.services.base_email_provider import BaseEmailProvider
from backend.app.database.seed_data import SAMPLE_EMAILS

class MockEmailProvider(BaseEmailProvider):
    """Mock Email Provider delivering synthetic faculty emails without external API requirements."""

    def __init__(self, custom_messages: Optional[List[Dict[str, Any]]] = None):
        if custom_messages is not None:
            self._messages = list(custom_messages)
        else:
            self._messages = self._build_default_messages()

    @property
    def provider_name(self) -> str:
        return "mock"

    def is_authenticated(self) -> bool:
        """Always authenticated in mock/offline mode."""
        return True

    def _build_default_messages(self) -> List[Dict[str, Any]]:
        """Extract standardized email messages from SAMPLE_EMAILS."""
        messages = []
        for idx, sample in enumerate(SAMPLE_EMAILS, start=1):
            messages.append({
                "id": f"mock-msg-{idx:03d}",
                "sender": sample["sender"],
                "recipient": sample.get("recipient", "faculty@university.edu"),
                "subject": sample["subject"],
                "body": sample["body"],
                "received_at": sample["received_at"] if isinstance(sample["received_at"], datetime) else datetime.now(timezone.utc).replace(tzinfo=None),
                "is_read": sample.get("is_read", False)
            })
        return messages

    def get_messages(
        self,
        limit: int = 50,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve mock messages, optionally filtered by keyword query."""
        results = self._messages
        if query and query.strip():
            q = query.strip().lower()
            results = [
                m for m in results
                if q in m["subject"].lower() or q in m["body"].lower() or q in m["sender"].lower()
            ]
        return results[:limit]

    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific mock message by its synthetic ID."""
        for msg in self._messages:
            if msg["id"] == message_id:
                return msg
        return None

    def add_message(self, message: Dict[str, Any]) -> str:
        """Helper to append a mock message during tests."""
        if "id" not in message:
            message["id"] = f"mock-msg-{len(self._messages) + 1:03d}"
        if "received_at" not in message:
            message["received_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        if "is_read" not in message:
            message["is_read"] = False
        self._messages.append(message)
        return message["id"]
