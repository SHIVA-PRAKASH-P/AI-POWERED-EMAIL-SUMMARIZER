from sqlalchemy import Column, Integer, String, Text, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    due_date = Column(String(50), nullable=True, index=True)
    priority = Column(String(20), default="MEDIUM", nullable=False)
    completed = Column(Boolean, default=False, nullable=False, index=True)
    relationship_type = Column(String(50), default="DUE_ON", nullable=False, index=True)
    target_event = Column(String(255), nullable=True)
    relationship_reason = Column(Text, nullable=True)
    binding_confidence = Column(Float, default=1.0, nullable=True)

    # Relationship back to Email
    email = relationship("Email", back_populates="action_items")

    def __repr__(self):
        return (
            f"<ActionItem(id={self.id}, email_id={self.email_id}, "
            f"relationship='{self.relationship_type}', due_date='{self.due_date}')>"
        )
