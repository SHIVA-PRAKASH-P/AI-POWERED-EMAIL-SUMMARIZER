from pydantic import BaseModel, ConfigDict

class EntityBase(BaseModel):
    entity_type: str
    entity_value: str

class EntityResponse(EntityBase):
    id: int
    email_id: int

    model_config = ConfigDict(from_attributes=True)
