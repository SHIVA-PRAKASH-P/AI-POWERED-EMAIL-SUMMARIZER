import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from backend.main import app
from backend.app.ai.mock_service import MockAIService
from backend.app.ai.llm_service import LLMService
from backend.app.schemas.ai_schema import AIServiceOutput
from backend.app.database.session import SessionLocal, reset_db
from backend.app.database.seed_data import seed_database
from backend.app.models import Email, AIAnalysis, ActionItem, Meeting

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database is seeded for AI tests."""
    reset_db()
    db = SessionLocal()
    seed_database(db)
    db.close()

def test_mock_ai_flagship_email():
    """Verify MockAIService outputs exact schema matching Section 5 and Section 41 specifications."""
    service = MockAIService()
    subject = "Internal Assessment Marks Submission"
    body = (
        "Dear Faculty, all members are requested to submit the internal assessment marks before September 10. "
        "A review meeting will be conducted on September 8 at 10 AM in the Seminar Hall. "
        "Please bring the updated mark sheet and student attendance logs."
    )
    result = service.analyze_email(subject=subject, body=body, sender="hod.cse@university.edu")

    assert isinstance(result, AIServiceOutput)
    assert "Internal assessment marks" in result.summary or "internal assessment marks" in result.summary
    assert result.category == "Academic"
    assert result.priority == "HIGH"
    assert "Mandatory" in result.priority_reason
    assert result.deadline == "2026-09-10"
    assert result.meeting is not None
    assert result.meeting.title == "Department Review Meeting"
    assert result.meeting.date == "2026-09-08"
    assert result.meeting.time == "10:00"
    assert result.meeting.location == "Seminar Hall"
    assert len(result.action_items) >= 2
    assert len(result.evidence) >= 2
    assert any(e.field_name == "deadline" and "2026-09-10" in e.extracted_value for e in result.evidence)

def test_mock_ai_examination_email():
    """Verify MockAIService extraction for examination scenario."""
    service = MockAIService()
    subject = "Confidential: Setting of Question Papers for End Semester Examinations"
    body = "Please submit manuscript question papers before September 15 to the COE office."
    result = service.analyze_email(subject=subject, body=body, sender="coe@university.edu")

    assert result.category == "Examination"
    assert result.priority == "HIGH"
    assert result.deadline == "2026-09-15"
    assert len(result.action_items) >= 1

def test_mock_ai_student_email():
    """Verify MockAIService extraction for student leave scenario."""
    service = MockAIService()
    subject = "Medical Leave Certificate & Request for Re-test"
    body = "Requesting re-test before September 12 following viral fever."
    result = service.analyze_email(subject=subject, body=body, sender="student@university.edu")

    assert result.category == "Student"
    assert result.priority == "MEDIUM"
    assert result.deadline == "2026-09-12"

def test_mock_ai_heuristic_unseen_email():
    """Verify MockAIService dynamic fallback on unseen email without crash."""
    service = MockAIService()
    subject = "Urgent: Faculty Meeting on Research Funding"
    body = "All professors are requested to submit project proposals before September 22. Urgent action required."
    result = service.analyze_email(subject=subject, body=body, sender="director@institute.org")

    assert result.priority == "HIGH"
    assert result.deadline == "2026-09-22"
    assert len(result.action_items) >= 1
    assert len(result.evidence) >= 1

def test_llm_service_fallback_to_mock():
    """Verify LLMService gracefully routes to MockAIService when no LLM_API_KEY is configured."""
    llm_service = LLMService(fallback_to_mock=True)
    result = llm_service.analyze_email(
        subject="Internal Assessment Marks Submission",
        body="Submit marks before September 10.",
        sender="hod@university.edu"
    )
    assert isinstance(result, AIServiceOutput)
    assert result.category == "Academic"
    assert result.priority == "HIGH"

def test_api_analyze_unanalyzed_email():
    """Test POST /api/emails/{id}/analyze executes MockAIService and persists to DB."""
    # Email 11 is originally un-analyzed in seed data
    get_before = client.get("/api/analysis/11")
    assert get_before.status_code == 404

    # Trigger analysis via API
    response = client.post("/api/emails/11/analyze")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "analysis" in data
    analysis = data["analysis"]
    assert analysis["category"] == "Research"
    assert analysis["priority"] == "MEDIUM"
    assert len(analysis["evidences"]) >= 1

    # Verify GET /api/analysis/11 now returns persisted data
    get_after = client.get("/api/analysis/11")
    assert get_after.status_code == 200
    assert get_after.json()["category"] == "Research"

    # Verify action items were created for email 11
    email_detail = client.get("/api/emails/11").json()
    assert len(email_detail["action_items"]) >= 1

def test_api_analyze_capstone_with_meeting():
    """Test POST /api/emails/13/analyze creates meeting, deadline, and updates dashboard metrics."""
    # Email 13 is Capstone Project evaluation
    dash_before = client.get("/api/dashboard").json()["metrics"]
    meetings_before = dash_before["upcoming_meetings_count"]

    response = client.post("/api/emails/13/analyze")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    # Verify meeting was recorded in database
    email_detail = client.get("/api/emails/13").json()
    assert len(email_detail["meetings"]) == 1
    meeting = email_detail["meetings"][0]
    assert "Capstone Project" in meeting["title"]
    assert meeting["location"] == "Systems Lab 4"

    # Verify dashboard metrics reflect the newly analyzed meeting
    dash_after = client.get("/api/dashboard").json()["metrics"]
    assert dash_after["upcoming_meetings_count"] == meetings_before + 1
