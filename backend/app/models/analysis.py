from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    summary = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    priority = Column(String(20), nullable=False, index=True)
    priority_reason = Column(Text, nullable=False)
    deadline_date = Column(String(50), nullable=True)
    deadline_status = Column(String(20), nullable=True)
    reply_expected = Column(Boolean, default=False, nullable=False)
    reply_reason = Column(Text, nullable=True)
    suggested_reply = Column(Text, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship back to Email
    email = relationship("Email", back_populates="analysis")

    # One-to-many relationship with Evidence
    evidences = relationship(
        "Evidence",
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="Evidence.id"
    )

    def __repr__(self):
        return f"<AIAnalysis(id={self.id}, email_id={self.email_id}, category='{self.category}', priority='{self.priority}')>"
