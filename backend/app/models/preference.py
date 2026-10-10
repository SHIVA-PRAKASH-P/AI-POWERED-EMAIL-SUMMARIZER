"""Faculty Personalization & Preference SQLAlchemy Model (Stage 15).

Stores user-specific institutional profiles, priority tuning weights,
critical category focuses, and custom priority keyword rules.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class FacultyPreference(Base):
    __tablename__ = "faculty_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, unique=True, index=True)
    faculty_name = Column(String(255), default="Dr. Faculty", nullable=False)
    role = Column(String(255), default="Professor & Academic Incharge", nullable=False)
    department = Column(String(255), default="Computer Science & Engineering", nullable=False)

    # Relationship to User (Stage 19B)
    user = relationship("User", back_populates="preference")
    
    # Priority tuning mode: 'BALANCED', 'DEADLINE_HEAVY', 'AUTHORITY_FIRST', 'CUSTOM'
    priority_mode = Column(String(50), default="BALANCED", nullable=False)
    
    # Comma-separated category priorities (e.g. "Examination,Academic")
    high_priority_categories = Column(Text, default="Examination,Academic", nullable=False)
    
    # Comma-separated custom keywords that force priority elevation
    custom_keywords_high = Column(Text, default="marks,question paper,naac,accreditation,urgent", nullable=False)
    
    # Comma-separated custom keywords that reduce priority
    custom_keywords_low = Column(Text, default="newsletter,invitation,webinar,sports", nullable=False)
    
    # Threshold for considering upcoming deadline immediate (in days)
    deadline_urgency_days = Column(Integer, default=3, nullable=False)
    
    # Mathematical factor weight multipliers
    authority_weight = Column(Float, default=1.0, nullable=False)
    deadline_weight = Column(Float, default=1.0, nullable=False)
    
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    def __repr__(self):
        return f"<FacultyPreference(id={self.id}, role='{self.role}', dept='{self.department}')>"
