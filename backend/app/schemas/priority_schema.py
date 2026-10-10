from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Optional

class AIPriorityResult(BaseModel):
    """Structured output from Context-Aware AI Priority Classification."""
    priority: str = Field(..., description="HIGH | MEDIUM | LOW")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reason: str = Field(..., description="Short human-readable contextual explanation")

    model_config = ConfigDict(from_attributes=True)

class PriorityAssessment(BaseModel):
    """Structured internal representation of the multi-factor priority analysis."""
    mandatory: bool
    urgency_language: bool
    deadline_proximity: str  # "IMMEDIATE", "HIGH", "MEDIUM", "LOW", "NONE"
    sender_authority: str    # "STATUTORY", "DEPARTMENTAL", "STUDENT", "EXTERNAL", "ROUTINE"
    academic_context: bool
    examination_context: bool
    required_action: bool
    meeting_proximity: str   # "IMMEDIATE", "APPROACHING", "NONE"
    consequence_indicators: bool
    score: float
    priority: str            # "HIGH", "MEDIUM", "LOW"
    priority_reason: str     # Transparent, explainable rationale
    confidence: float = 1.0
    reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    def model_post_init(self, __context) -> None:
        if self.reason is None and self.priority_reason:
            self.reason = self.priority_reason
        elif self.priority_reason is None and self.reason:
            self.priority_reason = self.reason
