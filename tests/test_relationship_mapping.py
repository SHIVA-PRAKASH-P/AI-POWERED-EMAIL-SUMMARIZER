import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.ai.relationship_mapper import ActionDeadlineMapper
from backend.app.ai.action_service import ActionExtractionService
from backend.app.ai.orchestrator import AIOrchestrator
from backend.app.database.session import SessionLocal, init_db
from backend.app.models import Email, ActionItem

client = TestClient(app)
REF_DATE = datetime(2026, 9, 6, 9, 0, 0)

@pytest.fixture
def mapper():
    return ActionDeadlineMapper()

@pytest.fixture
def action_service():
    return ActionExtractionService()

@pytest.fixture
def orchestrator():
    return AIOrchestrator()


def test_direct_submission_due_on_mapping(mapper):
    """Scenario 1: Direct submission obligation bound to an explicit deadline."""
    actions = [
        {
            "description": "Submit final question papers to examination section",
            "source_text": "Please submit final question papers to examination section before September 15.",
            "priority": "HIGH"
        }
    ]
    body = "Please submit final question papers to examination section before September 15."
    
    mapped = mapper.map_relationships(
        actions=actions,
        body=body,
        reference_date=REF_DATE,
        email_deadline="2026-09-15"
    )

    assert len(mapped) == 1
    act = mapped[0]
    assert act["relationship_type"] == "DUE_ON"
    assert act["due_date"] == "2026-09-15"
    assert "september 15" in act["relationship_reason"].lower()


def test_multi_action_multi_deadline_disambiguation(action_service):
    """Scenario 2: Distinct actions within the same email bound to different deadlines."""
    body = (
        "Dear Colleagues,\n\n"
        "Please submit the student marks before September 10.\n"
        "Also, kindly upload the project evaluation rubrics by September 20.\n\n"
        "Thank you."
    )
    
    mapped = action_service.extract_actions(
        body=body,
        deadline="2026-09-10",
        reference_date=REF_DATE
    )

    assert len(mapped) >= 2
    # Find marks action and rubrics action
    marks_act = next((a for a in mapped if "marks" in a["description"].lower()), None)
    rubrics_act = next((a for a in mapped if "rubrics" in a["description"].lower() or "evaluation" in a["description"].lower()), None)

    assert marks_act is not None
    assert marks_act["relationship_type"] == "DUE_ON"
    assert marks_act["due_date"] == "2026-09-10"

    assert rubrics_act is not None
    assert rubrics_act["relationship_type"] == "DUE_ON"
    assert rubrics_act["due_date"] == "2026-09-20"
    # Proves fine-grained clausal disambiguation rather than assigning 2026-09-10 to both!
    assert marks_act["due_date"] != rubrics_act["due_date"]


def test_meeting_preparation_relationship_prepare_before(mapper):
    """Scenario 3: Prerequisite preparation task tied to an upcoming meeting."""
    actions = [
        {
            "description": "Bring updated mark sheets and student attendance logs",
            "source_text": "Please bring the updated mark sheets and student attendance logs.",
            "priority": "MEDIUM"
        }
    ]
    body = "A review meeting will be conducted on September 8 at 10 AM in Seminar Hall. Please bring updated mark sheets."
    meeting = {
        "title": "Department Review Meeting",
        "date": "2026-09-08",
        "time": "10:00",
        "location": "Seminar Hall"
    }

    mapped = mapper.map_relationships(
        actions=actions,
        body=body,
        reference_date=REF_DATE,
        email_deadline="2026-09-10",
        meeting=meeting
    )

    assert len(mapped) == 1
    act = mapped[0]
    assert act["relationship_type"] == "PREPARE_BEFORE"
    assert act["due_date"] == "2026-09-08"
    assert act["target_event"] == "Department Review Meeting"
    assert "Prerequisite preparation" in act["relationship_reason"]
    assert act["binding_confidence"] >= 0.90


def test_meeting_attendance_relationship_attend_by(mapper):
    """Scenario 4: Physical or virtual event attendance requirement."""
    actions = [
        {
            "description": "Attend the emergency faculty council meeting",
            "source_text": "All members are requested to attend the emergency faculty council meeting on September 12 at 3 PM.",
            "priority": "HIGH"
        }
    ]
    body = "All members are requested to attend the emergency faculty council meeting on September 12 at 3 PM in the Senate Hall."
    meeting = {
        "title": "Emergency Faculty Council Meeting",
        "date": "2026-09-12",
        "time": "15:00",
        "location": "Senate Hall"
    }

    mapped = mapper.map_relationships(
        actions=actions,
        body=body,
        reference_date=REF_DATE,
        meeting=meeting
    )

    assert len(mapped) == 1
    act = mapped[0]
    assert act["relationship_type"] == "ATTEND_BY"
    assert act["due_date"] == "2026-09-12"
    assert "attendance" in act["relationship_reason"].lower()


def test_communication_response_deadline_communicate_by(mapper):
    """Scenario 5: Confirmation or nomination response bound to deadline."""
    actions = [
        {
            "description": "Confirm attendance and dietary preferences",
            "source_text": "Please confirm your attendance and dietary preferences by September 14.",
            "priority": "LOW"
        }
    ]
    body = "Please confirm your attendance and dietary preferences by September 14."

    mapped = mapper.map_relationships(
        actions=actions,
        body=body,
        reference_date=REF_DATE,
        email_deadline="2026-09-14"
    )

    assert len(mapped) == 1
    act = mapped[0]
    assert act["relationship_type"] == "COMMUNICATE_BY"
    assert act["due_date"] == "2026-09-14"
    assert "Communication requirement" in act["relationship_reason"]


def test_standalone_routine_action_without_deadline(mapper):
    """Scenario 6: Ongoing operational task with no temporal constraint."""
    actions = [
        {
            "description": "Verify student credentials on the department portal periodically",
            "source_text": "Please verify student credentials on the department portal periodically.",
            "priority": "LOW"
        }
    ]
    body = "Please verify student credentials on the department portal periodically."

    mapped = mapper.map_relationships(
        actions=actions,
        body=body,
        reference_date=REF_DATE,
        email_deadline=None,
        meeting=None
    )

    assert len(mapped) == 1
    act = mapped[0]
    assert act["relationship_type"] == "STANDALONE"
    assert act["due_date"] is None
    assert act["target_event"] is None
    assert "Routine" in act["relationship_reason"]


def test_mixed_flagship_email_relationships(orchestrator):
    """Scenario 7: Flagship HOD Email with DUE_ON submission and PREPARE_BEFORE meeting prep."""
    subject = "Internal Assessment Marks Submission"
    body = (
        "Dear Faculty,\n\n"
        "All members are requested to submit the internal assessment marks before September 10. "
        "A review meeting will be conducted on September 8 at 10 AM in the Seminar Hall. "
        "Please bring the updated mark sheet and student attendance logs.\n\n"
        "Regards,\nHOD CSE"
    )
    
    result = orchestrator.orchestrate(
        subject=subject,
        body=body,
        sender="hod.cse@university.edu",
        received_at=REF_DATE
    )

    output = result["output"]
    assert len(output.structured_actions) >= 2
    
    # Check that both DUE_ON and PREPARE_BEFORE are represented correctly
    rel_types = [a.relationship_type for a in output.structured_actions]
    assert "DUE_ON" in rel_types
    assert "PREPARE_BEFORE" in rel_types

    # Find the submission action
    sub_action = next(a for a in output.structured_actions if a.relationship_type == "DUE_ON")
    assert sub_action.due_date == "2026-09-10"

    # Find the preparation action
    prep_action = next(a for a in output.structured_actions if a.relationship_type == "PREPARE_BEFORE")
    assert prep_action.due_date == "2026-09-08"


def test_relative_date_temporal_resolution_in_relationship(action_service):
    """Scenario 8: Relative expression 'tomorrow' correctly normalized in action relationship."""
    body = "Please submit the final revision of course outcomes by tomorrow."
    
    mapped = action_service.extract_actions(
        body=body,
        reference_date=REF_DATE
    )

    assert len(mapped) >= 1
    act = mapped[0]
    assert act["relationship_type"] == "DUE_ON"
    assert act["due_date"] == "2026-09-07"  # Tomorrow from 2026-09-06
    assert "2026-09-07" in act["relationship_reason"]


def test_api_action_items_filtering_by_relationship_type():
    """Scenario 9: REST API query parameter filtering by relationship_type."""
    # Test filtering DUE_ON
    resp_due = client.get("/api/action-items?relationship_type=DUE_ON")
    assert resp_due.status_code == 200
    items_due = resp_due.json()
    assert len(items_due) > 0
    for item in items_due:
        assert item["relationship_type"] == "DUE_ON"

    # Test filtering PREPARE_BEFORE
    resp_prep = client.get("/api/action-items?relationship_type=PREPARE_BEFORE")
    assert resp_prep.status_code == 200
    items_prep = resp_prep.json()
    assert len(items_prep) > 0
    for item in items_prep:
        assert item["relationship_type"] == "PREPARE_BEFORE"


def test_api_deadlines_contains_relationship_metadata():
    """Scenario 10: Deadlines endpoint includes relationship_type and target_event."""
    resp = client.get("/api/deadlines")
    assert resp.status_code == 200
    deadlines = resp.json()
    assert len(deadlines) > 0
    
    first = deadlines[0]
    assert "relationship_type" in first
    assert "target_event" in first
    assert "relationship_reason" in first
    assert first["relationship_type"] in ["DUE_ON", "PREPARE_BEFORE", "ATTEND_BY", "COMMUNICATE_BY", "STANDALONE"]


def test_patch_action_item_relationship_attributes():
    """Scenario 11: Updating action item relationship fields via PATCH endpoint."""
    # Fetch first action item
    resp = client.get("/api/action-items")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) > 0
    target_id = items[0]["id"]

    # Update relationship fields
    update_payload = {
        "relationship_type": "PREPARE_BEFORE",
        "target_event": "NAAC Steering Committee Audit",
        "relationship_reason": "Updated prerequisite relationship for committee audit"
    }
    patch_resp = client.patch(f"/api/action-items/{target_id}", json=update_payload)
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["relationship_type"] == "PREPARE_BEFORE"
    assert updated["target_event"] == "NAAC Steering Committee Audit"
    assert updated["relationship_reason"] == "Updated prerequisite relationship for committee audit"
