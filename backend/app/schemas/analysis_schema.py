from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional
from backend.app.schemas.evidence_schema import EvidenceResponse

class AIAnalysisBase(BaseModel):
    summary: str
    category: str
    priority: str
    priority_reason: str
    deadline_date: Optional[str] = None
    deadline_status: Optional[str] = None
    reply_expected: bool = False
    reply_reason: Optional[str] = None
    suggested_reply: Optional[str] = None

class AIAnalysisResponse(AIAnalysisBase):
    id: int
    email_id: int
    processed_at: datetime
    evidences: List[EvidenceResponse] = []

    model_config = ConfigDict(from_attributes=True)
