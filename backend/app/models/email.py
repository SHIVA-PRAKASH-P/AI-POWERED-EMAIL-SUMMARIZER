from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    provider_message_id = Column(String(255), nullable=True, index=True)
    sender = Column(String(255), nullable=False, index=True)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False, index=True)
    body = Column(Text, nullable=False)
    received_at = Column(DateTime, nullable=False, index=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to User (Stage 19B Multi-User Isolation)
    user = relationship("User", back_populates="emails")

    # One-to-one relationship with AIAnalysis
    analysis = relationship(
        "AIAnalysis",
        back_populates="email",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # One-to-many relationships
    action_items = relationship(
        "ActionItem",
        back_populates="email",
        cascade="all, delete-orphan",
        order_by="ActionItem.id"
    )

    meetings = relationship(
        "Meeting",
        back_populates="email",
        cascade="all, delete-orphan",
        order_by="Meeting.id"
    )

    entities = relationship(
        "Entity",
        back_populates="email",
        cascade="all, delete-orphan",
        order_by="Entity.id"
    )

    def __repr__(self):
        return f"<Email(id={self.id}, sender='{self.sender}', subject='{self.subject[:30]}')>"
