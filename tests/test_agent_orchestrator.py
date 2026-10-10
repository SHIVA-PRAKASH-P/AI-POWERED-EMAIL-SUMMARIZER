import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from backend.main import app
from backend.app.ai.orchestrator import AIOrchestrator
from backend.app.ai.classification_service import ClassificationService
from backend.app.ai.temporal_service import TemporalExtractionService
from backend.app.ai.action_service import ActionExtractionService
from backend.app.ai.meeting_service import MeetingExtractionService
from backend.app.ai.priority_service import PriorityService
from backend.app.ai.summarization_service import SummarizationService
from backend.app.ai.evidence_service import EvidenceValidationService
from backend.app.database.session import SessionLocal, reset_db
from backend.app.database.seed_data import seed_database

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    reset_db()
    db = SessionLocal()
    seed_database(db)
    db.close()

def test_orchestrator_initialization():
    """Verify AIOrchestrator properly initializes all 7 specialized sub-services."""
    orchestrator = AIOrchestrator()
    assert isinstance(orchestrator.classification_service, ClassificationService)
    assert isinstance(orchestrator.temporal_service, TemporalExtractionService)
    assert isinstance(orchestrator.action_service, ActionExtractionService)
    assert isinstance(orchestrator.meeting_service, MeetingExtractionService)
    assert isinstance(orchestrator.priority_service, PriorityService)
    assert isinstance(orchestrator.summarization_service, SummarizationService)
    assert isinstance(orchestrator.evidence_service, EvidenceValidationService)

def test_orchestrator_full_workflow_steps():
    """Verify orchestrator executes sequential pipeline steps and generates trace."""
    orchestrator = AIOrchestrator()
    subject = "Internal Assessment Marks Submission"
    body = (
        "Dear Faculty, all members are requested to submit the internal assessment marks before September 10. "
        "A review meeting will be conducted on September 8 at 10 AM in the Seminar Hall. "
        "Please bring the updated mark sheet and student attendance logs."
    )
    result = orchestrator.orchestrate(
        subject=subject,
        body=body,
        sender="hod.cse@university.edu",
        received_at=datetime(2026, 9, 6, 9, 0, 0)
    )

    assert "output" in result
    assert "steps" in result
    assert "tasks_detected" in result

    steps = result["steps"]
    assert any("Context analysis" in s for s in steps)
    assert any("Task detection" in s for s in steps)
    assert any("ClassificationService" in s for s in steps)
    assert any("TemporalExtractionService" in s for s in steps)
    assert any("MeetingExtractionService" in s for s in steps)
    assert any("ActionExtractionService" in s for s in steps)
    assert any("PriorityService" in s for s in steps)
    assert any("SummarizationService" in s for s in steps)
    assert any("EvidenceValidationService" in s for s in steps)
    assert any("complete" in s.lower() for s in steps)

    output = result["output"]
    assert output.category == "Academic"
    assert output.priority == "HIGH"
    assert output.deadline == "2026-09-10"
    assert output.meeting is not None
    assert output.meeting.time == "10:00"
    assert output.meeting.location == "Seminar Hall"
    assert len(output.action_items) >= 2
    assert len(output.evidence) >= 2

def test_orchestrator_task_detection_no_deadline():
    """Verify task detection accurately skips temporal extraction when no dates exist."""
    orchestrator = AIOrchestrator()
    subject = "Library Access Guidelines"
    body = "Faculty members can now access the digital library portal from off-campus networks."
    result = orchestrator.orchestrate(
        subject=subject,
        body=body,
        sender="librarian@university.edu"
    )
    tasks = result["tasks_detected"]
    assert tasks["temporal"] is False
    assert result["output"].deadline is None

def test_orchestrator_task_detection_with_meeting():
    """Verify meeting extraction triggers when event keywords exist."""
    orchestrator = AIOrchestrator()
    subject = "Department Review Meeting"
    body = "The review session will be held on September 8 at 10 AM in the Seminar Hall. Please bring mark sheets."
    result = orchestrator.orchestrate(
        subject=subject,
        body=body,
        sender="hod@university.edu"
    )
    assert result["tasks_detected"]["meeting"] is True
    assert result["output"].meeting is not None
    assert result["output"].meeting.location == "Seminar Hall"

def test_orchestrator_priority_reasoning():
    """Verify priority service evaluates high statutory authority and mandatory cues."""
    orchestrator = AIOrchestrator()
    subject = "Confidential: Question Paper Submission"
    body = "It is strictly mandatory to submit question papers before September 15 to the COE office."
    result = orchestrator.orchestrate(
        subject=subject,
        body=body,
        sender="coe@university.edu"
    )
    output = result["output"]
    assert output.priority == "HIGH"
    assert "high-authority" in output.priority_reason.lower() or "statutory" in output.priority_reason.lower() or "mandatory" in output.priority_reason.lower()

def test_api_orchestration_execution():
    """Test POST /api/emails/{id}/analyze returns orchestrated pipeline steps."""
    # Force refresh analysis on Email 1 to inspect multi-agent trace
    response = client.post("/api/emails/1/analyze?force_refresh=true")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "steps" in data
    assert len(data["steps"]) >= 8
    assert "analysis" in data
    assert data["analysis"]["category"] == "Academic"
    assert data["analysis"]["priority"] == "HIGH"
