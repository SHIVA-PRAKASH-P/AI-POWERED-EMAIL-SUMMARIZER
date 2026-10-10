import re
from typing import Dict, Any

class ClassificationService:
    """Specialized agent sub-service for academic category classification and role detection."""

    CATEGORIES = [
        "Academic",
        "Administrative",
        "Examination",
        "Meeting",
        "Student",
        "Department",
        "Event",
        "Research",
        "Placement",
        "General"
    ]

    def classify(self, subject: str, body: str, sender: str) -> Dict[str, Any]:
        text = f"{subject} {body}".lower()
        sender_lower = sender.lower()

        # Sender role authority detection
        sender_role = "FACULTY"
        if "dean" in sender_lower or "dean" in text:
            sender_role = "DEAN"
        elif "hod" in sender_lower or "head of department" in text:
            sender_role = "HOD"
        elif "coe" in sender_lower or "controller of examinations" in text:
            sender_role = "COE"
        elif "registrar" in sender_lower or "registrar" in text:
            sender_role = "REGISTRAR"
        elif "student" in sender_lower or "roll no" in text:
            sender_role = "STUDENT"
        elif "placement" in sender_lower:
            sender_role = "PLACEMENT_CELL"
        elif "ieee" in sender_lower or "journal" in sender_lower:
            sender_role = "EXTERNAL_ACADEMIC"

        # Domain classification
        if any(k in text for k in ["internal assessment", "mark sheet", "marks submission", "mid term assessment"]):
            category = "Academic"
        elif any(k in text for k in ["question paper", "exam", "quiz 1", "end semester", "invigilation", "confidential section"]):
            category = "Examination"
        elif any(k in text for k in ["board of studies", "bos", "minutes of meeting", "annual general meeting"]):
            category = "Meeting"
        elif any(k in text for k in ["serb", "grant", "research proposal", "ieee", "peer-review", "manuscript"]):
            category = "Research"
        elif any(k in text for k in ["placement", "interview coordinator", "hiring drive", "campus hiring"]):
            category = "Placement"
        elif any(k in text for k in ["medical leave", "re-test", "student", "roll no"]):
            category = "Student"
        elif any(k in text for k in ["naac", "accreditation", "apar", "self-appraisal", "circular no", "biometric", "memorandum"]):
            category = "Administrative"
        elif any(k in text for k in ["hackathon", "sih", "fdp", "faculty development program", "workshop"]):
            category = "Event"
        elif any(k in text for k in ["library", "book purchase", "department advisory"]):
            category = "Department"
        elif any(k in text for k in ["review meeting", "department meeting"]):
            category = "Meeting"
        elif any(k in text for k in ["syllabus", "course file", "capstone"]):
            category = "Academic"
        elif any(k in text for k in ["wi-fi", "firewall", "maintenance", "downtime"]):
            category = "General"
        else:
            category = "Academic"

        return {
            "category": category,
            "sender_role": sender_role,
            "confidence": 0.95
        }
