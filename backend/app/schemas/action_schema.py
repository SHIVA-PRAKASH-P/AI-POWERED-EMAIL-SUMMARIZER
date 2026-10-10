from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class ActionItemBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=500, description="Task imperative action description")
    due_date: Optional[str] = Field(None, max_length=20, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Normalized target date (YYYY-MM-DD)")
    priority: str = Field("MEDIUM", max_length=10, pattern=r"^(?i)(HIGH|MEDIUM|LOW)$", description="Priority rating: HIGH, MEDIUM, LOW")
    completed: bool = False
    relationship_type: str = Field("DUE_ON", max_length=30, pattern=r"^(?i)(DUE_ON|PREPARE_BEFORE|ATTEND_BY|COMMUNICATE_BY|STANDALONE)$", description="Relational link type")
    target_event: Optional[str] = Field(None, max_length=255, description="Associated meeting or institutional event")
    relationship_reason: Optional[str] = Field(None, max_length=500, description="Relational justification")
    binding_confidence: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")

class ActionItemCreate(ActionItemBase):
    pass

class ActionItemUpdate(BaseModel):
    completed: Optional[bool] = None
    priority: Optional[str] = Field(None, max_length=10, pattern=r"^(?i)(HIGH|MEDIUM|LOW)$")
    due_date: Optional[str] = Field(None, max_length=20, pattern=r"^\d{4}-\d{2}-\d{2}$")
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    relationship_type: Optional[str] = Field(None, max_length=30, pattern=r"^(?i)(DUE_ON|PREPARE_BEFORE|ATTEND_BY|COMMUNICATE_BY|STANDALONE)$")
    target_event: Optional[str] = Field(None, max_length=255)
    relationship_reason: Optional[str] = Field(None, max_length=500)
    binding_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

class ActionItemResponse(ActionItemBase):
    id: int
    email_id: int
    email_subject: Optional[str] = None
    email_sender: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
