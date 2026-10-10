from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class GroundTruthMeeting(BaseModel):
    """Ground truth meeting representation for evaluation."""
    title: str
    date: Optional[str] = None
    time: Optional[str] = None
    location: Optional[str] = None
    preparation: Optional[str] = None

class GroundTruthEmail(BaseModel):
    """Schema for ground-truth annotated email in the golden benchmark dataset."""
    id: str
    sender: str
    subject: str
    body: str
    received_at: str  # ISO timestamp or YYYY-MM-DD string
    expected_category: str
    expected_priority: str  # "HIGH", "MEDIUM", "LOW"
    expected_priority_reason: Optional[str] = None
    expected_deadline: Optional[str] = None  # Normalized YYYY-MM-DD
    expected_meeting: Optional[GroundTruthMeeting] = None
    expected_actions: List[str] = Field(default_factory=list)
    expected_summary: str
    grounded_spans: List[str] = Field(default_factory=list)  # Verified textual spans in email
    domain: str = "Academic Administration"
    difficulty: str = "Standard"  # "Standard", "Complex", "Ambiguous"
    metadata: Dict[str, Any] = Field(default_factory=dict)
