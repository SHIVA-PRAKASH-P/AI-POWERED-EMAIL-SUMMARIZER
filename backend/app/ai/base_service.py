from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from backend.app.schemas.ai_schema import AIServiceOutput

class AIService(ABC):
    """Abstract Base Class for email intelligence processing services."""

    @abstractmethod
    def analyze_email(
        self,
        subject: str,
        body: str,
        sender: str,
        received_at: Optional[datetime] = None
    ) -> AIServiceOutput:
        """Analyze email content and return standardized structured intelligence."""
        pass
