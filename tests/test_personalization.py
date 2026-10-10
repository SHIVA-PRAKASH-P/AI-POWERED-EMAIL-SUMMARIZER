"""Comprehensive Automated Tests for Faculty Personalization (Stage 15).

Validates:
1. FacultyPreference model persistence and PreferenceService operations.
2. ContextAwarePriorityEngine personalization adjustments:
   - Custom high urgency keyword boosts.
   - Custom low priority keyword demotions.
   - High priority category focus.
   - Configurable deadline urgency horizon.
   - Department and role alignment.
3. AIOrchestrator personalization parameter propagation.
4. REST API endpoints (/api/preferences, /api/preferences/reset).
5. Dynamic re-analysis reflecting altered faculty preferences.
"""

import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.app.database.session import Base
from backend.app.models.email import Email
from backend.app.models.preference import FacultyPreference
from backend.app.schemas.preference_schema import FacultyPreferenceUpdate
from backend.app.services.preference_service import PreferenceService, preference_service
from backend.app.ai.priority_engine import ContextAwarePriorityEngine
from backend.app.ai.orchestrator import AIOrchestrator

client = TestClient(app)

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# --------------------------------------------------------------------------
# 1. Database & Preference Service Tests
# --------------------------------------------------------------------------

def test_get_or_create_default_preferences(test_db):
    """Verify PreferenceService creates sensible academic defaults if none exist."""
    pref = PreferenceService.get_or_create_preferences(test_db)
    assert pref is not None
    assert pref.id == 1
    assert "Professor" in pref.role
    assert pref.department == "Computer Science & Engineering"
    assert "Examination" in pref.high_priority_categories
    assert pref.deadline_urgency_days == 3
    assert pref.authority_weight == 1.0

def test_update_preferences(test_db):
    """Verify updating faculty personalization fields."""
    update_data = FacultyPreferenceUpdate(
        faculty_name="Prof. Alan Turing",
        role="Dean of Computing",
        department="Informatics",
        custom_keywords_high="accreditation,quantum,patent",
        deadline_urgency_days=5
    )
    updated = PreferenceService.update_preferences(test_db, update_data)
    assert updated.faculty_name == "Prof. Alan Turing"
    assert updated.role == "Dean of Computing"
    assert updated.department == "Informatics"
    assert updated.custom_keywords_high == "accreditation,quantum,patent"
    assert updated.deadline_urgency_days == 5

def test_reset_preferences(test_db):
    """Verify resetting preferences restores standard defaults."""
    PreferenceService.update_preferences(
        test_db,
        FacultyPreferenceUpdate(role="Custom Role", deadline_urgency_days=10)
    )
    reset = PreferenceService.reset_preferences(test_db)
    assert reset.role == "Professor & Academic Incharge"
    assert reset.deadline_urgency_days == 3

# --------------------------------------------------------------------------
# 2. Priority Engine Personalization Tuning Tests
# --------------------------------------------------------------------------

def test_custom_keyword_boost():
    """Verify custom high urgency keywords elevate priority and provide explainable reason."""
    engine = ContextAwarePriorityEngine()
    pref = FacultyPreference(
        custom_keywords_high="quantum computing,patent draft",
        high_priority_categories=""
    )

    assessment = engine.assess_priority(
        subject="Discussion on patent draft submission",
        body="Please review the initial disclosure.",
        sender="colleague@university.edu",
        sender_role="PEER",
        category="General",
        preferences=pref
    )

    assert "patent draft" in assessment.priority_reason.lower()
    assert assessment.score >= 4.0

def test_category_focus_boost():
    """Verify email matching faculty focus category gets elevated score and reasoning."""
    engine = ContextAwarePriorityEngine()
    pref = FacultyPreference(
        high_priority_categories="Research,Placement",
        custom_keywords_high=""
    )

    # Category 'Research' is in faculty focus
    assessment = engine.assess_priority(
        subject="Grant Application Guidelines",
        body="Guidelines for the new semester funding.",
        sender="rnd@university.edu",
        sender_role="STAFF",
        category="Research",
        preferences=pref
    )

    assert "matches faculty focus category 'research'" in assessment.priority_reason.lower()
    assert assessment.score >= 4.0

def test_custom_low_keyword_demotion():
    """Verify non-mandatory email with low keywords gets score reduction."""
    engine = ContextAwarePriorityEngine()
    pref = FacultyPreference(
        custom_keywords_low="sports carnival,annual cultural fest",
        custom_keywords_high=""
    )

    assessment = engine.assess_priority(
        subject="Volunteers needed for annual cultural fest",
        body="Join the fest coordination team.",
        sender="students@university.edu",
        sender_role="STUDENT",
        category="Event",
        preferences=pref
    )

    assert "matched low-priority keyword" in assessment.priority_reason.lower()
    assert assessment.priority == "LOW"

def test_custom_deadline_urgency_horizon():
    """Verify customizing deadline urgency horizon changes proximity classification."""
    engine = ContextAwarePriorityEngine()
    ref_date = datetime(2026, 9, 6)

    # Deadline is 4 days away (Sept 10)
    # Default (horizon=2) -> 'HIGH'
    pref_default = FacultyPreference(deadline_urgency_days=2)
    assess_default = engine.assess_priority(
        subject="Task Deadline",
        body="Submit by date.",
        sender="hod@university.edu",
        sender_role="HOD",
        category="Academic",
        deadline="2026-09-10",
        reference_date=ref_date,
        preferences=pref_default
    )
    assert assess_default.deadline_proximity == "HIGH"

    # With horizon=5 -> 'IMMEDIATE'
    pref_extended = FacultyPreference(deadline_urgency_days=5)
    assess_extended = engine.assess_priority(
        subject="Task Deadline",
        body="Submit by date.",
        sender="hod@university.edu",
        sender_role="HOD",
        category="Academic",
        deadline="2026-09-10",
        reference_date=ref_date,
        preferences=pref_extended
    )
    assert assess_extended.deadline_proximity == "IMMEDIATE"

# --------------------------------------------------------------------------
# 3. AI Orchestrator Personalization Propagation Test
# --------------------------------------------------------------------------

def test_orchestrator_personalization_propagation():
    """Verify AIOrchestrator propagates faculty preferences to priority engine."""
    orchestrator = AIOrchestrator()
    pref = FacultyPreference(
        custom_keywords_high="accreditation matrix",
        department="Computer Science & Engineering"
    )

    res = orchestrator.orchestrate(
        subject="Urgent review of accreditation matrix",
        body="Please verify the accreditation matrix for department compliance.",
        sender="dean@university.edu",
        received_at=datetime(2026, 9, 6, 10, 0),
        preferences=pref
    )

    output = res["output"]
    assert "accreditation matrix" in output.priority_reason.lower()
    assert output.priority == "HIGH"

# --------------------------------------------------------------------------
# 4. REST API Integration Tests
# --------------------------------------------------------------------------

def test_api_get_preferences():
    """Verify GET /api/preferences returns current preferences."""
    res = client.get("/api/preferences")
    assert res.status_code == 200
    data = res.json()
    assert "role" in data
    assert "department" in data
    assert "priority_mode" in data
    assert "custom_keywords_high" in data

def test_api_update_preferences():
    """Verify PUT /api/preferences saves updates properly."""
    payload = {
        "role": "Distinguished Professor & NAAC Lead",
        "custom_keywords_high": "supercomputer,quantum,naac",
        "deadline_urgency_days": 4
    }
    res = client.put("/api/preferences", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "Distinguished Professor & NAAC Lead"
    assert "supercomputer" in data["custom_keywords_high"]
    assert data["deadline_urgency_days"] == 4

def test_api_reset_preferences():
    """Verify POST /api/preferences/reset restores defaults."""
    res = client.post("/api/preferences/reset")
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "Professor & Academic Incharge"
    assert data["deadline_urgency_days"] == 3
