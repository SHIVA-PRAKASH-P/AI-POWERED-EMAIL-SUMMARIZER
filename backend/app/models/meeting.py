from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    meeting_date = Column(String(50), nullable=True)
    meeting_time = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    preparation = Column(Text, nullable=True)

    # Relationship back to Email
    email = relationship("Email", back_populates="meetings")

    def __repr__(self):
        return f"<Meeting(id={self.id}, email_id={self.email_id}, title='{self.title}', date='{self.meeting_date}')>"
