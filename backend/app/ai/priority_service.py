from typing import Dict, Any, Optional

class PriorityService:
    """Specialized agent sub-service for explainable context-aware priority determination."""

    def evaluate_priority(
        self,
        subject: str,
        body: str,
        sender_role: str = "ROUTINE",
        category: str = "General",
        deadline: Optional[str] = None,
        has_meeting: bool = False,
        actions_count: int = 0,
        sender: Optional[str] = None,
        preferences: Optional[Any] = None
    ) -> Dict[str, str]:
        from backend.app.ai.priority_engine import ContextAwarePriorityEngine
        engine = ContextAwarePriorityEngine()
        assessment = engine.assess_priority(
            subject=subject,
            body=body,
            sender=sender or "",
            sender_role=sender_role,
            category=category,
            deadline=deadline,
            meeting={"date": "2026-09-08"} if has_meeting else None,
            actions_count=actions_count,
            preferences=preferences
        )
        return {
            "priority": assessment.priority,
            "priority_reason": assessment.priority_reason
        }
