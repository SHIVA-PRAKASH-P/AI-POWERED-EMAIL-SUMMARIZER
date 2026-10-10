import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.ai.evidence_service import EvidenceValidationService
from backend.app.ai.orchestrator import AIOrchestrator

client = TestClient(app)

SAMPLE_BODY = (
    "Dear Faculty,\n\n"
    "All members are requested to submit the internal assessment marks before September 10. "
    "A review meeting will be conducted on September 8 at 10 AM in the Seminar Hall. "
    "Please bring the updated mark sheet and student attendance logs.\n\n"
    "Regards,\nOffice of the HOD"
)

@pytest.fixture
def evidence_service():
    return EvidenceValidationService()

@pytest.fixture
def orchestrator():
    return AIOrchestrator()


def test_exact_span_grounding_verified(evidence_service):
    """Scenario 1: Exact sentence evidence grounded with character offsets."""
    deadline = "2026-09-10"
    deadline_raw = "September 10"

    evidences = evidence_service.validate_and_ground(
        body=SAMPLE_BODY,
        deadline=deadline,
        deadline_raw=deadline_raw
    )

    assert len(evidences) >= 1
    ev = next(e for e in evidences if e.field_name == "deadline")
    assert ev.validation_status == "VERIFIED"
    assert ev.confidence >= 0.95
    assert ev.char_start is not None
    assert ev.char_end is not None
    # Character offsets accurately slice the original email body
    sliced = SAMPLE_BODY[ev.char_start:ev.char_end]
    assert "internal assessment marks" in sliced or "September 10" in sliced


def test_relative_temporal_grounding_inferred(evidence_service):
    """Scenario 2: Relative temporal expression recognized as INFERRED via temporal anchor."""
    body = "Please submit the final accreditation report by tomorrow without fail."
    evidences = evidence_service.validate_and_ground(
        body=body,
        deadline="2026-09-07",
        deadline_raw="tomorrow"
    )

    assert len(evidences) >= 1
    ev = evidences[0]
    assert ev.validation_status == "INFERRED"
    assert ev.grounding_method == "TEMPORAL_ANCHOR"
    assert ev.confidence >= 0.90
    assert "tomorrow" in ev.source_text.lower()


def test_meeting_clausal_grounding(evidence_service):
    """Scenario 3: Meeting details grounded to venue and scheduled time sentence."""
    meeting_dict = {
        "title": "Review Meeting",
        "date": "2026-09-08",
        "time": "10:00",
        "location": "Seminar Hall"
    }

    evidences = evidence_service.validate_and_ground(
        body=SAMPLE_BODY,
        meeting=meeting_dict
    )

    assert len(evidences) >= 1
    ev = next(e for e in evidences if e.field_name == "meeting")
    assert ev.validation_status == "VERIFIED"
    assert "Seminar Hall" in ev.extracted_value
    assert "Seminar Hall" in ev.source_text
    assert ev.char_start is not None


def test_action_items_grounding_with_offsets(evidence_service):
    """Scenario 4: Extracted action item traceable to source directive sentence."""
    actions = [
        {
            "description": "Bring updated mark sheet and student attendance logs",
            "source_text": "Please bring the updated mark sheet and student attendance logs."
        }
    ]

    evidences = evidence_service.validate_and_ground(
        body=SAMPLE_BODY,
        actions=actions
    )

    assert len(evidences) >= 1
    ev = next(e for e in evidences if e.field_name == "action_item")
    assert ev.validation_status == "VERIFIED"
    assert ev.confidence >= 0.90
    assert ev.char_start is not None
    assert "mark sheet" in SAMPLE_BODY[ev.char_start:ev.char_end]


def test_hallucination_detection_unsupported(evidence_service):
    """Scenario 5: Fabricated fact not in email is flagged as UNSUPPORTED with low confidence."""
    result = evidence_service.validate_assertion(
        field_name="deadline",
        extracted_value="December 25, 2026",
        raw_text=SAMPLE_BODY
    )

    assert result["is_valid"] is False
    assert result["validation_status"] == "UNSUPPORTED"
    assert result["confidence"] <= 0.35
    assert result["grounded_sentence"] is None
    assert "No verifiable lexical" in result["audit_explanation"] or "ungrounded" in result["audit_explanation"].lower()


def test_partial_grounding_detection(evidence_service):
    """Scenario 6: Paraphrased or partially matching assertion identified as PARTIAL."""
    result = evidence_service.validate_assertion(
        field_name="action_item",
        extracted_value="Submit logs and sheets",
        raw_text=SAMPLE_BODY
    )

    assert result["is_valid"] is True
    assert result["validation_status"] in ["VERIFIED", "PARTIAL"]
    assert result["char_start"] is not None


def test_orchestrator_evidence_pipeline_integration(orchestrator):
    """Scenario 7: Full AI orchestrator produces grounded evidences with validation metadata."""
    result = orchestrator.orchestrate(
        subject="Internal Assessment Marks Submission",
        body=SAMPLE_BODY,
        sender="hod.cse@university.edu",
        received_at=datetime(2026, 9, 6, 9, 0, 0)
    )

    evidences = result["output"].evidence
    assert len(evidences) >= 3

    for ev in evidences:
        assert ev.validation_status in ["VERIFIED", "INFERRED", "PARTIAL"]
        assert 0.0 <= ev.confidence <= 1.0
        assert len(ev.source_text) > 5
        assert ev.grounding_method in ["EXACT_SPAN", "TEMPORAL_ANCHOR", "CLAUSAL_BOUNDARY", "TOKEN_SPAN_OVERLAP", "TOKEN_OVERLAP", "PARTIAL_OVERLAP"]


def test_api_verify_assertion_supported():
    """Scenario 8: API endpoint /api/analysis/verify-assertion validates authentic assertion."""
    payload = {
        "field_name": "deadline",
        "extracted_value": "September 10",
        "raw_text": SAMPLE_BODY
    }
    resp = client.post("/api/analysis/verify-assertion", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["validation_status"] == "VERIFIED"
    assert data["confidence"] >= 0.90
    assert data["char_start"] is not None
    assert "September 10" in data["grounded_sentence"]


def test_api_verify_assertion_hallucination():
    """Scenario 9: API endpoint detects and rejects unsupported hallucinated assertion."""
    payload = {
        "field_name": "action_item",
        "extracted_value": "Purchase new supercomputers for lab 4",
        "raw_text": SAMPLE_BODY
    }
    resp = client.post("/api/analysis/verify-assertion", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is False
    assert data["validation_status"] == "UNSUPPORTED"
    assert data["confidence"] <= 0.35


def test_api_verify_assertion_by_email_id():
    """Scenario 10: API endpoint validates assertion directly against stored email ID."""
    payload = {
        "field_name": "deadline",
        "extracted_value": "September 10",
        "email_id": 1
    }
    resp = client.post("/api/analysis/verify-assertion", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["validation_status"] == "VERIFIED"


def test_api_get_analysis_returns_evidence_metadata():
    """Scenario 11: GET /api/analysis/{email_id} returns validation_status and character offsets."""
    resp = client.get("/api/analysis/1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["evidences"]) > 0

    first_ev = data["evidences"][0]
    assert "validation_status" in first_ev
    assert "char_start" in first_ev
    assert "char_end" in first_ev
    assert "grounding_method" in first_ev
    assert first_ev["validation_status"] in ["VERIFIED", "INFERRED", "PARTIAL"]


def test_empty_input_graceful_handling(evidence_service):
    """Scenario 12: Empty inputs handled defensively without crashing."""
    res = evidence_service.validate_assertion("test", "", "")
    assert res["is_valid"] is False
    assert res["validation_status"] == "UNSUPPORTED"
