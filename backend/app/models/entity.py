from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)
    entity_value = Column(String(255), nullable=False)

    # Relationship back to Email
    email = relationship("Email", back_populates="entities")

    def __repr__(self):
        return f"<Entity(id={self.id}, email_id={self.email_id}, type='{self.entity_type}', value='{self.entity_value}')>"
