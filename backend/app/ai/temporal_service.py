from datetime import datetime
from typing import Optional, Dict, Any

from backend.app.utils.date_parser import (
    normalize_temporal_expression,
    normalize_time_expression,
    extract_actionable_deadline,
    compute_temporal_status
)

class TemporalExtractionService:
    """Specialized agent sub-service for temporal expression detection and date normalization.
    
    Supports expressions:
    - Tomorrow / Day after tomorrow / Today / Within N days
    - Monday / Before Friday / Next week
    - September 10 / Sept 10th / 15 September 2026 / DD.MM.YYYY / DD/MM/YYYY
    - By end of day / At 10 AM / 14:30
    
    Anchors relative dates to email arrival timestamp.
    Differentiates actionable deadlines from past/historical non-deadline dates.
    Strictly returns null where dates cannot be reliably determined (never invents).
    """

    def extract_deadline(
        self,
        text: str,
        reference_date: Optional[datetime] = None,
        current_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        iso_date, raw_text, confidence = extract_actionable_deadline(text, reference_date=reference_date)
        deadline_status = None
        relative_status = None
        if iso_date:
            c_date = current_date.date() if isinstance(current_date, datetime) else current_date
            deadline_status, relative_status = compute_temporal_status(iso_date, current_date=c_date)
        return {
            "deadline": iso_date,
            "raw_text": raw_text,
            "confidence": confidence,
            "deadline_status": deadline_status,
            "relative_status": relative_status
        }

    def extract_time(self, text: str) -> Optional[str]:
        return normalize_time_expression(text)
