from datetime import datetime
from typing import List, Dict, Any, Optional
import re

from backend.app.ai.relationship_mapper import ActionDeadlineMapper

class ActionExtractionService:
    """Specialized agent sub-service for detecting actionable faculty obligations and mapping relationships."""

    IMPERATIVE_VERBS = [
        "submit", "bring", "prepare", "review", "verify", "upload", "complete",
        "register", "conduct", "attend", "forward", "coordinate", "evaluate",
        "check", "ensure", "nominate", "confirm", "send"
    ]

    def __init__(self):
        self.relationship_mapper = ActionDeadlineMapper()

    def extract_actions(
        self,
        body: str,
        deadline: Optional[str] = None,
        meeting: Optional[Dict[str, Any]] = None,
        reference_date: Optional[datetime] = None,
        priority: str = "MEDIUM",
        subject: str = ""
    ) -> List[Dict[str, Any]]:
        raw_actions = []
        sentences = [s.strip() for s in re.split(r'[\n\.\?!]', body) if len(s.strip()) > 8]

        for s in sentences:
            s_lower = s.lower().strip()
            # Strip leading conversational conjuncts (also, additionally, furthermore, and)
            core_sentence = re.sub(r'^(?:also|additionally|furthermore|and|note that)\s+', '', s_lower).strip()

            # Match sentences starting with imperative requests or containing polite directives
            is_action = False
            if any(re.search(rf'\b{verb}\b', core_sentence) for verb in self.IMPERATIVE_VERBS):
                if any(prefix in core_sentence for prefix in [
                    "requested to", "mandatory to", "strictly mandatory", "please", "kindly", "must",
                    "should", "required to", "all members", "all faculty", "all professors",
                    "need to", "instructed to", "directed to"
                ]):
                    is_action = True
                elif any(core_sentence.startswith(verb) for verb in self.IMPERATIVE_VERBS):
                    is_action = True

            if is_action:
                # Clean up leading fillers
                cleaned = re.sub(
                    r'^(?:all members are requested to|all faculty are requested to|please|kindly|it is strictly mandatory to|you are requested to|also|additionally|furthermore)\s+',
                    '',
                    s,
                    flags=re.IGNORECASE
                ).strip()
                if cleaned:
                    task_text = cleaned[0].upper() + cleaned[1:]
                    raw_actions.append({
                        "description": task_text,
                        "source_text": s,
                        "priority": priority,
                        "completed": False
                    })

        # De-duplicate while preserving order
        unique_raw = []
        seen = set()
        for a in raw_actions:
            key = a["description"][:35].lower()
            if key not in seen:
                seen.add(key)
                unique_raw.append(a)

        candidate_actions = unique_raw[:4]

        # Stage 8: Formulate relational edges via ActionDeadlineMapper
        mapped_actions = self.relationship_mapper.map_relationships(
            actions=candidate_actions,
            body=body,
            subject=subject,
            reference_date=reference_date,
            email_deadline=deadline,
            meeting=meeting,
            default_priority=priority
        )

        return mapped_actions
