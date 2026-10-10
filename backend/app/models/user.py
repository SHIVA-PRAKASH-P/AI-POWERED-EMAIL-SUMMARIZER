"""User Identity Model for Multi-User Architecture (Stage 19B).

Supports distinct users:
1. Mock / Test User (mock.faculty@university.edu)
2. College Gmail User (shivaprakashp.cs24@bitsathy.ac.in)
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from backend.app.database.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(100), default="Faculty Member", nullable=False)
    provider_type = Column(String(50), default="mock", nullable=False)  # "mock" or "gmail"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    emails = relationship(
        "Email",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Email.received_at.desc()"
    )

    preference = relationship(
        "FacultyPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', provider='{self.provider_type}')>"
