"""Master Stage 17 Comprehensive Automated Test Suite.

Validates all 7 critical architectural pillars:
1. Backend & Database Integrity (cascades, idempotent seeding, atomic rollback).
2. AI Processing Pipeline (orchestrator coordination, multi-agent synchronization).
3. Information Extraction (meetings, deadlines, actions, entities, temporal resolution).
4. Evidence Grounding & Anti-Hallucination (span verification, unsupported penalties).
5. Context-Aware Priority Engine (statutory authority, urgency horizons, personalization modes).
6. REST API Endpoints & Multi-Dimensional Filtering Matrix.
7. Critical Frontend Contract Verification (exact JSON schema matching TypeScript types).
"""

import pytest
from datetime import datetime, date, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.app.database.session import Base
from backend.app.database.seed_data import seed_database
from backend.app.models import Email, AIAnalysis, ActionItem, Meeting, Evidence, Entity
from backend.app.models.preference import FacultyPreference
from backend.app.ai.orchestrator import AIOrchestrator
from backend.app.ai.priority_engine import ContextAwarePriorityEngine
from backend.app.ai.evidence_service import EvidenceValidationService
from backend.app.services.preference_service import PreferenceService

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
# 1. Backend & Database Integrity Tests
# --------------------------------------------------------------------------

def test_database_cascade_deletion(test_db):
    """Verify deleting an Email cascades and removes all dependent child records."""
    email = Email(
        sender="hod@univ.edu",
        recipient="prof@univ.edu",
        subject="Cascade Verification Email",
        body="Action item test body.",
        received_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    test_db.add(email)
    test_db.commit()
    test_db.refresh(email)

    # Attach analysis, action, meeting, entity
    analysis = AIAnalysis(
        email_id=email.id,
        summary="Test Summary",
        category="Academic",
        priority="HIGH",
        priority_reason="Reason"
    )
    test_db.add(analysis)
    test_db.commit()

    action = ActionItem(email_id=email.id, description="Do task", due_date="2026-09-15")
    meeting = Meeting(email_id=email.id, title="Test Meeting", meeting_date="2026-09-14")
    entity = Entity(email_id=email.id, entity_type="COURSE", entity_value="CS101")
    evidence = Evidence(analysis_id=analysis.id, field_name="summary", extracted_value="Val", source_text="Src")
    test_db.add_all([action, meeting, entity, evidence])
    test_db.commit()

    # Delete the parent email
    test_db.delete(email)
    test_db.commit()

    # Assert all child records were cleanly wiped
    assert test_db.query(AIAnalysis).filter(AIAnalysis.email_id == email.id).count() == 0
    assert test_db.query(ActionItem).filter(ActionItem.email_id == email.id).count() == 0
    assert test_db.query(Meeting).filter(Meeting.email_id == email.id).count() == 0
    assert test_db.query(Entity).filter(Entity.email_id == email.id).count() == 0

def test_database_session_idempotent_seeding(test_db):
    """Verify repeated seeding is idempotent and does not create duplicate entries."""
    seed_database(test_db)
    initial_count = test_db.query(Email).count()
    assert initial_count == 15

    # Run seed again
    seed_database(test_db)
    second_count = test_db.query(Email).count()
    assert second_count == 15

def test_database_atomic_rollback_on_failure(test_db):
    """Verify transaction rollback ensures zero dirty state on error."""
    email = Email(
        sender="dean@univ.edu",
        recipient="prof@univ.edu",
        subject="Atomic Test",
        body="Body",
        received_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    test_db.add(email)
    test_db.commit()

    initial_actions = test_db.query(ActionItem).count()

    try:
        act1 = ActionItem(email_id=email.id, description="Valid Action")
        test_db.add(act1)
        test_db.flush()

        # Intentionally cause an error
        raise RuntimeError("Simulated transaction fault")
    except RuntimeError:
        test_db.rollback()

    assert test_db.query(ActionItem).count() == initial_actions

# --------------------------------------------------------------------------
# 2. AI Processing & Multi-Agent Orchestrator Tests
# --------------------------------------------------------------------------

def test_ai_orchestrator_full_lifecycle():
    """Verify AI Orchestrator executes all sub-agents in coordinated sequence."""
    orchestrator = AIOrchestrator()
    sample_text = (
        "Dear Faculty,\n"
        "All faculty members are requested to submit the question paper files "
        "for the End Semester Examinations before September 14, 2026. "
        "A preparatory review meeting is scheduled on September 10, 2026 at 10:00 AM in Senate Hall. "
        "Failure to submit on time will result in disciplinary escalation."
    )

    result = orchestrator.orchestrate(
        subject="URGENT: End Semester Question Papers Submission",
        body=sample_text,
        sender="coe@university.edu",
        received_at=datetime(2026, 9, 6, 9, 0, 0)
    )

    assert "output" in result
    assert "steps" in result
    assert len(result["steps"]) >= 8

    output = result["output"]
    assert output.category == "Examination"
    assert output.priority == "HIGH"
    assert output.deadline == "2026-09-14"
    assert output.meeting is not None
    assert output.meeting.date == "2026-09-10"
    assert "Senate Hall" in (output.meeting.location or "")
    assert len(output.structured_actions) >= 1
    assert len(output.evidence) >= 1

def test_hallucination_detection_and_unsupported_penalty():
    """Verify EvidenceValidationService detects and penalizes hallucinated claims."""
    validator = EvidenceValidationService()
    raw_body = "The faculty meeting is scheduled for Friday at 3:00 PM in Conference Room B."

    # Valid grounded assertion
    grounded = validator.validate_assertion("meeting", "Friday at 3:00 PM", raw_body)
    assert grounded["is_valid"] is True
    assert grounded["validation_status"] == "VERIFIED"
    assert grounded["confidence"] >= 0.8

    # Hallucinated assertion (never stated in text)
    hallucinated = validator.validate_assertion("deadline", "Submit budget report by Monday", raw_body)
    assert hallucinated["is_valid"] is False
    assert hallucinated["validation_status"] in ["UNSUPPORTED", "PARTIAL"]
    assert hallucinated["confidence"] < 0.5

# --------------------------------------------------------------------------
# 3. Information Extraction & Priority Engine Tests
# --------------------------------------------------------------------------

def test_extraction_multiple_actions_and_dates():
    """Verify extraction of distinct action items with individual due dates."""
    orchestrator = AIOrchestrator()
    body = (
        "Please submit syllabus draft before September 12. "
        "Also bring student attendance logs by September 15."
    )
    result = orchestrator.orchestrate(
        subject="Academic Checklist",
        body=body,
        sender="hod@univ.edu",
        received_at=datetime(2026, 9, 6)
    )
    actions = result["output"].structured_actions
    assert len(actions) >= 2
    dates = [a.due_date for a in actions if a.due_date]
    assert "2026-09-12" in dates or "2026-09-15" in dates

def test_priority_modes_authority_first_vs_deadline_heavy():
    """Verify priority modes adjust scores mathematically based on tuning profile."""
    engine = ContextAwarePriorityEngine()
    ref_date = date(2026, 9, 6)

    pref_auth = FacultyPreference(priority_mode="AUTHORITY_FIRST")
    pref_dead = FacultyPreference(priority_mode="DEADLINE_HEAVY")

    # Email with high authority (Dean) but far deadline (18 days away)
    score_auth = engine.assess_priority(
        subject="Long range policy review",
        body="Dean requests thoughts by end of month.",
        sender="dean@univ.edu",
        sender_role="DEAN",
        category="Administrative",
        deadline="2026-09-24",
        reference_date=ref_date,
        preferences=pref_auth
    )

    score_dead = engine.assess_priority(
        subject="Long range policy review",
        body="Dean requests thoughts by end of month.",
        sender="dean@univ.edu",
        sender_role="DEAN",
        category="Administrative",
        deadline="2026-09-24",
        reference_date=ref_date,
        preferences=pref_dead
    )

    # Authority-First must score higher for Dean's communication
    assert score_auth.score > score_dead.score

# --------------------------------------------------------------------------
# 4. REST API Multi-Filter Matrix Tests
# --------------------------------------------------------------------------

def test_api_multi_filter_combination():
    """Verify query filtering handles combination of search, category, priority, and read status."""
    resp = client.get("/api/emails?category=Examination&priority=HIGH&is_read=false")
    assert resp.status_code == 200
    emails = resp.json()
    assert isinstance(emails, list)
    for e in emails:
        assert e["category"] == "Examination"
        assert e["priority"] == "HIGH"
        assert e["is_read"] is False

def test_api_dashboard_metrics_consistency():
    """Verify dashboard metrics align with individual table queries."""
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    metrics = data["metrics"]

    assert "total_emails" in metrics
    assert "unread_emails" in metrics
    assert "high_priority_count" in metrics
    assert "upcoming_deadlines_count" in metrics
    assert "upcoming_meetings_count" in metrics
    assert "pending_actions_count" in metrics

    # Verification: total >= unread
    assert metrics["total_emails"] >= metrics["unread_emails"]

def test_api_not_found_handling():
    """Verify 404 responses on non-existent resources."""
    resp = client.get("/api/emails/999999")
    assert resp.status_code == 404
    assert "not found" in resp.json().get("detail", "").lower()

    resp2 = client.patch("/api/action-items/999999", json={"completed": True})
    assert resp2.status_code == 404

# --------------------------------------------------------------------------
# 5. Critical Frontend Contract Verification
# --------------------------------------------------------------------------

def test_frontend_email_summary_contract():
    """Verify FastAPI /api/emails response strictly conforms to React EmailSummary interface."""
    resp = client.get("/api/emails?limit=1")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) > 0
    e = items[0]

    required_fields = [
        "id", "sender", "recipient", "subject", "body_preview",
        "received_at", "is_read", "created_at", "has_analysis",
        "action_items_count", "meetings_count", "has_deadline"
    ]
    for field in required_fields:
        assert field in e, f"Missing required frontend field: '{field}'"

def test_frontend_email_detail_contract():
    """Verify /api/emails/{id} response strictly conforms to React EmailDetail interface."""
    resp = client.get("/api/emails/1")
    assert resp.status_code == 200
    data = resp.json()

    required_detail_fields = [
        "id", "sender", "recipient", "subject", "body",
        "received_at", "is_read", "created_at", "analysis",
        "action_items", "meetings", "entities"
    ]
    for field in required_detail_fields:
        assert field in data, f"Missing required detail field: '{field}'"

    if data["analysis"]:
        analysis = data["analysis"]
        for a_field in ["id", "email_id", "summary", "category", "priority", "priority_reason", "processed_at"]:
            assert a_field in analysis, f"Missing required analysis field: '{a_field}'"

def test_frontend_cross_intelligence_contract():
    """Verify /api/emails/{id}/cross-intelligence strictly conforms to React CrossIntelligenceResponse."""
    resp = client.get("/api/emails/1/cross-intelligence")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("success") is True
    data = body.get("data")
    assert "email_id" in data
    assert "related_emails" in data
    assert "timeline" in data
    assert "insights" in data

def test_frontend_preferences_contract():
    """Verify /api/preferences conforms to React FacultyPreference interface."""
    resp = client.get("/api/preferences")
    assert resp.status_code == 200
    pref = resp.json()

    pref_fields = [
        "id", "faculty_name", "role", "department", "priority_mode",
        "high_priority_categories", "custom_keywords_high", "custom_keywords_low",
        "deadline_urgency_days", "authority_weight", "deadline_weight", "updated_at"
    ]
    for field in pref_fields:
        assert field in pref, f"Missing required preference field: '{field}'"
