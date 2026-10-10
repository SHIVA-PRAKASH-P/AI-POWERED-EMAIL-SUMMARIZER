import pytest
from datetime import datetime, date
from backend.app.ai.priority_engine import ContextAwarePriorityEngine
from backend.app.schemas.priority_schema import PriorityAssessment

# Fixed reference date: Sunday, September 6, 2026
REF_DATE = datetime(2026, 9, 6, 9, 0, 0)

# =======================================================
# 1. SCENARIO TESTING FOR MULTI-FACTOR PRIORITY ENGINE
# =======================================================

def test_statutory_examination_priority():
    """Scenario 1: Controller of Examinations directive with mandatory language."""
    engine = ContextAwarePriorityEngine()
    assessment = engine.assess_priority(
        subject="Confidential: Setting of Question Papers for End Semester Examinations",
        body="It is strictly mandatory to submit manuscript question papers before September 15 to the COE Confidential Section.",
        sender="coe@university.edu",
        sender_role="COE",
        category="Examination",
        deadline="2026-09-15",
        reference_date=REF_DATE
    )

    assert isinstance(assessment, PriorityAssessment)
    assert assessment.priority == "HIGH"
    assert assessment.mandatory is True
    assert assessment.examination_context is True
    assert assessment.sender_authority == "STATUTORY"
    assert assessment.deadline_proximity in ["MEDIUM", "HIGH"]
    assert assessment.score >= 8.0
    assert "statutory directive from coe" in assessment.priority_reason.lower()
    assert "mandatory institutional language" in assessment.priority_reason.lower()

def test_hod_marks_submission_with_meeting_priority():
    """Scenario 2: HOD directive with approaching deadline and review meeting."""
    engine = ContextAwarePriorityEngine()
    assessment = engine.assess_priority(
        subject="Internal Assessment Marks Submission",
        body="All members are requested to submit internal assessment marks before September 10. A review meeting will be conducted on September 8 at 10 AM in the Seminar Hall.",
        sender="hod.cse@university.edu",
        sender_role="HOD",
        category="Academic",
        deadline="2026-09-10",
        meeting={"date": "2026-09-08", "time": "10:00", "location": "Seminar Hall"},
        actions_count=2,
        reference_date=REF_DATE
    )

    assert assessment.priority == "HIGH"
    assert assessment.academic_context is True
    assert assessment.sender_authority == "DEPARTMENTAL"
    assert assessment.meeting_proximity in ["IMMEDIATE", "APPROACHING"]
    assert "departmental directive from hod" in assessment.priority_reason.lower()
    assert "meeting" in assessment.priority_reason.lower()

def test_dean_naac_accreditation_priority():
    """Scenario 3: Dean Academics NAAC file audit with compliance indicators."""
    engine = ContextAwarePriorityEngine()
    assessment = engine.assess_priority(
        subject="Urgent: NAAC Peer Team Visit Preparation & File Audit",
        body="A mandatory file audit will be held on September 9 at 2:30 PM in the Main Board Room. Course files and compliance bylaws must be updated.",
        sender="dean.academics@university.edu",
        sender_role="DEAN",
        category="Administrative",
        deadline="2026-09-09",
        meeting={"date": "2026-09-09", "time": "14:30", "location": "Main Board Room"},
        actions_count=1,
        reference_date=REF_DATE
    )

    assert assessment.priority == "HIGH"
    assert assessment.sender_authority == "STATUTORY"
    assert assessment.urgency_language is True
    assert assessment.mandatory is True

def test_student_medical_leave_priority():
    """Scenario 4: Student medical leave appeal with discretionary scheduling."""
    engine = ContextAwarePriorityEngine()
    assessment = engine.assess_priority(
        subject="Medical Leave Certificate & Request for Re-test",
        body="Student requests a make-up re-test for Quiz 1 before September 12 following hospital discharge.",
        sender="student@university.edu",
        sender_role="STUDENT",
        category="Student",
        deadline="2026-09-12",
        actions_count=1,
        reference_date=REF_DATE
    )

    assert assessment.priority == "MEDIUM"
    assert assessment.sender_authority == "STUDENT"
    assert "approaching deadline" in assessment.priority_reason.lower()

def test_library_book_indent_routine_priority():
    """Scenario 5: Routine resource recommendation with distant deadline (>20 days)."""
    engine = ContextAwarePriorityEngine()
    assessment = engine.assess_priority(
        subject="Department Library: Book Purchase Indents",
        body="The library advisory committee invites book purchase indents before September 30.",
        sender="librarian@university.edu",
        sender_role="ROUTINE",
        category="Department",
        deadline="2026-09-30",
        reference_date=REF_DATE
    )

    assert assessment.priority in ["LOW", "MEDIUM"]
    assert assessment.deadline_proximity == "LOW"
    assert assessment.mandatory is False

def test_wifi_maintenance_informational_priority():
    """Scenario 6: Nocturnal maintenance alert without faculty action."""
    engine = ContextAwarePriorityEngine()
    assessment = engine.assess_priority(
        subject="Scheduled Maintenance: Core Campus Wi-Fi",
        body="Campus Wi-Fi will be intermittently unavailable from 11 PM to 4 AM for routine firmware upgrades.",
        sender="it.support@university.edu",
        sender_role="ROUTINE",
        category="General",
        deadline=None,
        meeting=None,
        actions_count=0,
        reference_date=REF_DATE
    )

    assert assessment.priority == "LOW"
    assert assessment.required_action is False
    assert "routine priority" in assessment.priority_reason.lower()

def test_immediate_deadline_proximity_elevation():
    """Scenario 7: Routine sender but deadline is tomorrow (<= 2 days) -> elevated priority."""
    engine = ContextAwarePriorityEngine()
    assessment = engine.assess_priority(
        subject="Urgent Reminder: Upload Student Attendance",
        body="Please upload attendance today itself. Deadline is tomorrow September 7.",
        sender="faculty.peer@university.edu",
        sender_role="ROUTINE",
        category="Academic",
        deadline="2026-09-07",
        actions_count=1,
        reference_date=REF_DATE
    )

    assert assessment.deadline_proximity == "IMMEDIATE"
    assert assessment.urgency_language is True
    assert assessment.priority in ["HIGH", "MEDIUM"]
    assert assessment.score >= 7.0

def test_consequence_indicators():
    """Scenario 8: Presence of explicit compliance consequences."""
    engine = ContextAwarePriorityEngine()
    assessment = engine.assess_priority(
        subject="Non-Compliance Notice: Self-Appraisal Submission",
        body="Failure to submit APAR by September 15 may result in promotion withheld under compliance bylaws.",
        sender="registrar@university.edu",
        sender_role="REGISTRAR",
        category="Administrative",
        deadline="2026-09-15",
        actions_count=1,
        reference_date=REF_DATE
    )

    assert assessment.consequence_indicators is True
    assert assessment.priority == "HIGH"
    assert "consequence" in assessment.priority_reason.lower() or "statutory" in assessment.priority_reason.lower()


# =======================================================
# 2. QUICK PRIORITY FIX TESTS — COLLEGE GMAIL SCENARIOS
# =======================================================

def test_extension_till_imminent_deadline_elevated_priority():
    """Scenario 9: 'Extension till 08.09.2026' receives elevated priority when deadline is imminent."""
    engine = ContextAwarePriorityEngine()
    # Reference date is 2026-09-08 (deadline is today -> imminent)
    ref_date = datetime(2026, 9, 8, 9, 0, 0)
    assessment = engine.assess_priority(
        subject="Scholarship Applications: Extension till 08.09.2026",
        body="All eligible candidates please note: Extension till 08.09.2026 for document submission.",
        sender="scholarships@bitsathy.ac.in",
        sender_role="ROUTINE",
        category="Academic",
        reference_date=ref_date
    )

    # Must NOT be classified LOW merely because it is routine institutional communication
    assert assessment.priority != "LOW"
    assert assessment.priority in ["HIGH", "MEDIUM"]
    assert assessment.deadline_proximity == "IMMEDIATE"
    assert assessment.urgency_language is True


def test_by_tomorrow_mandatory_action_elevated_priority():
    """Scenario 10: 'by tomorrow' + mandatory action receives elevated priority (HIGH)."""
    engine = ContextAwarePriorityEngine()
    ref_date = datetime(2026, 9, 6, 9, 0, 0)
    assessment = engine.assess_priority(
        subject="Mandatory Course Plan Submission",
        body="It is strictly mandatory to submit the updated course plan by tomorrow without fail.",
        sender="academic.coordinator@bitsathy.ac.in",
        sender_role="ROUTINE",
        category="Academic",
        reference_date=ref_date
    )

    # Elevated priority with mandatory action and imminent tomorrow deadline
    assert assessment.priority == "HIGH"
    assert assessment.mandatory is True
    assert assessment.urgency_language is True
    assert assessment.deadline_proximity == "IMMEDIATE"


def test_routine_mandatory_announcement_without_imminent_deadline_not_high():
    """Scenario 11: Routine 'mandatory' announcement without an imminent deadline must NOT become HIGH."""
    engine = ContextAwarePriorityEngine()
    ref_date = datetime(2026, 9, 6, 9, 0, 0)
    assessment = engine.assess_priority(
        subject="Mandatory Notice: Annual Campus Cleanliness and Energy Conservation Drive",
        body="It is strictly mandatory for all faculty and staff to observe the energy conservation protocols across campus buildings.",
        sender="campus.estate@bitsathy.ac.in",
        sender_role="ROUTINE",
        category="General",
        deadline=None,
        reference_date=ref_date
    )

    # Routine mandatory announcements without an imminent deadline should NOT automatically become HIGH
    assert assessment.mandatory is True
    assert assessment.deadline_proximity == "NONE"
    assert assessment.priority != "HIGH"
    assert assessment.priority in ["MEDIUM", "LOW"]


# =======================================================
# 3. DAILYNEWS & WORD OF THE DAY SENDER OVERRIDE TESTS
# =======================================================

def test_dailynews_sender_medium_by_default():
    """Scenario 12: Emails from dailynews@bitsathy.ac.in are MEDIUM by default, overriding keywords."""
    engine = ContextAwarePriorityEngine()
    assessment = engine.assess_priority(
        subject="BIT Campus Daily Pulse & Announcements - September 8, 2026",
        body="Today's campus circular: It is mandatory for all students to review today's seminar schedules and library timings.",
        sender="dailynews@bitsathy.ac.in",
        sender_role="ROUTINE",
        category="General",
        reference_date=datetime(2026, 9, 8, 9, 0, 0)
    )

    # Must be MEDIUM by default despite generic keywords like "today" and "mandatory"
    assert assessment.priority == "MEDIUM"
    assert "dailynews@bitsathy.ac.in" in assessment.priority_reason.lower()


def test_dailynews_word_of_the_day_low_priority():
    """Scenario 13: 'Word of the Day' from dailynews@bitsathy.ac.in is strictly LOW, overriding keywords."""
    engine = ContextAwarePriorityEngine()
    assessment = engine.assess_priority(
        subject="Word of the Day: Ubiquitous [08.09.2026]",
        body="Today's word of the day is Ubiquitous. It is mandatory for all students to submit vocabulary notes today without fail.",
        sender="dailynews@bitsathy.ac.in",
        sender_role="ROUTINE",
        category="General",
        reference_date=datetime(2026, 9, 8, 9, 0, 0)
    )

    # Must be strictly LOW overriding 'today', 'mandatory', 'without fail', 'submit'
    assert assessment.priority == "LOW"
    assert "word of the day" in assessment.priority_reason.lower()


# =======================================================
# 4. CONTEXT-AWARE AI CLASSIFICATION TESTS (10 REQUIREMENTS)
# =======================================================

from unittest.mock import MagicMock
from backend.app.schemas.priority_schema import AIPriorityResult
from backend.app.ai.priority_service import PriorityService
from backend.app.ai.llm_service import LLMService

def test_mandatory_academic_submission_imminent_deadline_high():
    """Requirement 1: Mandatory academic submission with imminent deadline -> HIGH."""
    engine = ContextAwarePriorityEngine()
    ref_date = datetime(2026, 9, 8, 9, 0, 0)
    assessment = engine.assess_priority(
        subject="Mandatory Internal Assessment Marks Submission",
        body="It is strictly mandatory for all faculty to submit the consolidated internal assessment marks by tomorrow without fail.",
        sender="coe@bitsathy.ac.in",
        sender_role="COE",
        category="Examination",
        deadline="2026-09-09",
        actions_count=1,
        reference_date=ref_date
    )

    assert assessment.priority == "HIGH"
    assert assessment.confidence >= 0.85
    assert len(assessment.reason) > 0
    assert "high priority" in assessment.reason.lower()


def test_mandatory_marks_verification_without_fail_high():
    """Requirement 2: Mandatory marks verification ('Verify PT-1 marks without fail') -> HIGH."""
    engine = ContextAwarePriorityEngine()
    ref_date = datetime(2026, 9, 8, 9, 0, 0)
    assessment = engine.assess_priority(
        subject="Urgent: Verify PT-1 Marks Without Fail",
        body="All faculty handling second year courses must verify PT-1 marks in the academic portal immediately today without fail.",
        sender="academic.audit@bitsathy.ac.in",
        sender_role="ROUTINE",
        category="Academic",
        deadline="2026-09-08",
        actions_count=1,
        reference_date=ref_date
    )

    assert assessment.priority == "HIGH"
    assert assessment.mandatory is True
    assert "verification" in assessment.reason.lower() or "marks" in assessment.reason.lower()


def test_voluntary_event_registration_deadline_medium():
    """Requirement 3: Voluntary event with registration deadline -> MEDIUM (never HIGH)."""
    engine = ContextAwarePriorityEngine()
    ref_date = datetime(2026, 9, 8, 9, 0, 0)
    assessment = engine.assess_priority(
        subject="Vinayagar Chathurthi Programme - Special Celebration",
        body="The cultural club is organizing a Vinayagar Chathurthi programme. Interested students may register by 4:30 PM today. Food will be provided.",
        sender="cultural.club@bitsathy.ac.in",
        sender_role="ROUTINE",
        category="Event",
        deadline="2026-09-08",
        actions_count=1,
        reference_date=ref_date
    )

    # Must be MEDIUM, NOT HIGH, because participation is voluntary despite the imminent 4:30 PM deadline
    assert assessment.priority == "MEDIUM"
    assert "voluntary" in assessment.reason.lower() or "no academic consequence" in assessment.reason.lower()


def test_daily_institutional_news_update_medium():
    """Requirement 4: Daily institutional news / bulletin -> MEDIUM."""
    engine = ContextAwarePriorityEngine()
    ref_date = datetime(2026, 9, 8, 9, 0, 0)
    assessment = engine.assess_priority(
        subject="Campus News & Daily Bulletin - September 8, 2026",
        body="Here is today's overview of campus activities, seminar venue updates, and placement drive highlights.",
        sender="campus.relations@bitsathy.ac.in",
        sender_role="ROUTINE",
        category="General",
        reference_date=ref_date
    )

    assert assessment.priority == "MEDIUM"
    assert assessment.mandatory is False


def test_word_of_the_day_routine_informational_low():
    """Requirement 5: Word of the Day routine informational content -> LOW."""
    engine = ContextAwarePriorityEngine()
    ref_date = datetime(2026, 9, 8, 9, 0, 0)
    assessment = engine.assess_priority(
        subject="Word of the Day: Ephemeral [08.09.2026]",
        body="Meaning: Lasting for a very short time. Example sentence: The ephemeral nature of fashion trends.",
        sender="english.club@bitsathy.ac.in",
        sender_role="ROUTINE",
        category="General",
        reference_date=ref_date
    )

    assert assessment.priority == "LOW"
    assert "word of the day" in assessment.reason.lower() or "educational" in assessment.reason.lower()


def test_routine_announcement_containing_mandatory_not_high():
    """Requirement 6: Routine announcement containing 'mandatory' without urgent action/consequence -> NOT HIGH (MEDIUM)."""
    engine = ContextAwarePriorityEngine()
    ref_date = datetime(2026, 9, 8, 9, 0, 0)
    assessment = engine.assess_priority(
        subject="Mandatory Annual Campus Cleanliness and Energy Conservation Notice",
        body="It is strictly mandatory for all faculty, staff, and students to adhere to energy conservation protocols when vacating lecture halls.",
        sender="campus.admin@bitsathy.ac.in",
        sender_role="ROUTINE",
        category="General",
        deadline=None,
        actions_count=0,
        reference_date=ref_date
    )

    assert assessment.priority != "HIGH"
    assert assessment.priority == "MEDIUM"
    assert "protocol" in assessment.reason.lower() or "scope" in assessment.reason.lower() or "medium" in assessment.reason.lower()


def test_contextual_meaning_of_today_keyword():
    """Requirement 7: Same keyword ('today') in different contexts yields different priorities."""
    engine = ContextAwarePriorityEngine()
    ref_date = datetime(2026, 9, 8, 9, 0, 0)

    # 7a: Voluntary event with deadline today -> MEDIUM
    voluntary_assessment = engine.assess_priority(
        subject="Cultural Fest Auditions",
        body="Interested students may register by 4:30 PM today for the classical music auditions.",
        sender="music.society@bitsathy.ac.in",
        sender_role="ROUTINE",
        category="Event",
        deadline="2026-09-08",
        actions_count=1,
        reference_date=ref_date
    )
    assert voluntary_assessment.priority == "MEDIUM"

    # 7b: Mandatory academic compliance with deadline today -> HIGH
    mandatory_assessment = engine.assess_priority(
        subject="Urgent: Verify and Submit PT-1 Marks Today Without Fail",
        body="All course coordinators must verify and submit PT-1 marks today without fail. Results will be published tonight.",
        sender="coe@bitsathy.ac.in",
        sender_role="COE",
        category="Examination",
        deadline="2026-09-08",
        actions_count=1,
        reference_date=ref_date
    )
    assert mandatory_assessment.priority == "HIGH"


def test_primary_ai_classification_success_path():
    """Requirement 8a: Primary AI classifier returns valid result; keyword/fallback logic is bypassed completely."""
    mock_llm = MagicMock(spec=LLMService)
    mock_llm.is_configured = True
    mock_llm.provider = "gemini"
    mock_llm.classify_priority.return_value = AIPriorityResult(
        priority="HIGH",
        confidence=0.98,
        reason="Context-Aware AI: Urgent statutory directive from COE with immediate deadline."
    )

    engine = ContextAwarePriorityEngine(llm_service=mock_llm)
    assessment = engine.assess_priority(
        subject="Some Subject",
        body="Some Body",
        sender="someone@university.edu"
    )

    assert mock_llm.classify_priority.called
    assert assessment.priority == "HIGH"
    assert assessment.confidence == 0.98
    assert assessment.reason == "Context-Aware AI: Urgent statutory directive from COE with immediate deadline."
    assert assessment.priority_reason == assessment.reason


def test_primary_ai_classification_fallback_on_error():
    """Requirement 8b: When AI classifier raises exception, contextual semantic fallback takes over gracefully."""
    mock_llm = MagicMock(spec=LLMService)
    mock_llm.is_configured = True
    mock_llm.provider = "gemini"
    mock_llm.classify_priority.side_effect = RuntimeError("LLM API request timeout")

    engine = ContextAwarePriorityEngine(llm_service=mock_llm)
    ref_date = datetime(2026, 9, 8, 9, 0, 0)
    assessment = engine.assess_priority(
        subject="Vinayagar Chathurthi Programme",
        body="Interested students may register by 4:30 PM today.",
        sender="cultural@bitsathy.ac.in",
        category="Event",
        reference_date=ref_date
    )

    assert mock_llm.classify_priority.called
    # Fallback took over and recognized voluntary event
    assert assessment.priority == "MEDIUM"
    assert assessment.confidence > 0
    assert len(assessment.reason) > 0


def test_structured_ai_priority_output_schema():
    """Requirement 9: Structured output schema conforms to AIPriorityResult and PriorityAssessment contracts."""
    res = AIPriorityResult(
        priority="MEDIUM",
        confidence=0.89,
        reason="Actionable faculty notification with moderate urgency."
    )
    assert res.priority == "MEDIUM"
    assert res.confidence == 0.89
    assert res.reason == "Actionable faculty notification with moderate urgency."

    assessment = PriorityAssessment(
        mandatory=False,
        urgency_language=True,
        deadline_proximity="APPROACHING",
        sender_authority="ROUTINE",
        academic_context=True,
        examination_context=False,
        required_action=True,
        meeting_proximity="NONE",
        consequence_indicators=False,
        score=5.5,
        priority="MEDIUM",
        priority_reason="Medium priority: actionable correspondence.",
        confidence=0.89,
        reason="Medium priority: actionable correspondence."
    )
    assert assessment.confidence == 0.89
    assert assessment.reason == "Medium priority: actionable correspondence."
    assert assessment.priority_reason == assessment.reason


def test_priority_service_delegates_to_context_aware_engine():
    """Requirement 10: PriorityService delegates directly to ContextAwarePriorityEngine for unified evaluation."""
    service = PriorityService()

    # Case A: Voluntary event
    res_voluntary = service.evaluate_priority(
        subject="Annual Gala",
        body="Interested students may register by 4:30 PM.",
        category="Event"
    )
    assert res_voluntary["priority"] == "MEDIUM"

    # Case B: Word of the Day
    res_wod = service.evaluate_priority(
        subject="Word of the Day: Resilient",
        body="Today's vocabulary feature.",
        category="General"
    )
    assert res_wod["priority"] == "LOW"



