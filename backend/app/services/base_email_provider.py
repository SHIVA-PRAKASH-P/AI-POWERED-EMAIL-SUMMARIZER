from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

class BaseEmailProvider(ABC):
    """Abstract Base Class for modular email ingestion providers.
    
    Standard message representation returned by all providers:
    {
        "id": str,               # Unique message ID from provider or synthetic key
        "sender": str,           # Sender email address / name
        "recipient": str,        # Recipient email address
        "subject": str,          # Subject line
        "body": str,             # Clean plaintext message body
        "received_at": datetime, # Transmission timestamp
        "is_read": bool          # Read / unread status
    }
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the email provider."""
        pass

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check whether the provider has valid credentials / active session."""
        pass

    @abstractmethod
    def get_messages(
        self,
        limit: int = 50,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve recent email messages matching optional search query."""
        pass

    @abstractmethod
    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific email message by its identifier."""
        pass
