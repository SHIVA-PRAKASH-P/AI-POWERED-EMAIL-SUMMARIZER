import json
import pytest
from unittest.mock import patch, MagicMock
import httpx
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.ai.llm_service import LLMService, SYSTEM_PROMPT
from backend.app.ai.mock_service import MockAIService
from backend.app.ai.orchestrator import AIOrchestrator
from backend.app.schemas.ai_schema import AIServiceOutput
from backend.app.config import settings

client = TestClient(app)

SAMPLE_SUBJECT = "URGENT: Submission of End-Semester Grades by Friday 5 PM"
SAMPLE_BODY = """Dear Faculty,
Please ensure all internal assessment marks and end-semester lab grades are submitted
to the Controller of Examinations portal strictly by Friday, September 11, 2026, 5:00 PM.
Failure to submit will delay student grade card generation.
Regards,
Dean of Academic Affairs"""
SAMPLE_SENDER = "dean.academics@university.edu"

def test_llm_service_fallback_when_no_api_key():
    """Verify that LLMService defaults to MockAIService when no key is set."""
    service = LLMService(provider="openai", api_key="", fallback_to_mock=True)
    assert service.is_configured is False
    assert service.masked_key == "Not Configured"

    output = service.analyze_email(SAMPLE_SUBJECT, SAMPLE_BODY, SAMPLE_SENDER)
    assert isinstance(output, AIServiceOutput)
    assert output.priority in ["HIGH", "MEDIUM", "LOW"]
    assert output.summary is not None
    assert len(output.action_items) > 0

def test_llm_service_strict_error_when_fallback_disabled():
    """Verify that LLMService raises ValueError if fallback is disabled and key is missing."""
    service = LLMService(provider="openai", api_key="", fallback_to_mock=False)
    with pytest.raises(ValueError) as exc_info:
        service.analyze_email(SAMPLE_SUBJECT, SAMPLE_BODY, SAMPLE_SENDER)
    assert "LLM API key not configured" in str(exc_info.value)

def test_llm_service_secret_masking():
    """Ensure secret keys are never exposed in masked_key or string representations."""
    raw_key = "sk-proj-super-secret-key-123456789"
    service = LLMService(provider="openai", api_key=raw_key)
    masked = service.masked_key
    assert "super-secret" not in masked
    assert masked.startswith("sk-p")
    assert masked.endswith("6789")

    # Short keys
    short_service = LLMService(api_key="12345")
    assert short_service.masked_key == "********"

def test_mock_provider_explicit_mode():
    """Verify provider='mock' cleanly calls MockAIService without requiring keys."""
    service = LLMService(provider="mock")
    assert service.is_configured is True
    output = service.analyze_email(SAMPLE_SUBJECT, SAMPLE_BODY, SAMPLE_SENDER)
    assert isinstance(output, AIServiceOutput)
    assert output.category is not None

def test_openai_response_parsing_and_validation():
    """Test OpenAI JSON completion parsing, Pydantic validation, and evidence grounding."""
    mock_llm_json = {
        "summary": "Dean requires submission of end-semester lab grades by Friday.",
        "category": "Examination",
        "priority": "HIGH",
        "priority_reason": "Statutory academic deadline from Dean with consequence for grade cards.",
        "deadline": "2026-09-11",
        "meeting": None,
        "action_items": ["Submit all internal assessment marks to COE portal"],
        "structured_actions": [
            {
                "description": "Submit all internal assessment marks to COE portal",
                "due_date": "2026-09-11",
                "priority": "HIGH",
                "relationship_type": "DUE_ON",
                "target_event": "Grade submission",
                "relationship_reason": "Direct submission deadline",
                "binding_confidence": 1.0
            }
        ],
        "important_entities": [
            {"type": "ORGANIZATION", "value": "Controller of Examinations"}
        ],
        "evidence": [
            {
                "field_name": "deadline",
                "extracted_value": "2026-09-11",
                "source_text": "Friday, September 11, 2026, 5:00 PM",
                "confidence": 1.0,
                "validation_status": "VERIFIED"
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(mock_llm_json)}}]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client.post", return_value=mock_resp):
        service = LLMService(provider="openai", api_key="sk-testkey123456789", fallback_to_mock=False)
        output = service.analyze_email(SAMPLE_SUBJECT, SAMPLE_BODY, SAMPLE_SENDER)

        assert isinstance(output, AIServiceOutput)
        assert output.category == "Examination"
        assert output.priority == "HIGH"
        assert output.deadline == "2026-09-11"
        assert len(output.structured_actions) == 1
        assert output.structured_actions[0].relationship_type == "DUE_ON"
        assert len(output.evidence) >= 1

def test_markdown_wrapped_json_extraction():
    """Verify that JSON wrapped in markdown ```json ... ``` codeblocks parses cleanly."""
    service = LLMService(provider="mock")
    wrapped_content = """Here is the structured intelligence:
```json
{
  "summary": "Internal department review meeting scheduled.",
  "category": "Meeting",
  "priority": "MEDIUM",
  "priority_reason": "Department level review meeting",
  "deadline": null,
  "meeting": {
    "title": "Faculty Meeting",
    "date": "2026-09-15",
    "time": "14:00",
    "location": "Conference Room A",
    "preparation": "Bring syllabus"
  },
  "action_items": ["Attend faculty meeting"],
  "structured_actions": [],
  "important_entities": [],
  "evidence": []
}
```
Hope this helps!"""
    parsed = service._extract_json(wrapped_content)
    assert parsed["category"] == "Meeting"
    assert parsed["meeting"]["location"] == "Conference Room A"

def test_google_gemini_api_dispatch_and_parsing():
    """Test Google Gemini REST candidate extraction."""
    mock_gemini_json = {
        "summary": "Gemini extracted summary.",
        "category": "Academic",
        "priority": "LOW",
        "priority_reason": "Routine information",
        "deadline": None,
        "meeting": None,
        "action_items": ["Review information"],
        "structured_actions": [],
        "important_entities": [],
        "evidence": []
    }

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps(mock_gemini_json)}]}}
        ]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client.post", return_value=mock_resp):
        service = LLMService(provider="gemini", api_key="AIzaSy-testkey", fallback_to_mock=False)
        output = service.analyze_email(SAMPLE_SUBJECT, SAMPLE_BODY, SAMPLE_SENDER)
        assert output.summary == "Gemini extracted summary."
        assert output.category == "Academic"

def test_anthropic_api_dispatch_and_parsing():
    """Test Anthropic Messages API dispatch."""
    mock_anthropic_json = {
        "summary": "Anthropic Claude extracted summary.",
        "category": "Research",
        "priority": "HIGH",
        "priority_reason": "Grant submission milestone",
        "deadline": "2026-10-01",
        "meeting": None,
        "action_items": ["Submit grant proposal"],
        "structured_actions": [],
        "important_entities": [],
        "evidence": []
    }

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "content": [{"text": json.dumps(mock_anthropic_json)}]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client.post", return_value=mock_resp):
        service = LLMService(provider="anthropic", api_key="sk-ant-testkey", fallback_to_mock=False)
        output = service.analyze_email(SAMPLE_SUBJECT, SAMPLE_BODY, SAMPLE_SENDER)
        assert output.summary == "Anthropic Claude extracted summary."
        assert output.category == "Research"

def test_http_network_error_triggers_graceful_fallback():
    """Verify that network failures automatically trigger deterministic fallback when enabled."""
    with patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")):
        service = LLMService(provider="openai", api_key="sk-livekey12345", fallback_to_mock=True)
        # Should NOT raise, but return MockAIService output
        output = service.analyze_email(SAMPLE_SUBJECT, SAMPLE_BODY, SAMPLE_SENDER)
        assert isinstance(output, AIServiceOutput)
        assert output.summary is not None

def test_ai_orchestrator_routes_to_llm_when_configured():
    """Verify AIOrchestrator respects settings.AI_MODE == 'llm'."""
    mock_output = AIServiceOutput(
        summary="Orchestrated through LLM adapter.",
        category="Administrative",
        priority="HIGH",
        priority_reason="High administrative stakes",
        deadline="2026-09-12",
        meeting=None,
        action_items=["Complete compliance report"],
        structured_actions=[],
        important_entities=[],
        evidence=[]
    )

    mock_llm_service = MagicMock(spec=LLMService)
    mock_llm_service.provider = "openai"
    mock_llm_service.model = "gpt-4o-mini"
    mock_llm_service.analyze_email.return_value = mock_output

    with patch.object(settings, "AI_MODE", "llm"):
        orchestrator = AIOrchestrator(llm_service=mock_llm_service)
        result = orchestrator.orchestrate(SAMPLE_SUBJECT, SAMPLE_BODY, SAMPLE_SENDER)
        assert result["output"].summary == "Orchestrated through LLM adapter."
        assert any("Active AI Mode: 'llm'" in step for step in result["steps"])

def test_api_llm_status_endpoint():
    """Verify GET /api/llm-status never leaks API key."""
    res = client.get("/api/llm-status")
    assert res.status_code == 200
    data = res.json()
    assert "ai_mode" in data
    assert "provider" in data
    assert "masked_api_key" in data
    # Ensure full secret key is never present
    if settings.LLM_API_KEY:
        assert settings.LLM_API_KEY not in data["masked_api_key"]
    assert "is_ready" in data

def test_api_health_endpoint_stage_12():
    """Verify health check reports Stage 12."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert "STAGE" in data["stage"]
    assert "llm_provider" in data
    assert "llm_configured" in data
