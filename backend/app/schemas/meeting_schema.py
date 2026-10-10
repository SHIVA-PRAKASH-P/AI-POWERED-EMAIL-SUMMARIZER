from pydantic import BaseModel, ConfigDict
from typing import Optional

class MeetingBase(BaseModel):
    title: str
    meeting_date: Optional[str] = None
    meeting_time: Optional[str] = None
    location: Optional[str] = None
    preparation: Optional[str] = None

class MeetingResponse(MeetingBase):
    id: int
    email_id: int
    email_subject: Optional[str] = None
    email_sender: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
