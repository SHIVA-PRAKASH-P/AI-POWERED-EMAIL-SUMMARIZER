from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional
from backend.app.schemas.analysis_schema import AIAnalysisResponse
from backend.app.schemas.action_schema import ActionItemResponse
from backend.app.schemas.meeting_schema import MeetingResponse
from backend.app.schemas.entity_schema import EntityResponse

class EmailBase(BaseModel):
    sender: str
    recipient: str
    subject: str
    body: str
    received_at: datetime
    is_read: bool = False

class EmailSummaryResponse(BaseModel):
    id: int
    sender: str
    recipient: str
    subject: str
    body_preview: str
    received_at: datetime
    is_read: bool
    created_at: datetime
    has_analysis: bool = False
    category: Optional[str] = None
    priority: Optional[str] = None
    priority_reason: Optional[str] = None
    action_items_count: int = 0
    meetings_count: int = 0
    has_deadline: bool = False

    model_config = ConfigDict(from_attributes=True)

class EmailDetailResponse(BaseModel):
    id: int
    sender: str
    recipient: str
    subject: str
    body: str
    received_at: datetime
    is_read: bool
    created_at: datetime
    analysis: Optional[AIAnalysisResponse] = None
    action_items: List[ActionItemResponse] = []
    meetings: List[MeetingResponse] = []
    entities: List[EntityResponse] = []

    model_config = ConfigDict(from_attributes=True)
