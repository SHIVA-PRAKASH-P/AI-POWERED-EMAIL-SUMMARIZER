import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from backend.app.utils.date_parser import normalize_temporal_expression

class ActionDeadlineMapper:
    """Specialized engine for Action-Deadline Semantic Relationship Mapping.
    
    Patent & Research Concept:
    Rather than treating extracted actions and deadlines as disconnected entities,
    this engine formulates explicit typed semantic edges:
        ACTION -(RELATIONSHIP)-> DEADLINE / EVENT
    
    Supported Relationship Types:
    - DUE_ON: Direct submission or task completion by a hard deadline.
    - PREPARE_BEFORE: Prerequisite materials/actions required before a meeting/event.
    - ATTEND_BY: Physical or virtual attendance obligations at a scheduled event.
    - COMMUNICATE_BY: Confirmation, nomination, or feedback response required by a date.
    - STANDALONE: Routine operational tasks without a temporal constraint.
    """

    SUBMISSION_VERBS = [
        "submit", "upload", "enter", "forward", "hand over", "dispatch",
        "file", "send", "finalize", "deliver", "turn in", "provide"
    ]

    PREPARATION_VERBS = [
        "bring", "prepare", "carry", "compile", "draft", "print", "collate",
        "review", "read", "assemble", "gather", "organize"
    ]

    PREPARATION_CONTEXT_TOKENS = [
        "mark sheet", "attendance", "syllabus", "curriculum", "notes", "slides",
        "files", "dossier", "documents", "reports", "agenda", "question paper",
        "log", "rubric", "presentation"
    ]

    ATTENDANCE_VERBS = [
        "attend", "be present", "join", "participate", "report to", "report at"
    ]

    COMMUNICATION_VERBS = [
        "confirm", "reply", "notify", "inform", "nominate", "revert", "respond"
    ]

    def map_relationships(
        self,
        actions: List[Dict[str, Any]],
        body: str,
        subject: str = "",
        reference_date: Optional[datetime] = None,
        email_deadline: Optional[str] = None,
        meeting: Optional[Dict[str, Any]] = None,
        default_priority: str = "MEDIUM"
    ) -> List[Dict[str, Any]]:
        """Map candidate actions to their corresponding deadlines and events with explicit reasons."""
        ref_date = reference_date or datetime.now()
        mapped_actions = []

        for action in actions:
            desc = action.get("description", "").strip()
            source_text = action.get("source_text", desc)
            act_priority = action.get("priority", default_priority)

            desc_lower = desc.lower()
            source_lower = source_text.lower()

            # 1. Intra-clausal Temporal Extraction: Check if the action's source sentence has its own date
            local_date, local_raw, local_conf = normalize_temporal_expression(source_text, reference_date=ref_date)

            relationship_type = "STANDALONE"
            due_date = None
            target_event = None
            relationship_reason = ""
            binding_confidence = 0.85

            if local_date:
                # Local sentence contains an explicit or relative temporal expression
                due_date = local_date
                binding_confidence = min(0.98, local_conf + 0.05)

                if any(re.search(rf"\b{v}\b", desc_lower) for v in self.ATTENDANCE_VERBS):
                    relationship_type = "ATTEND_BY"
                    target_event = meeting.get("title") if meeting else "Scheduled Event"
                    relationship_reason = (
                        f"Event attendance obligation bound to local clause temporal expression "
                        f"'{local_raw}' resolving to {local_date}."
                    )
                elif any(re.search(rf"\b{v}\b", desc_lower) for v in self.COMMUNICATION_VERBS):
                    relationship_type = "COMMUNICATE_BY"
                    relationship_reason = (
                        f"Communication requirement bound to local clause deadline expression "
                        f"'{local_raw}' resolving to {local_date}."
                    )
                elif any(re.search(rf"\b{v}\b", desc_lower) for v in self.PREPARATION_VERBS) and meeting:
                    relationship_type = "PREPARE_BEFORE"
                    target_event = meeting.get("title", "Review Meeting")
                    relationship_reason = (
                        f"Meeting preparation bound to local temporal expression "
                        f"'{local_raw}' ({local_date}) for event '{target_event}'."
                    )
                else:
                    relationship_type = "DUE_ON"
                    relationship_reason = (
                        f"Action bound to explicit local clause deadline "
                        f"'{local_raw}' resolving to {local_date}."
                    )

            elif meeting and (
                any(re.search(rf"\b{v}\b", desc_lower) for v in self.PREPARATION_VERBS) or
                any(t in desc_lower for t in self.PREPARATION_CONTEXT_TOKENS)
            ):
                # Prerequisite material preparation tied to an upcoming meeting
                meeting_title = meeting.get("title", "Scheduled Meeting")
                meeting_date = meeting.get("date")
                relationship_type = "PREPARE_BEFORE"
                due_date = meeting_date
                target_event = meeting_title
                binding_confidence = 0.94
                relationship_reason = (
                    f"Prerequisite preparation bound to scheduled meeting '{meeting_title}'"
                    + (f" on {meeting_date}" if meeting_date else "") + "."
                )

            elif meeting and any(re.search(rf"\b{v}\b", desc_lower) for v in self.ATTENDANCE_VERBS):
                # Meeting attendance obligation
                meeting_title = meeting.get("title", "Scheduled Meeting")
                meeting_date = meeting.get("date")
                relationship_type = "ATTEND_BY"
                due_date = meeting_date
                target_event = meeting_title
                binding_confidence = 0.95
                relationship_reason = (
                    f"Mandatory attendance obligation bound to scheduled meeting '{meeting_title}'"
                    + (f" on {meeting_date}" if meeting_date else "") + "."
                )

            elif email_deadline and any(re.search(rf"\b{v}\b", desc_lower) for v in self.COMMUNICATION_VERBS):
                # Communication / feedback bound to primary email deadline
                relationship_type = "COMMUNICATE_BY"
                due_date = email_deadline
                binding_confidence = 0.89
                relationship_reason = f"Response/confirmation obligation bound to primary deadline {email_deadline}."

            elif email_deadline and (
                any(re.search(rf"\b{v}\b", desc_lower) for v in self.SUBMISSION_VERBS) or
                any(k in desc_lower for k in ["deadline", "marks", "report", "proposal", "dossier", "exam", "grade", "syllabus"])
            ):
                # Core submission bound to primary email deadline
                relationship_type = "DUE_ON"
                due_date = email_deadline
                binding_confidence = 0.90
                relationship_reason = f"Submission task bound to primary document deadline {email_deadline}."

            elif email_deadline and not meeting:
                # Single action in email with deadline: bind as DUE_ON by default
                relationship_type = "DUE_ON"
                due_date = email_deadline
                binding_confidence = 0.82
                relationship_reason = f"General task linked to primary document deadline {email_deadline}."

            else:
                # Standalone routine task without specific temporal dependency
                relationship_type = "STANDALONE"
                due_date = None
                target_event = None
                binding_confidence = 0.90
                relationship_reason = "Routine academic/administrative task with no strict temporal or event dependency."

            mapped_actions.append({
                "description": desc,
                "due_date": due_date,
                "priority": act_priority,
                "completed": action.get("completed", False),
                "relationship_type": relationship_type,
                "target_event": target_event,
                "relationship_reason": relationship_reason,
                "binding_confidence": round(binding_confidence, 2),
                "source_text": source_text
            })

        return mapped_actions
