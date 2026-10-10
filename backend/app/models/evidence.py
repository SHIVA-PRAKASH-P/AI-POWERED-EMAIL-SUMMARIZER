from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class Evidence(Base):
    __tablename__ = "evidences"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("ai_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, index=True)
    extracted_value = Column(Text, nullable=False)
    source_text = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    validation_status = Column(String(50), default="VERIFIED", nullable=False, index=True)
    char_start = Column(Integer, nullable=True)
    char_end = Column(Integer, nullable=True)
    grounding_method = Column(String(50), default="EXACT_SPAN", nullable=True)

    # Relationship back to AIAnalysis
    analysis = relationship("AIAnalysis", back_populates="evidences")

    def __repr__(self):
        return (
            f"<Evidence(id={self.id}, field='{self.field_name}', "
            f"status='{self.validation_status}', confidence={self.confidence})>"
        )
