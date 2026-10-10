from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class EvidenceBase(BaseModel):
    field_name: str = Field(..., max_length=50)
    extracted_value: str = Field(..., max_length=2000)
    source_text: str = Field(..., max_length=5000)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    validation_status: str = Field("VERIFIED", max_length=30)
    char_start: Optional[int] = Field(None, ge=0)
    char_end: Optional[int] = Field(None, ge=0)
    grounding_method: Optional[str] = Field("EXACT_SPAN", max_length=50)

class EvidenceResponse(EvidenceBase):
    id: int
    analysis_id: int

    model_config = ConfigDict(from_attributes=True)

class AssertionVerificationRequest(BaseModel):
    field_name: str = Field(..., min_length=1, max_length=50)
    extracted_value: str = Field(..., min_length=1, max_length=2000)
    email_id: Optional[int] = Field(None, ge=1)
    raw_text: Optional[str] = Field(None, max_length=50000)

class AssertionVerificationResponse(BaseModel):
    is_valid: bool
    validation_status: str  # VERIFIED, INFERRED, PARTIAL, UNSUPPORTED
    confidence: float
    grounded_sentence: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    grounding_method: str
    audit_explanation: str
