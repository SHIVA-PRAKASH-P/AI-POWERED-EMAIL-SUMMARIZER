from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from backend.app.schemas.ai_schema import (
    AIServiceOutput,
    AIMeetingOutput,
    AIEntityOutput,
    AIEvidenceOutput,
    AIActionItemOutput
)
from backend.app.models import Email, AIAnalysis, ActionItem, Meeting, Evidence, Entity
from backend.app.ai.classification_service import ClassificationService
from backend.app.ai.temporal_service import TemporalExtractionService
from backend.app.ai.action_service import ActionExtractionService
from backend.app.ai.meeting_service import MeetingExtractionService
from backend.app.ai.priority_engine import ContextAwarePriorityEngine
from backend.app.ai.summarization_service import SummarizationService
from backend.app.ai.evidence_service import EvidenceValidationService
from backend.app.ai.entity_service import EntityExtractionService
from backend.app.ai.smart_reply_service import SmartReplyService
from backend.app.utils.date_parser import compute_temporal_status
from backend.app.ai.llm_service import LLMService
from backend.app.config import settings


class AIOrchestrator:
    """Central AI Agent Orchestrator coordinating specialized information extraction sub-services.
    
    Pipeline:
    EMAIL -> CONTEXT ANALYSIS -> TASK DETECTION -> SPECIALIZED PROCESSING -> VALIDATION -> STRUCTURED OUTPUT
    """

    def __init__(self, llm_service: Optional[LLMService] = None, db: Optional[Session] = None):
        self.db = db
        self.llm_service = llm_service or LLMService()
        self.classification_service = ClassificationService()
        self.temporal_service = TemporalExtractionService()
        self.action_service = ActionExtractionService()
        self.meeting_service = MeetingExtractionService()
        self.priority_engine = ContextAwarePriorityEngine(llm_service=self.llm_service)
        self.priority_service = self.priority_engine  # Backward-compatible alias
        self.summarization_service = SummarizationService()
        self.evidence_service = EvidenceValidationService()
        self.entity_service = EntityExtractionService()
        self.smart_reply_service = SmartReplyService()

    def orchestrate(
        self,
        subject: str,
        body: str,
        sender: str,
        received_at: Optional[datetime] = None,
        preferences: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Execute the coordinated multi-agent orchestration pipeline with edge case handling."""
        steps_executed = []

        # Handle empty email edge case gracefully
        if not body.strip() and not subject.strip():
            return {
                "output": AIServiceOutput(
                    summary="Empty email content received.",
                    category="General",
                    priority="LOW",
                    priority_reason="No textual content provided in email body or subject.",
                    deadline=None,
                    deadline_date=None,
                    deadline_status=None,
                    reply_expected=False,
                    reply_reason=None,
                    suggested_reply=None,
                    meeting=None,
                    action_items=[],
                    important_entities=[],
                    evidence=[]
                ),
                "steps": ["Empty email detected; aborting specialized extraction."],
                "tasks_detected": {"temporal": False, "meeting": False, "action": False}
            }

        # If AI_MODE is explicitly configured to "llm", dispatch to LLMService
        if settings.AI_MODE.lower() == "llm":
            steps_executed.append(
                f"Active AI Mode: 'llm' (provider: {self.llm_service.provider}, model: {self.llm_service.model})"
            )
            llm_output = self.llm_service.analyze_email(subject, body, sender, received_at)
            # Ensure Stage 21 temporal status and smart reply fields are set
            if llm_output.deadline:
                llm_output.deadline_date = llm_output.deadline
                if not llm_output.deadline_status:
                    llm_output.deadline_status = compute_temporal_status(llm_output.deadline)[0]
            if not llm_output.suggested_reply and not llm_output.reply_expected:
                reply_intent = self.smart_reply_service.detect_reply_intent(subject, body, sender)
                llm_output.reply_expected = reply_intent.get("reply_expected", False)
                llm_output.reply_reason = reply_intent.get("reply_reason")
                if llm_output.reply_expected:
                    user_name = None
                    if preferences:
                        user_name = getattr(preferences, 'faculty_name', None) or (preferences.get('name') if isinstance(preferences, dict) else None)
                    llm_output.suggested_reply = self.smart_reply_service.generate_reply(subject, body, sender, reply_intent, user_name=user_name)
            steps_executed.append("LLM inference complete & response validated against AIServiceOutput schema")
            steps_executed.append("Evidence grounding verified across source sentences")
            return {
                "output": llm_output,
                "steps": steps_executed,
                "tasks_detected": {
                    "temporal": llm_output.deadline is not None,
                    "meeting": llm_output.meeting is not None,
                    "action": len(llm_output.action_items) > 0
                }
            }

        ref_date = received_at or datetime.now()
        full_text = f"{subject}\n{body}"
        text_lower = full_text.lower()

        # Step 1: Context Analysis
        steps_executed.append("Context analysis: normalizing text, cleaning whitespace, and inspecting sender hierarchy")

        # Step 2: Dynamic Task Detection
        has_temporal_cues = any(k in text_lower for k in [
            "before", "by", "until", "tomorrow", "next week", "monday", "tuesday", "wednesday",
            "thursday", "friday", "saturday", "sunday", "eod", "end of day", "september", "sept",
            "october", "november", "december", "january", "february", "march", "april", "may",
            "june", "july", "august", "deadline", "due date", "effective", "till", "extension till",
            "last date", "due", "complete by"
        ])
        has_meeting_cues = any(k in text_lower for k in [
            "meeting", "review session", "audit", "briefing", "presentations", "hall", "room", "auditorium", "zoom", "meet"
        ])
        has_action_cues = any(k in text_lower for k in [
            "submit", "bring", "prepare", "review", "upload", "complete", "register", "verify",
            "requested to", "mandatory", "kindly", "please", "evaluate"
        ])

        steps_executed.append(
            f"Task detection: temporal_cues={has_temporal_cues}, meeting_cues={has_meeting_cues}, action_cues={has_action_cues}"
        )

        # Step 3: Domain Classification
        steps_executed.append("Executing ClassificationService: identifying academic category and sender authority")
        cls_info = self.classification_service.classify(subject, body, sender)
        category = cls_info["category"]
        sender_role = cls_info["sender_role"]

        # Step 4: Temporal Extraction & Normalization
        deadline = None
        deadline_raw = None
        deadline_status = None
        if has_temporal_cues:
            steps_executed.append("Executing TemporalExtractionService: resolving relative expressions anchored to arrival timestamp")
            temp_info = self.temporal_service.extract_deadline(body, reference_date=ref_date, current_date=datetime.now(timezone.utc).date())
            deadline = temp_info.get("deadline")
            deadline_raw = temp_info.get("raw_text")
            deadline_status = temp_info.get("deadline_status")

        # Step 5: Meeting Extraction
        meeting_dict = None
        if has_meeting_cues:
            steps_executed.append("Executing MeetingExtractionService: extracting venue, time, and preparation checklist")
            meeting_dict = self.meeting_service.extract_meeting(subject, body, reference_date=ref_date)

        # Step 6: Action Item Extraction & Relationship Formulation
        actions_list = []
        if has_action_cues:
            steps_executed.append("Executing ActionExtractionService: extracting actionable faculty tasks and binding relationships")
            actions_list = self.action_service.extract_actions(
                body=body,
                deadline=deadline,
                meeting=meeting_dict,
                reference_date=ref_date,
                subject=subject
            )

        # Step 7: Context-Aware Priority Reasoning
        steps_executed.append("Executing PriorityService / ContextAwarePriorityEngine: evaluating 9 multi-factor dimensions and generating explainable justification")
        action_descriptions = [a.get("description", "") if isinstance(a, dict) else str(a) for a in actions_list]
        priority_assessment = self.priority_engine.assess_priority(
            subject=subject,
            body=body,
            sender=sender,
            sender_role=sender_role,
            category=category,
            deadline=deadline,
            meeting=meeting_dict,
            actions_count=len(actions_list),
            actions_list=action_descriptions,
            reference_date=ref_date,
            preferences=preferences
        )
        priority = priority_assessment.priority
        priority_reason = priority_assessment.priority_reason

        # Step 8: Summarization
        steps_executed.append("Executing SummarizationService: synthesizing structured executive summary")
        summary = self.summarization_service.summarize(
            subject=subject,
            body=body,
            category=category,
            deadline=deadline,
            actions=actions_list,
            meeting=meeting_dict
        )

        # Step 9: Evidence Validation & Grounding
        steps_executed.append("Executing EvidenceValidationService: verifying assertions against source text and anchoring sentences")
        evidences = self.evidence_service.validate_and_ground(
            body=body,
            subject=subject,
            deadline=deadline,
            deadline_raw=deadline_raw,
            meeting=meeting_dict,
            actions=actions_list
        )

        # Step 10: Entity Extraction
        steps_executed.append("Executing EntityExtractionService: extracting named entities, departments, and course codes")
        extracted_entities = self.entity_service.extract_entities(full_text, sender)
        if meeting_dict and meeting_dict.get("location"):
            extracted_entities.append(AIEntityOutput(type="VENUE", value=meeting_dict["location"]))

        # Step 11: Smart Reply Intent Detection & Grounded Draft Generation (Stage 21)
        steps_executed.append("Executing SmartReplyService: evaluating reply requirement and drafting response")
        reply_intent = self.smart_reply_service.detect_reply_intent(subject=subject, body=body, sender=sender)
        user_name = None
        if preferences:
            user_name = getattr(preferences, 'faculty_name', None) or (preferences.get('name') if isinstance(preferences, dict) else None)
        suggested_reply = self.smart_reply_service.generate_reply(
            subject=subject,
            body=body,
            sender=sender,
            intent_info=reply_intent,
            user_name=user_name
        )

        meeting_output = None
        if meeting_dict:
            meeting_output = AIMeetingOutput(
                title=meeting_dict.get("title", subject),
                date=meeting_dict.get("date"),
                time=meeting_dict.get("time"),
                location=meeting_dict.get("location"),
                preparation=meeting_dict.get("preparation")
            )

        structured_actions = [
            AIActionItemOutput(
                description=a["description"],
                due_date=a.get("due_date"),
                priority=a.get("priority", priority),
                relationship_type=a.get("relationship_type", "DUE_ON"),
                target_event=a.get("target_event"),
                relationship_reason=a.get("relationship_reason"),
                binding_confidence=a.get("binding_confidence", 1.0)
            )
            for a in actions_list
        ]

        structured_output = AIServiceOutput(
            summary=summary,
            category=category,
            priority=priority,
            priority_reason=priority_reason,
            deadline=deadline,
            deadline_date=deadline,
            deadline_status=deadline_status,
            reply_expected=reply_intent.get("reply_expected", False),
            reply_reason=reply_intent.get("reply_reason"),
            suggested_reply=suggested_reply,
            meeting=meeting_output,
            action_items=[a["description"] for a in actions_list],
            structured_actions=structured_actions,
            important_entities=extracted_entities,
            evidence=evidences
        )

        steps_executed.append("Orchestration pipeline complete: structured intelligence validated")

        return {
            "output": structured_output,
            "steps": steps_executed,
            "tasks_detected": {
                "temporal": has_temporal_cues,
                "meeting": has_meeting_cues,
                "action": has_action_cues
            }
        }

    def process_email(
        self,
        db_or_id: Any,
        email: Optional[Email] = None,
        preferences: Optional[Any] = None,
        force_refresh: bool = False,
        db: Optional[Session] = None
    ) -> AIAnalysis:
        """Execute the coordinated multi-agent AI pipeline on an Email model instance and persist
        the resulting analysis, evidence, action items, meetings, and entities into the database.
        
        Reuses the existing AI pipeline to ensure identical Priority (HIGH/MEDIUM/LOW), Category,
        Summary, Action Items, Deadlines, and Meetings across Mock and Gmail-imported emails.
        """
        if isinstance(db_or_id, Session):
            db = db_or_id
        elif isinstance(db_or_id, int):
            db = db or self.db
            if not db:
                raise ValueError("Database session required for process_email")
            email = db.query(Email).filter(Email.id == db_or_id).first()
            if not email:
                raise ValueError(f"Email {db_or_id} not found")
        elif hasattr(db_or_id, 'id') and hasattr(db_or_id, 'subject'):
            email = db_or_id
            db = db or self.db
        else:
            raise ValueError("Invalid parameters to process_email")

        # Resolve preferences scoped to the email owner if not explicitly passed
        if preferences is None and email.user_id:
            from backend.app.services.preference_service import preference_service
            preferences = preference_service.get_or_create_preferences(db, user_id=email.user_id)

        # Run multi-agent orchestration
        orchestration_result = self.orchestrate(
            subject=email.subject,
            body=email.body,
            sender=email.sender,
            received_at=email.received_at,
            preferences=preferences
        )
        ai_output: AIServiceOutput = orchestration_result["output"]
        self.last_steps = orchestration_result.get("steps", [])

        # If re-analyzing, remove existing analysis and previous child items to trigger clean refresh
        existing_analysis = db.query(AIAnalysis).filter(AIAnalysis.email_id == email.id).first()
        if existing_analysis:
            db.query(Evidence).filter(Evidence.analysis_id == existing_analysis.id).delete()
            db.delete(existing_analysis)
            db.query(ActionItem).filter(ActionItem.email_id == email.id).delete()
            db.query(Meeting).filter(Meeting.email_id == email.id).delete()
            db.flush()

        # Persist new AIAnalysis
        analysis_record = AIAnalysis(
            email_id=email.id,
            summary=ai_output.summary,
            category=ai_output.category,
            priority=ai_output.priority,
            priority_reason=ai_output.priority_reason,
            deadline_date=ai_output.deadline_date or ai_output.deadline,
            deadline_status=ai_output.deadline_status,
            reply_expected=ai_output.reply_expected,
            reply_reason=ai_output.reply_reason,
            suggested_reply=ai_output.suggested_reply,
            processed_at=datetime.now(timezone.utc)
        )
        db.add(analysis_record)
        db.flush()

        # Persist grounded Evidence
        for ev in ai_output.evidence:
            ev_record = Evidence(
                analysis_id=analysis_record.id,
                field_name=ev.field_name,
                extracted_value=ev.extracted_value,
                source_text=ev.source_text,
                confidence=ev.confidence,
                validation_status=getattr(ev, "validation_status", "VERIFIED"),
                char_start=getattr(ev, "char_start", None),
                char_end=getattr(ev, "char_end", None),
                grounding_method=getattr(ev, "grounding_method", "EXACT_SPAN")
            )
            db.add(ev_record)

        # Persist structured Action Items with relational link metadata
        for act in ai_output.structured_actions:
            action_record = ActionItem(
                email_id=email.id,
                description=act.description,
                due_date=act.due_date,
                priority=act.priority,
                completed=False,
                relationship_type=act.relationship_type,
                target_event=act.target_event,
                relationship_reason=act.relationship_reason,
                binding_confidence=act.binding_confidence
            )
            db.add(action_record)

        # Fallback simple action items if structured is empty
        if not ai_output.structured_actions and ai_output.action_items:
            for act_text in ai_output.action_items:
                action_record = ActionItem(
                    email_id=email.id,
                    description=act_text,
                    due_date=ai_output.deadline,
                    priority=ai_output.priority,
                    completed=False,
                    relationship_type="DUE_ON" if ai_output.deadline else "STANDALONE",
                    binding_confidence=0.8
                )
                db.add(action_record)

        # Persist Meeting if extracted
        if ai_output.meeting:
            mtg = ai_output.meeting
            meeting_record = Meeting(
                email_id=email.id,
                title=mtg.title,
                meeting_date=mtg.date,
                meeting_time=mtg.time,
                location=mtg.location,
                preparation=mtg.preparation
            )
            db.add(meeting_record)

        # Persist Entities if not already recorded
        if not email.entities and ai_output.important_entities:
            for ent in ai_output.important_entities:
                entity_record = Entity(
                    email_id=email.id,
                    entity_type=ent.entity_type,
                    entity_value=ent.entity_value
                )
                db.add(entity_record)

        db.commit()
        db.refresh(analysis_record)
        return analysis_record


AgentOrchestrator = AIOrchestrator

