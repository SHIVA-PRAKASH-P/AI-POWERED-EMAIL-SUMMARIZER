from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

class AIMeetingOutput(BaseModel):
    title: str
    date: Optional[str] = None
    time: Optional[str] = None
    location: Optional[str] = None
    preparation: Optional[str] = None

class AIEntityOutput(BaseModel):
    entity_type: str = Field(alias="type", default="GENERAL")
    entity_value: str = Field(alias="value")

    model_config = ConfigDict(populate_by_name=True)

class AIEvidenceOutput(BaseModel):
    field_name: str
    extracted_value: str
    source_text: str
    confidence: float = 1.0
    validation_status: str = "VERIFIED"
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    grounding_method: Optional[str] = "EXACT_SPAN"

class AIActionItemOutput(BaseModel):
    description: str
    due_date: Optional[str] = None
    priority: str = "MEDIUM"
    relationship_type: str = "DUE_ON"
    target_event: Optional[str] = None
    relationship_reason: Optional[str] = None
    binding_confidence: float = 1.0

class AIServiceOutput(BaseModel):
    summary: str
    category: str
    priority: str
    priority_reason: str
    deadline: Optional[str] = None
    deadline_date: Optional[str] = None
    deadline_status: Optional[str] = None
    reply_expected: bool = False
    reply_reason: Optional[str] = None
    suggested_reply: Optional[str] = None
    meeting: Optional[AIMeetingOutput] = None
    action_items: List[str] = []
    structured_actions: List[AIActionItemOutput] = []
    important_entities: List[AIEntityOutput] = []
    evidence: List[AIEvidenceOutput] = []
