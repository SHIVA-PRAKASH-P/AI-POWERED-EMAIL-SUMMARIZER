from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from backend.app.schemas.email_schema import EmailSummaryResponse
from backend.app.schemas.action_schema import ActionItemResponse
from backend.app.schemas.meeting_schema import MeetingResponse

class DashboardMetrics(BaseModel):
    total_emails: int
    unread_emails: int
    high_priority_count: int
    medium_priority_count: int = 0
    low_priority_count: int = 0
    upcoming_deadlines_count: int
    expired_deadlines_count: int = 0
    upcoming_meetings_count: int
    pending_actions_count: int

class DeadlineItem(BaseModel):
    id: int
    email_id: int
    email_subject: str
    email_sender: str
    task_description: str
    due_date: str
    priority: str
    completed: bool
    relationship_type: str = "DUE_ON"
    target_event: Optional[str] = None
    relationship_reason: Optional[str] = None
    deadline_status: Optional[str] = None
    relative_status: Optional[str] = None

class DashboardResponse(BaseModel):
    metrics: DashboardMetrics
    priority_emails: List[EmailSummaryResponse]
    upcoming_deadlines: List[DeadlineItem]
    expired_deadlines: List[DeadlineItem] = []
    upcoming_meetings: List[MeetingResponse]
    pending_tasks: List[ActionItemResponse]
    recent_emails: List[EmailSummaryResponse]
