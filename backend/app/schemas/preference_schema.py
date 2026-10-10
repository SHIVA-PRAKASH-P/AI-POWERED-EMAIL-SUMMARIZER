"""Pydantic Schemas for Faculty Personalization & Preferences (Stage 15 & 16 Hardening)."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class FacultyPreferenceBase(BaseModel):
    faculty_name: str = Field(default="Dr. Faculty", min_length=1, max_length=150, description="Faculty member display name")
    role: str = Field(default="Professor & Academic Incharge", min_length=1, max_length=150, description="Institutional designation")
    department: str = Field(default="Computer Science & Engineering", min_length=1, max_length=150, description="Academic department")
    priority_mode: str = Field(default="BALANCED", max_length=30, pattern=r"^(?i)(BALANCED|DEADLINE_HEAVY|AUTHORITY_FIRST|CUSTOM)$", description="Tuning preset: BALANCED, DEADLINE_HEAVY, AUTHORITY_FIRST, CUSTOM")
    high_priority_categories: str = Field(default="Examination,Academic", max_length=500, description="Comma-separated category focus list")
    custom_keywords_high: str = Field(default="marks,question paper,naac,accreditation,urgent", max_length=1000, description="Comma-separated high urgency keywords")
    custom_keywords_low: str = Field(default="newsletter,invitation,webinar,sports", max_length=1000, description="Comma-separated low priority demotion keywords")
    deadline_urgency_days: int = Field(default=3, ge=1, le=30, description="Horizon for immediate deadlines (days)")
    authority_weight: float = Field(default=1.0, ge=0.1, le=3.0, description="Authority weight multiplier")
    deadline_weight: float = Field(default=1.0, ge=0.1, le=3.0, description="Deadline weight multiplier")

class FacultyPreferenceUpdate(BaseModel):
    faculty_name: Optional[str] = Field(None, min_length=1, max_length=150)
    role: Optional[str] = Field(None, min_length=1, max_length=150)
    department: Optional[str] = Field(None, min_length=1, max_length=150)
    priority_mode: Optional[str] = Field(None, max_length=30, pattern=r"^(?i)(BALANCED|DEADLINE_HEAVY|AUTHORITY_FIRST|CUSTOM)$")
    high_priority_categories: Optional[str] = Field(None, max_length=500)
    custom_keywords_high: Optional[str] = Field(None, max_length=1000)
    custom_keywords_low: Optional[str] = Field(None, max_length=1000)
    deadline_urgency_days: Optional[int] = Field(None, ge=1, le=30)
    authority_weight: Optional[float] = Field(None, ge=0.1, le=3.0)
    deadline_weight: Optional[float] = Field(None, ge=0.1, le=3.0)

class FacultyPreferenceResponse(FacultyPreferenceBase):
    id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
