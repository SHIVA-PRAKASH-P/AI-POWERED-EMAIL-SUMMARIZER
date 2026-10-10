import pytest
from datetime import datetime
from backend.app.utils.date_parser import normalize_temporal_expression, normalize_time_expression
from backend.app.ai.temporal_service import TemporalExtractionService
from backend.app.ai.meeting_service import MeetingExtractionService
from backend.app.ai.action_service import ActionExtractionService
from backend.app.ai.entity_service import EntityExtractionService
from backend.app.ai.classification_service import ClassificationService
from backend.app.ai.orchestrator import AIOrchestrator

# Fixed baseline epoch: Sunday, September 6, 2026, 09:00 AM
REF_DATE = datetime(2026, 9, 6, 9, 0, 0)

# ==========================================
# 1. TEMPORAL NORMALIZATION (NORMAL & EDGES)
# ==========================================

def test_temporal_explicit_dates():
    """Test standard explicit date normalization."""
    # Month + Day
    d1, _, _ = normalize_temporal_expression("Submit marks before September 10.", REF_DATE)
    assert d1 == "2026-09-10"

    # Abbreviated month
    d2, _, _ = normalize_temporal_expression("Due by Oct 15, 2026.", REF_DATE)
    assert d2 == "2026-10-15"

    # Ordinal numbers
    d3, _, _ = normalize_temporal_expression("Submission closes on Sept 25th.", REF_DATE)
    assert d3 == "2026-09-25"

def test_temporal_relative_expressions():
    """Test relative date resolutions anchored to reference date (2026-09-06, Sunday)."""
    # Tomorrow (Monday, Sept 7)
    d_tom, _, _ = normalize_temporal_expression("All files must be submitted tomorrow.", REF_DATE)
    assert d_tom == "2026-09-07"

    # Before Friday (Friday, Sept 11)
    d_fri, _, _ = normalize_temporal_expression("Please reply before Friday.", REF_DATE)
    assert d_fri == "2026-09-11"

    # Monday (Tomorrow Monday, Sept 7)
    d_mon, _, _ = normalize_temporal_expression("Meeting on Monday morning.", REF_DATE)
    assert d_mon == "2026-09-07"

    # Next week (Monday of next week, Sept 14)
    d_nw, _, _ = normalize_temporal_expression("Submit final draft next week.", REF_DATE)
    assert d_nw == "2026-09-14"

    # End of day (Resolves to reference date Sept 6)
    d_eod, _, _ = normalize_temporal_expression("Complete task by end of day.", REF_DATE)
    assert d_eod == "2026-09-06"

def test_temporal_time_normalization():
    """Test 12-hour and 24-hour time parsing into HH:MM."""
    assert normalize_time_expression("Meeting at 10 AM") == "10:00"
    assert normalize_time_expression("Session begins at 2:30 PM") == "14:30"
    assert normalize_time_expression("Briefing at 9:00 am") == "09:00"
    assert normalize_time_expression("Downtime starting at 23:00") == "23:00"
    assert normalize_time_expression("No time specified") is None

def test_temporal_zero_hallucination_on_ambiguous():
    """Verify system returns None and NEVER invents dates when information is absent or ambiguous."""
    # Vague timeline -> Must return None
    d1, _, _ = normalize_temporal_expression("Please get this done as soon as possible.", REF_DATE)
    assert d1 is None

    # Ambiguous timeline -> Must return None
    d2, _, _ = normalize_temporal_expression("We will organize a session some time next month.", REF_DATE)
    assert d2 is None

    # Completely absent date -> Must return None
    d3, _, _ = normalize_temporal_expression("Thank you for your assistance with the curriculum.", REF_DATE)
    assert d3 is None

# ==========================================
# 2. MEETING EXTRACTION (NORMAL & EDGES)
# ==========================================

def test_meeting_extraction_physical_venue():
    """Test extracting physical meeting with venue room number and preparation."""
    service = MeetingExtractionService()
    subject = "Internal Assessment Review Meeting"
    body = "A review meeting will be conducted on September 8 at 10 AM in the Seminar Hall. Please bring updated mark sheet."
    
    mtg = service.extract_meeting(subject, body, reference_date=REF_DATE)
    assert mtg is not None
    assert mtg["date"] == "2026-09-08"
    assert mtg["time"] == "10:00"
    assert mtg["location"] == "Seminar Hall"
    assert "bring updated mark sheet" in mtg["preparation"].lower()

def test_meeting_extraction_virtual_platform():
    """Test meeting extraction with virtual platform link."""
    service = MeetingExtractionService()
    subject = "Faculty Committee Sync"
    body = "Our briefing will take place on September 9 at 2 PM on Google Meet."
    
    mtg = service.extract_meeting(subject, body, reference_date=REF_DATE)
    assert mtg is not None
    assert mtg["date"] == "2026-09-09"
    assert mtg["time"] == "14:00"
    assert mtg["location"] == "Google Meet"

def test_meeting_without_venue_edge_case():
    """Test meeting extraction when no physical venue is mentioned."""
    service = MeetingExtractionService()
    subject = "Emergency Department Meeting"
    body = "All members must attend a discussion on September 10 at 11 AM."
    
    mtg = service.extract_meeting(subject, body, reference_date=REF_DATE)
    assert mtg is not None
    assert mtg["date"] == "2026-09-10"
    assert mtg["time"] == "11:00"
    assert mtg["location"] is None  # Does not invent a venue

def test_no_meeting_edge_case():
    """Test non-meeting email returns None."""
    service = MeetingExtractionService()
    subject = "Book Recommendations for Library"
    body = "Please send recommendations for new textbooks before September 30."
    assert service.extract_meeting(subject, body, reference_date=REF_DATE) is None

# ==========================================
# 3. ACTION & ENTITY EXTRACTION
# ==========================================

def test_action_extraction_polite_cleanup():
    """Test imperative task extraction and removal of conversational fillers."""
    service = ActionExtractionService()
    body = "All members are requested to submit internal assessment marks. Please bring the updated mark sheet."
    actions = service.extract_actions(body, deadline="2026-09-10")
    
    assert len(actions) == 2
    assert "submit internal assessment marks" in actions[0]["description"].lower()
    assert "bring the updated mark sheet" in actions[1]["description"].lower()
    # Relationship type mapped
    assert actions[0]["relationship_type"] == "DUE_ON"

def test_entity_extraction():
    """Test extracting course codes, departments, organizations, and committees."""
    service = EntityExtractionService()
    text = (
        "Dear Faculty of Computer Science & Engineering, regarding course CS2204, "
        "the Board of Studies and NAAC peer team requested syllabus review."
    )
    entities = service.extract_entities(text, sender="hod.cse@university.edu")
    
    types = {e.entity_type: e.entity_value for e in entities}
    assert "DEPARTMENT" in types
    assert types["DEPARTMENT"] == "Computer Science & Engineering"
    assert "COURSE_CODE" in types
    assert types["COURSE_CODE"] == "CS2204"
    assert "COMMITTEE" in types
    assert types["COMMITTEE"] == "Board of Studies"
    assert "ORGANIZATION" in types
    assert types["ORGANIZATION"] == "NAAC"

# ==========================================
# 4. ORCHESTRATOR EDGE CASES
# ==========================================

def test_orchestrator_empty_email_edge_case():
    """Test orchestrator handles empty or whitespace-only email without crashing."""
    orchestrator = AIOrchestrator()
    result = orchestrator.orchestrate(subject="", body="", sender="unknown@domain.com")
    
    assert result["output"].priority == "LOW"
    assert result["output"].category == "General"
    assert result["output"].deadline is None
    assert result["output"].meeting is None
    assert len(result["output"].action_items) == 0

def test_orchestrator_forwarded_email_chain():
    """Test orchestrator handles forwarded emails and extracts active deadline."""
    orchestrator = AIOrchestrator()
    subject = "Fwd: Urgent Question Paper Submission"
    body = (
        "---------- Forwarded message ---------\n"
        "From: Controller of Examinations <coe@university.edu>\n"
        "Date: Fri, Aug 28, 2026 at 10:15 AM\n"
        "Subject: Question Papers\n\n"
        "Dear Faculty, it is mandatory to submit manuscript question papers before September 15.\n"
    )
    result = orchestrator.orchestrate(subject=subject, body=body, sender="hod@university.edu", received_at=REF_DATE)
    
    output = result["output"]
    assert output.category == "Examination"
    assert output.deadline == "2026-09-15"
    assert output.priority == "HIGH"
    assert len(output.action_items) >= 1
