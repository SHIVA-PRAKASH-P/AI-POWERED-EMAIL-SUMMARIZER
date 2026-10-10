from backend.app.schemas.evidence_schema import (
    EvidenceResponse,
    AssertionVerificationRequest,
    AssertionVerificationResponse
)
from backend.app.schemas.entity_schema import EntityResponse
from backend.app.schemas.action_schema import ActionItemResponse, ActionItemUpdate, ActionItemCreate
from backend.app.schemas.meeting_schema import MeetingResponse
from backend.app.schemas.analysis_schema import AIAnalysisResponse
from backend.app.schemas.email_schema import EmailSummaryResponse, EmailDetailResponse
from backend.app.schemas.dashboard_schema import DashboardResponse, DashboardMetrics, DeadlineItem
from backend.app.schemas.preference_schema import (
    FacultyPreferenceBase,
    FacultyPreferenceUpdate,
    FacultyPreferenceResponse
)

__all__ = [
    "EvidenceResponse",
    "EntityResponse",
    "ActionItemResponse",
    "ActionItemUpdate",
    "ActionItemCreate",
    "MeetingResponse",
    "AIAnalysisResponse",
    "EmailSummaryResponse",
    "EmailDetailResponse",
    "DashboardResponse",
    "DashboardMetrics",
    "DeadlineItem",
    "FacultyPreferenceBase",
    "FacultyPreferenceUpdate",
    "FacultyPreferenceResponse",
]
