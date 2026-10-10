import json
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
import httpx
from pydantic import ValidationError

from backend.app.ai.base_service import AIService
from backend.app.ai.mock_service import MockAIService
from backend.app.ai.evidence_service import EvidenceValidationService
from backend.app.schemas.priority_schema import AIPriorityResult
from backend.app.schemas.ai_schema import (
    AIServiceOutput,
    AIMeetingOutput,
    AIEntityOutput,
    AIEvidenceOutput,
    AIActionItemOutput
)
from backend.app.config import settings
from backend.app.utils.security_logging import SensitiveDataFilter

logger = logging.getLogger("ai.llm_service")

PRIORITY_SYSTEM_PROMPT = """You are an expert Context-Aware AI Priority Classification Engine for academic email correspondence.
Analyze the email's full semantic context, meaning, sender role, extracted tasks, and institutional consequences to determine its priority.

You MUST evaluate these 10 core dimensions:
1. URGENCY: Is immediate attention required? Is the email time-sensitive?
2. DEADLINE: Is there an imminent deadline? How close is it, and how critical is the required task?
3. REQUIRED ACTION: Does the recipient need to submit, verify, attend, respond, upload, or prepare? Is the action mandatory or optional?
4. CONSEQUENCE: What happens if ignored? Academic/administrative penalties or compliance issues escalate priority.
5. INSTITUTIONAL IMPORTANCE: Examination, marks, accreditation (NAAC), statutory regulations have higher stakes than general circulars.
6. AUDIENCE: Is it directed at the recipient personally/departmentally vs broadcast to the entire student body or general campus?
7. MANDATORY VS VOLUNTARY (CRITICAL):
   - Mandatory duties ("faculty must submit marks by tomorrow") → HIGH.
   - Voluntary opportunities ("interested students may register by today", "welcome to participate") → MEDIUM, not HIGH.
8. CONTEXT AND SEMANTIC MEANING:
   - Do NOT determine priority merely because a word like "today", "tomorrow", "deadline", "mandatory", "submit", or "verify" appears.
   - Interpret how the word is functioning in the full email context.
9. ROUTINE COMMUNICATION:
   - Newsletters, general awareness, greetings, daily vocabulary ("Word of the Day"), and routine announcements are LOW or MEDIUM.
   - An announcement containing "mandatory" without urgent action/consequence is NOT automatically HIGH.
10. SENDER CONTEXT: Consider sender role (COE, Dean, HOD, Student, Routine) as supporting context without hardcoding fixed rules.

Respond with a single, valid JSON object matching this schema exactly:
{
  "priority": "HIGH" | "MEDIUM" | "LOW",
  "confidence": 0.0 to 1.0,
  "reason": "Short human-readable contextual explanation of why this priority was assigned (explaining urgency, action requirement, and consequences, NOT simply listing matched words)."
}
"""

SYSTEM_PROMPT = """You are an expert AI Email Intelligence Assistant designed specifically for university faculty and department heads.
Your mission is to analyze academic correspondence and extract structured, actionable intelligence with zero hallucination.

You MUST respond with a single, valid JSON object matching the following structure exactly:
{
  "summary": "Concise 2-3 sentence executive synthesis of the email content and institutional purpose.",
  "category": "Academic" | "Administrative" | "Examination" | "Meeting" | "Student" | "Department" | "Event" | "Research" | "Placement" | "General",
  "priority": "HIGH" | "MEDIUM" | "LOW",
  "priority_reason": "Explainable justification combining sender authority, deadline proximity, and mandatory academic tags.",
  "deadline": "YYYY-MM-DD" or null,
  "meeting": {
    "title": "Meeting name or title",
    "date": "YYYY-MM-DD" or null,
    "time": "HH:MM" or null,
    "location": "Physical room or virtual platform link" or null,
    "preparation": "Required preparatory documents or agenda notes" or null
  } or null,
  "action_items": [
    "Clean imperative action description directed at the faculty recipient"
  ],
  "structured_actions": [
    {
      "description": "Clean imperative action description",
      "due_date": "YYYY-MM-DD" or null,
      "priority": "HIGH" | "MEDIUM" | "LOW",
      "relationship_type": "DUE_ON" | "PREPARE_BEFORE" | "ATTEND_BY" | "COMMUNICATE_BY" | "STANDALONE",
      "target_event": "Associated meeting title or submission event" or null,
      "relationship_reason": "Relational justification for deadline association" or null,
      "binding_confidence": 1.0
    }
  ],
  "important_entities": [
    {
      "type": "PERSON" | "DATE" | "VENUE" | "ORGANIZATION" | "COURSE",
      "value": "Entity textual value"
    }
  ],
  "evidence": [
    {
      "field_name": "summary" | "priority" | "deadline" | "meeting" | "action_items",
      "extracted_value": "Extracted string value",
      "source_text": "Exact sentence or clause from the email body supporting this extraction",
      "confidence": 1.0,
      "validation_status": "VERIFIED"
    }
  ]
}

Strict Rules:
1. Output ONLY the JSON object. Do not wrap in markdown or include extraneous conversational remarks.
2. If no deadline or meeting exists, set them to null.
3. Every structured action MUST have an explicit relationship_type:
   - DUE_ON: Direct submission or milestone deadline.
   - PREPARE_BEFORE: Preparatory work required prior to a meeting/audit.
   - ATTEND_BY: Physical or virtual attendance at an event.
   - COMMUNICATE_BY: Acknowledgement or reply deadline.
   - STANDALONE: Routine task without an explicit calendar deadline.
4. Ground every assertion strictly in the provided email text. Do not invent dates or consequences.
"""

class LLMService(AIService):
    """Configurable Multi-Provider LLM Service Adapter.
    
    Supports:
    - OpenAI (and OpenAI-compatible endpoints e.g. Ollama, Groq, vLLM)
    - Google Gemini (REST generateContent)
    - Anthropic (Messages API)
    - Deterministic MockAIService fallback for 100% uptime
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        fallback_to_mock: Optional[bool] = None
    ):
        self.provider = (provider or settings.LLM_PROVIDER or "openai").lower()
        self.api_key = api_key if api_key is not None else settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL or "gpt-4o-mini"
        self.base_url = base_url if base_url is not None else settings.LLM_BASE_URL
        self.temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE
        self.fallback_to_mock = (
            fallback_to_mock if fallback_to_mock is not None else settings.LLM_FALLBACK_ON_ERROR
        )
        self.timeout = settings.LLM_TIMEOUT
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.mock_service = MockAIService()
        self.evidence_service = EvidenceValidationService()

    @property
    def is_configured(self) -> bool:
        """Check if active provider has an API key configured or is mock mode."""
        if self.provider == "mock":
            return True
        return bool(self.api_key and self.api_key.strip())

    @property
    def masked_key(self) -> str:
        """Return masked key for safe debugging without exposing secrets."""
        if not self.api_key:
            return "Not Configured"
        if len(self.api_key) <= 8:
            return "********"
        return f"{self.api_key[:4]}...{self.api_key[-4:]}"

    def analyze_email(
        self,
        subject: str,
        body: str,
        sender: str,
        received_at: Optional[datetime] = None
    ) -> AIServiceOutput:
        """Analyze email using configured LLM provider with schema validation and fallback."""
        # 1. Check if mock provider is explicitly selected or credentials missing
        if self.provider == "mock" or not self.is_configured:
            if self.fallback_to_mock:
                logger.info(
                    "LLM provider '%s' has no valid API key (masked: %s); routing to deterministic MockAIService.",
                    self.provider, self.masked_key
                )
                return self.mock_service.analyze_email(subject, body, sender, received_at)
            raise ValueError(
                f"LLM API key not configured for provider '{self.provider}'. "
                "Set LLM_API_KEY or enable LLM_FALLBACK_ON_ERROR."
            )

        # 2. Dispatch to designated provider
        try:
            raw_response_text = self._dispatch_llm_request(subject, body, sender, received_at)
            parsed_json = self._extract_json(raw_response_text)
            validated_output = self._validate_and_ground_output(
                parsed_json=parsed_json,
                raw_text=f"{subject}\n{body}",
                received_at=received_at
            )
            return validated_output

        except Exception as exc:
            redacted_error = SensitiveDataFilter.redact_text(str(exc))
            logger.warning(
                "LLM execution failed for provider '%s' (model: %s): %s",
                self.provider, self.model, redacted_error
            )
            if self.fallback_to_mock:
                logger.info("Falling back to deterministic MockAIService due to LLM failure.")
                return self.mock_service.analyze_email(subject, body, sender, received_at)
            raise

    def _build_user_prompt(
        self,
        subject: str,
        body: str,
        sender: str,
        received_at: Optional[datetime] = None
    ) -> str:
        """Construct structured user prompt with email transmission context."""
        timestamp_str = received_at.isoformat() if received_at else datetime.now().isoformat()
        return (
            f"EMAIL HEADERS & TRANSMISSION CONTEXT:\n"
            f"- SENDER: {sender}\n"
            f"- RECEIVED_AT: {timestamp_str}\n"
            f"- SUBJECT: {subject}\n\n"
            f"EMAIL BODY:\n{body}\n\n"
            f"Extract all intelligence strictly into the requested JSON schema."
        )

    def _dispatch_llm_request(
        self,
        subject: str,
        body: str,
        sender: str,
        received_at: Optional[datetime] = None
    ) -> str:
        """Send HTTP request to provider API via httpx."""
        user_prompt = self._build_user_prompt(subject, body, sender, received_at)

        if self.provider == "openai":
            return self._call_openai(user_prompt)
        elif self.provider == "gemini":
            return self._call_gemini(user_prompt)
        elif self.provider == "anthropic":
            return self._call_anthropic(user_prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _build_priority_prompt(
        self,
        subject: str,
        body: str,
        sender: str,
        sender_role: Optional[str] = None,
        category: Optional[str] = None,
        deadline: Optional[str] = None,
        meeting: Optional[Dict[str, Any]] = None,
        actions: Optional[List[str]] = None,
        reference_date: Optional[datetime] = None
    ) -> str:
        ref_str = reference_date.strftime("%Y-%m-%d") if reference_date else datetime.now().strftime("%Y-%m-%d")
        meeting_desc = "None"
        if meeting:
            m_title = meeting.get("title", "Meeting")
            m_date = meeting.get("date", "")
            m_loc = meeting.get("location", "")
            meeting_desc = f"{m_title} on {m_date} at {m_loc}".strip()

        actions_str = ", ".join(actions) if actions else "None"

        return (
            f"EMAIL CONTEXT & EXTRACTED METADATA:\n"
            f"- SENDER: {sender}\n"
            f"- SENDER ROLE / AUTHORITY: {sender_role or 'ROUTINE'}\n"
            f"- DOMAIN CATEGORY: {category or 'General'}\n"
            f"- REFERENCE DATE (TODAY): {ref_str}\n"
            f"- EXTRACTED DEADLINE: {deadline or 'None'}\n"
            f"- SCHEDULED MEETING: {meeting_desc}\n"
            f"- EXTRACTED ACTIONS: {actions_str}\n\n"
            f"EMAIL HEADERS:\n"
            f"Subject: {subject}\n\n"
            f"EMAIL BODY:\n"
            f"{body}\n\n"
            f"Evaluate the 10 contextual dimensions (especially mandatory vs voluntary and consequence of non-action) "
            f"and determine priority, confidence, and contextual reason."
        )

    def classify_priority(
        self,
        subject: str,
        body: str,
        sender: str,
        sender_role: Optional[str] = None,
        category: Optional[str] = None,
        deadline: Optional[str] = None,
        meeting: Optional[Dict[str, Any]] = None,
        actions: Optional[List[str]] = None,
        reference_date: Optional[datetime] = None
    ) -> AIPriorityResult:
        """Context-Aware AI Priority Classification using configured LLM.
        
        Evaluates urgency, deadline proximity, required actions (mandatory vs voluntary),
        institutional stakes, audience scope, routine communications, and consequences.
        """
        if self.provider == "mock" or not self.is_configured:
            raise RuntimeError(f"LLM provider '{self.provider}' is not configured for direct API calls.")

        user_prompt = self._build_priority_prompt(
            subject=subject,
            body=body,
            sender=sender,
            sender_role=sender_role,
            category=category,
            deadline=deadline,
            meeting=meeting,
            actions=actions,
            reference_date=reference_date
        )

        if self.provider == "openai":
            raw_response_text = self._call_openai(user_prompt, system_prompt=PRIORITY_SYSTEM_PROMPT)
        elif self.provider == "gemini":
            raw_response_text = self._call_gemini(user_prompt, system_prompt=PRIORITY_SYSTEM_PROMPT)
        elif self.provider == "anthropic":
            raw_response_text = self._call_anthropic(user_prompt, system_prompt=PRIORITY_SYSTEM_PROMPT)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

        parsed_json = self._extract_json(raw_response_text)

        priority_str = str(parsed_json.get("priority", "MEDIUM")).upper().strip()
        if priority_str not in ["HIGH", "MEDIUM", "LOW"]:
            priority_str = "MEDIUM"

        confidence_val = float(parsed_json.get("confidence", 0.9))
        confidence_val = max(0.0, min(1.0, confidence_val))

        reason_val = str(parsed_json.get("reason") or parsed_json.get("priority_reason") or "Contextual AI priority classification").strip()
        if reason_val:
            reason_val = reason_val[0].upper() + reason_val[1:]

        return AIPriorityResult(
            priority=priority_str,
            confidence=confidence_val,
            reason=reason_val
        )

    def _call_openai(self, user_prompt: str, system_prompt: Optional[str] = None) -> str:
        """Invoke OpenAI or OpenAI-compatible Chat Completions API."""
        base = self.base_url.rstrip("/") if self.base_url else "https://api.openai.com/v1"
        endpoint = f"{base}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        sys_p = system_prompt or SYSTEM_PROMPT
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sys_p},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"}
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _call_gemini(self, user_prompt: str, system_prompt: Optional[str] = None) -> str:
        """Invoke Google Gemini REST generateContent API securely via headers."""
        base = self.base_url.rstrip("/") if self.base_url else "https://generativelanguage.googleapis.com/v1beta"
        endpoint = f"{base}/models/{self.model}:generateContent"

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        sys_p = system_prompt or SYSTEM_PROMPT
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{sys_p}\n\n{user_prompt}"}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens
            }
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    def _call_anthropic(self, user_prompt: str, system_prompt: Optional[str] = None) -> str:
        """Invoke Anthropic Messages API."""
        base = self.base_url.rstrip("/") if self.base_url else "https://api.anthropic.com/v1"
        endpoint = f"{base}/messages"

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        sys_p = system_prompt or SYSTEM_PROMPT
        payload = {
            "model": self.model,
            "system": sys_p,
            "messages": [
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    def _extract_json(self, raw_text: str) -> Dict[str, Any]:
        """Extract valid JSON object from LLM response text, stripping markdown tags."""
        text = raw_text.strip()

        # Check for ```json ... ``` markdown codeblocks
        codeblock_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if codeblock_match:
            text = codeblock_match.group(1).strip()

        # Locate outer JSON object boundaries
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            text = text[first_brace:last_brace + 1]

        try:
            return json.loads(text)
        except json.JSONDecodeError as err:
            raise ValueError(f"Failed to parse LLM response as JSON: {err}. Raw text: {raw_text[:200]}")

    def _validate_and_ground_output(
        self,
        parsed_json: Dict[str, Any],
        raw_text: str,
        received_at: Optional[datetime] = None
    ) -> AIServiceOutput:
        """Validate parsed JSON against AIServiceOutput schema and ground evidences."""
        # Ensure meeting structure format
        if "meeting" in parsed_json and isinstance(parsed_json["meeting"], dict):
            # Normalize field names if LLM returned venue instead of location
            if "venue" in parsed_json["meeting"] and "location" not in parsed_json["meeting"]:
                parsed_json["meeting"]["location"] = parsed_json["meeting"].pop("venue")

        # Validate with Pydantic
        output = AIServiceOutput.model_validate(parsed_json)

        # Synchronize Stage 21 deadline status
        if output.deadline:
            output.deadline_date = output.deadline
            if not output.deadline_status:
                from backend.app.utils.date_parser import compute_temporal_status
                output.deadline_status, _ = compute_temporal_status(output.deadline)

        # Synchronize action_items strings if structured_actions were provided
        if output.structured_actions and not output.action_items:
            output.action_items = [act.description for act in output.structured_actions]

        # Bidirectional Evidence Grounding Post-Processing
        grounded_evidences = []
        for ev in output.evidence:
            validation = self.evidence_service.validate_assertion(
                field_name=ev.field_name,
                extracted_value=ev.extracted_value,
                raw_text=raw_text
            )
            grounded_evidences.append(
                AIEvidenceOutput(
                    field_name=ev.field_name,
                    extracted_value=ev.extracted_value,
                    source_text=validation.get("grounded_sentence") or "",
                    confidence=validation["confidence"],
                    validation_status=validation["validation_status"],
                    char_start=validation["char_start"],
                    char_end=validation["char_end"],
                    grounding_method=validation["grounding_method"]
                )
            )

        # If LLM didn't return evidence items, auto-ground the core extractions
        if not grounded_evidences:
            if output.deadline:
                val = self.evidence_service.validate_assertion("deadline", output.deadline, raw_text)
                grounded_evidences.append(
                    AIEvidenceOutput(
                        field_name="deadline",
                        extracted_value=output.deadline,
                        source_text=val.get("grounded_sentence") or "",
                        confidence=val["confidence"],
                        validation_status=val["validation_status"],
                        char_start=val["char_start"],
                        char_end=val["char_end"],
                        grounding_method=val["grounding_method"]
                    )
                )
            for act in output.structured_actions[:3]:
                val = self.evidence_service.validate_assertion("action", act.description, raw_text)
                grounded_evidences.append(
                    AIEvidenceOutput(
                        field_name="action",
                        extracted_value=act.description,
                        source_text=val.get("grounded_sentence") or "",
                        confidence=val["confidence"],
                        validation_status=val["validation_status"],
                        char_start=val["char_start"],
                        char_end=val["char_end"],
                        grounding_method=val["grounding_method"]
                    )
                )

        output.evidence = grounded_evidences
        return output

