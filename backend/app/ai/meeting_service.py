import re
from datetime import datetime
from typing import Optional, Dict, Any

from backend.app.utils.date_parser import (
    normalize_temporal_expression,
    normalize_time_expression
)

class MeetingExtractionService:
    """Specialized agent sub-service for meeting, venue, and calendar event extraction.
    
    Extracts:
    - Meeting title
    - Normalized date (anchored to received_at)
    - Normalized 24-hour time (e.g. 10:00, 14:30)
    - Location (Physical venues with room numbers, or virtual platforms: Google Meet, Zoom)
    - Preparation checklist
    """

    MEETING_TRIGGERS = [
        r'\bmeeting\b', r'\breview session\b', r'\baudit\b', r'\bbriefing\b',
        r'\bpresentations\b', r'\bconference\b', r'\bwebinar\b', r'\bdiscussion\b',
        r'\bconvene\b', r'\bconducted on\b', r'\bheld on\b'
    ]

    VIRTUAL_PLATFORMS = ["google meet", "zoom", "ms teams", "microsoft teams", "webex", "online"]

    def extract_meeting(
        self,
        subject: str,
        body: str,
        reference_date: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        text = f"{subject}\n{body}"
        text_lower = text.lower()

        # Check if meeting cues exist
        has_cue = any(re.search(trigger, text_lower) for trigger in self.MEETING_TRIGGERS)
        if not has_cue:
            return None

        # Prioritize sentence containing the meeting trigger for accurate date/time extraction
        sentences = [s.strip() for s in re.split(r'[\n\.\?!]', body) if len(s.strip()) > 5]
        meeting_sentence = None
        for s in sentences:
            if any(re.search(trigger, s.lower()) for trigger in self.MEETING_TRIGGERS):
                meeting_sentence = s
                break

        # Extract Time (from meeting sentence first, fallback to text)
        meeting_time = None
        if meeting_sentence:
            meeting_time = normalize_time_expression(meeting_sentence)
        if not meeting_time:
            meeting_time = normalize_time_expression(text)

        # Extract Date using the temporal engine (from meeting sentence first, fallback to text)
        meeting_date = None
        if meeting_sentence:
            meeting_date, _, _ = normalize_temporal_expression(meeting_sentence, reference_date=reference_date)
        if not meeting_date:
            meeting_date, _, _ = normalize_temporal_expression(text, reference_date=reference_date)

        # Extract Location / Venue
        location = None
        # Check virtual platforms first
        for vp in self.VIRTUAL_PLATFORMS:
            if vp in text_lower:
                location = vp.title()
                break

        # Check physical venues with room/hall identifiers
        if not location:
            venue_patterns = [
                r'(?:in|at)\s+the\s+([A-Z][a-zA-Z0-9\s]+(?:Hall|Room|Auditorium|Lab|Center|Wing|Building)(?:\s+[0-9a-zA-Z]+)?)',
                r'(?:in|at)\s+([A-Z][a-zA-Z0-9\s]+(?:Hall|Room|Auditorium|Lab|Center|Wing|Building)(?:\s+[0-9a-zA-Z]+)?)',
                r'\bVenue:\s*([A-Za-z0-9\s,\-]+)'
            ]
            for vp in venue_patterns:
                vm = re.search(vp, text)
                if vm:
                    location = vm.group(1).strip()
                    break

        # Extract Preparation notes
        preparation = None
        prep_patterns = [
            r'(?:please bring|bring|ensure|review attached|review draft|review syllabus)\s+([^\.\n]+)',
            r'\bPreparation:\s*([^\.\n]+)'
        ]
        for pp in prep_patterns:
            pm = re.search(pp, text, re.IGNORECASE)
            if pm:
                preparation = pm.group(0).strip()
                break

        # Generate concise meeting title
        title = subject.strip()
        if not any(k in title.lower() for k in ["meeting", "review", "audit", "briefing", "presentations"]):
            title = f"{title} - Review Meeting"

        return {
            "title": title,
            "date": meeting_date,
            "time": meeting_time,
            "location": location,
            "preparation": preparation,
            "confidence": 0.96
        }
