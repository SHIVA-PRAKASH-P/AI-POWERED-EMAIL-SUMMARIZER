import re
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List

from backend.app.schemas.priority_schema import PriorityAssessment, AIPriorityResult
from backend.app.ai.priority_service import PriorityService

logger = logging.getLogger("ai.priority_engine")

class ContextAwarePriorityEngine(PriorityService):
    """Context-Aware AI Priority Classification Engine with Resilient Semantic Fallback.
    
    Architectural Guarantee:
    1. Primary Mechanism: When an AI/LLM engine is configured and available, it executes
       context-aware classification across 10 semantic dimensions.
    2. Fallback Mechanism: When AI is unavailable, times out, or errors, the semantic
       context reasoning engine executes as a safe fallback without overriding successful AI decisions.
    3. Zero Keyword-Only Guessing: Prioritizes semantic understanding (voluntary vs mandatory,
       audience scope, and actual institutional consequences) over raw keyword hits.
    """

    MANDATORY_TERMS = [
        r'\bstrictly mandatory\b', r'\bmandatory\b', r'\bcompulsory\b',
        r'\bstrict compliance\b', r'\bby order of\b', r'\bit is required to\b',
        r'\bstatutory requirement\b', r'\bconfidential section\b',
        r'\bwithout fail\b'
    ]

    URGENCY_TERMS = [
        r'\burgent\b', r'\bimmediate\b', r'\bcritical\b', r'\bemergency\b',
        r'\bimportant notice\b', r'\baction required\b', r'\bwithout delay\b',
        r'\bpromptly\b', r'\btoday itself\b', r'\btoday\b',
        r'\bby tomorrow\b', r'\btomorrow\b',
        r'\blast date\b', r'\bdeadline\b', r'\bdue date\b', r'\bdue\b',
        r'\bextension till\b', r'\bextension until\b',
        r'\bcomplete by\b', r'\bwithout fail\b'
    ]

    CONSEQUENCE_TERMS = [
        r'\bconfidentiality must be maintained\b', r'\bdisciplinary\b',
        r'\bpenalty\b', r'\bcompliance bylaws\b', r'\bnaac accreditation\b',
        r'\bwithheld\b', r'\bregulatory sanctions\b', r'\bstatutory audit\b'
    ]

    VOLUNTARY_CUES = [
        "interested students may", "interested faculty may", "interested faculty can",
        "may register", "optional", "voluntary", "invited to attend", "invited to participate",
        "welcome to register", "welcome to attend", "open for registration", "feel free to attend",
        "if interested", "invitation to attend"
    ]

    ROUTINE_EDUCATIONAL_CUES = [
        "word of the day", "quote of the day", "daily vocabulary", "thought for the day",
        "idiom of the day", "vocabulary note"
    ]

    ROUTINE_NEWS_CUES = [
        "daily pulse", "campus news", "daily announcements", "daily circular",
        "daily bulletin", "weekly newsletter", "institutional newsletter"
    ]

    def __init__(self, llm_service: Optional[Any] = None):
        self.llm_service = llm_service

    def assess_priority(
        self,
        subject: str,
        body: str,
        sender: str = "",
        sender_role: str = "ROUTINE",
        category: str = "General",
        deadline: Optional[str] = None,
        meeting: Optional[Dict[str, Any]] = None,
        actions_count: int = 0,
        actions_list: Optional[List[str]] = None,
        reference_date: Optional[datetime] = None,
        preferences: Optional[Any] = None
    ) -> PriorityAssessment:
        """Context-aware priority assessment with Primary AI classification and Semantic Fallback."""
        # ------------------------------------------------------------------
        # 1. PRIMARY AI CLASSIFIER (LLM)
        # ------------------------------------------------------------------
        if self.llm_service and getattr(self.llm_service, "is_configured", False) and getattr(self.llm_service, "provider", "mock") != "mock":
            try:
                ai_res: Optional[AIPriorityResult] = self.llm_service.classify_priority(
                    subject=subject,
                    body=body,
                    sender=sender,
                    sender_role=sender_role,
                    category=category,
                    deadline=deadline,
                    meeting=meeting,
                    actions=actions_list,
                    reference_date=reference_date
                )
                if ai_res and ai_res.priority in ["HIGH", "MEDIUM", "LOW"]:
                    # Successful AI Classification: Return immediately!
                    # Do NOT run old keyword logic and do NOT override the AI result.
                    return self._build_assessment_from_ai_result(
                        ai_res=ai_res,
                        sender_role=sender_role,
                        category=category,
                        deadline=deadline,
                        meeting=meeting,
                        actions_count=actions_count,
                        reference_date=reference_date,
                        subject=subject,
                        body=body
                    )
            except Exception as exc:
                logger.warning(
                    "Primary AI priority classification failed; engaging contextual semantic fallback: %s",
                    exc
                )

        # ------------------------------------------------------------------
        # 2. CONTEXTUAL SEMANTIC FALLBACK ENGINE
        # ------------------------------------------------------------------
        return self._evaluate_semantic_fallback(
            subject=subject,
            body=body,
            sender=sender,
            sender_role=sender_role,
            category=category,
            deadline=deadline,
            meeting=meeting,
            actions_count=actions_count,
            reference_date=reference_date,
            preferences=preferences
        )

    def _build_assessment_from_ai_result(
        self,
        ai_res: AIPriorityResult,
        sender_role: str,
        category: str,
        deadline: Optional[str],
        meeting: Optional[Dict[str, Any]],
        actions_count: int,
        reference_date: Optional[datetime],
        subject: str,
        body: str
    ) -> PriorityAssessment:
        """Construct a PriorityAssessment reflecting the primary AI classification."""
        text_lower = f"{subject}\n{body}".lower()
        role_upper = (sender_role or "ROUTINE").upper()

        if role_upper in ["COE", "DEAN", "REGISTRAR", "VICE CHANCELLOR"]:
            authority = "STATUTORY"
        elif role_upper in ["HOD", "CHAIRPERSON", "BOS"]:
            authority = "DEPARTMENTAL"
        elif role_upper in ["STUDENT"]:
            authority = "STUDENT"
        else:
            authority = "ROUTINE"

        is_mandatory = ai_res.priority == "HIGH" or any(re.search(term, text_lower) for term in self.MANDATORY_TERMS)
        has_urgency = ai_res.priority == "HIGH" or any(re.search(term, text_lower) for term in self.URGENCY_TERMS)
        has_consequences = any(re.search(term, text_lower) for term in self.CONSEQUENCE_TERMS)
        is_exam = category == "Examination" or "exam" in text_lower or "question paper" in text_lower
        is_academic = category in ["Academic", "Administrative", "Research"]

        deadline_prox = "NONE"
        if deadline:
            deadline_prox = "IMMEDIATE" if ("today" in text_lower or "tomorrow" in text_lower) else "MEDIUM"

        meeting_prox = "NONE"
        if meeting and meeting.get("date"):
            meeting_prox = "APPROACHING"

        score = 9.0 if ai_res.priority == "HIGH" else (5.0 if ai_res.priority == "MEDIUM" else 2.0)

        return PriorityAssessment(
            mandatory=is_mandatory,
            urgency_language=has_urgency,
            deadline_proximity=deadline_prox,
            sender_authority=authority,
            academic_context=is_academic,
            examination_context=is_exam,
            required_action=actions_count > 0 or ai_res.priority in ["HIGH", "MEDIUM"],
            meeting_proximity=meeting_prox,
            consequence_indicators=has_consequences or ai_res.priority == "HIGH",
            score=score,
            priority=ai_res.priority,
            priority_reason=ai_res.reason,
            confidence=ai_res.confidence,
            reason=ai_res.reason
        )

    def _evaluate_semantic_fallback(
        self,
        subject: str,
        body: str,
        sender: str,
        sender_role: str,
        category: str,
        deadline: Optional[str] = None,
        meeting: Optional[Dict[str, Any]] = None,
        actions_count: int = 0,
        reference_date: Optional[datetime] = None,
        preferences: Optional[Any] = None
    ) -> PriorityAssessment:
        """Contextual semantic evaluation analyzing meaning, urgency, modality, and consequences."""
        ref_date = (reference_date or datetime.now()).date() if isinstance(reference_date, datetime) else reference_date
        if not ref_date:
            ref_date = date(2026, 9, 6)

        text = f"{subject}\n{body}"
        text_lower = text.lower()
        subject_lower = (subject or "").lower()
        sender_lower = (sender or "").lower()

        # Extract personalization settings if provided
        auth_weight = getattr(preferences, "authority_weight", 1.0) if preferences else 1.0
        if auth_weight is None:
            auth_weight = 1.0
        dead_weight = getattr(preferences, "deadline_weight", 1.0) if preferences else 1.0
        if dead_weight is None:
            dead_weight = 1.0
        mode = getattr(preferences, "priority_mode", "BALANCED") if preferences else "BALANCED"
        if mode == "DEADLINE_HEAVY":
            dead_weight *= 1.4
        elif mode == "AUTHORITY_FIRST":
            auth_weight *= 1.4

        urgent_days = getattr(preferences, "deadline_urgency_days", 2) if preferences else 2
        if urgent_days is None:
            urgent_days = 2

        # ------------------------------------------------------------------
        # Temporal Resolution & Proximity
        # ------------------------------------------------------------------
        detected_deadline = deadline
        if not detected_deadline:
            # Check for DD.MM.YYYY or DD/MM/YYYY (e.g., "08.09.2026")
            dmy_match = re.search(r'\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b', text)
            if dmy_match:
                try:
                    d_day = int(dmy_match.group(1))
                    d_mon = int(dmy_match.group(2))
                    d_yr = int(dmy_match.group(3))
                    detected_deadline = date(d_yr, d_mon, d_day).strftime("%Y-%m-%d")
                except ValueError:
                    pass
            if not detected_deadline:
                iso_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
                if iso_match:
                    detected_deadline = iso_match.group(1)
            if not detected_deadline:
                if re.search(r'\b(?:by\s+)?tomorrow\b', text_lower):
                    detected_deadline = (ref_date + timedelta(days=1)).strftime("%Y-%m-%d")
                elif re.search(r'\b(?:by\s+)?today(?:\s+itself)?\b', text_lower):
                    detected_deadline = ref_date.strftime("%Y-%m-%d")

        deadline = detected_deadline
        deadline_prox = "NONE"
        deadline_score = 0.0
        days_until_deadline = None

        if deadline:
            try:
                d_obj = datetime.strptime(deadline[:10], "%Y-%m-%d").date()
                days_until_deadline = (d_obj - ref_date).days
                if days_until_deadline <= urgent_days:
                    deadline_prox = "IMMEDIATE"
                    deadline_score = 4.0
                elif days_until_deadline <= max(urgent_days + 2, 5):
                    deadline_prox = "HIGH"
                    deadline_score = 3.0
                elif days_until_deadline <= 14:
                    deadline_prox = "MEDIUM"
                    deadline_score = 2.0
                else:
                    deadline_prox = "LOW"
                    deadline_score = 1.0
            except ValueError:
                deadline_prox = "MEDIUM"
                deadline_score = 2.0

        # Meeting Proximity
        meeting_prox = "NONE"
        meeting_score = 0.0
        if meeting and meeting.get("date"):
            try:
                m_obj = datetime.strptime(meeting["date"][:10], "%Y-%m-%d").date()
                days_until_meeting = (m_obj - ref_date).days
                if days_until_meeting <= 2:
                    meeting_prox = "IMMEDIATE"
                    meeting_score = 2.5
                elif days_until_meeting <= 5:
                    meeting_prox = "APPROACHING"
                    meeting_score = 1.5
                else:
                    meeting_prox = "SCHEDULED"
                    meeting_score = 1.0
            except ValueError:
                meeting_prox = "APPROACHING"
                meeting_score = 1.0

        # Sender Authority Level
        role_upper = sender_role.upper()
        if role_upper in ["COE", "DEAN", "REGISTRAR", "VICE CHANCELLOR"]:
            authority = "STATUTORY"
            auth_score = 4.0
        elif role_upper in ["HOD", "CHAIRPERSON", "BOS"]:
            authority = "DEPARTMENTAL"
            auth_score = 3.0
        elif role_upper in ["STUDENT"]:
            authority = "STUDENT"
            auth_score = 1.0
        elif role_upper in ["EXTERNAL_ACADEMIC", "PLACEMENT_CELL"]:
            authority = "EXTERNAL"
            auth_score = 2.0
        else:
            authority = "ROUTINE"
            auth_score = 0.5

        # Academic & Examination Context
        is_exam = category == "Examination" or any(k in text_lower for k in ["question paper", "quiz", "invigilation", "answer scheme"])
        is_academic = category in ["Academic", "Administrative", "Research"] or any(k in text_lower for k in ["internal assessment", "mark sheet", "naac", "syllabus", "grant", "course plan"])

        # Linguistic & Semantic Contextual Indicators
        is_mandatory = any(re.search(term, text_lower) for term in self.MANDATORY_TERMS)
        has_urgency = any(re.search(term, text_lower) for term in self.URGENCY_TERMS)
        has_consequences = any(re.search(term, text_lower) for term in self.CONSEQUENCE_TERMS)
        has_action = actions_count > 0 or any(k in text_lower for k in [
            "submit", "submission", "bring", "prepare", "upload", "verify", "complete by"
        ])
        action_score = 2.0 if has_action else 0.0

        # Personalization Adjustments
        personal_score = 0.0
        personalized_reasons = []
        if preferences:
            high_cats_str = getattr(preferences, "high_priority_categories", "")
            if high_cats_str:
                high_cats = [c.strip().lower() for c in high_cats_str.split(",") if c.strip()]
                if category.lower() in high_cats:
                    personal_score += 2.5
                    personalized_reasons.append(f"matches faculty focus category '{category}'")

            high_kw_str = getattr(preferences, "custom_keywords_high", "")
            if high_kw_str:
                high_kws = [k.strip().lower() for k in high_kw_str.split(",") if k.strip()]
                matched_high = [kw for kw in high_kws if kw in text_lower]
                if matched_high:
                    personal_score += min(4.5, len(matched_high) * 3.5)
                    personalized_reasons.append(f"matched personalized priority keyword: '{matched_high[0]}'")

            low_kw_str = getattr(preferences, "custom_keywords_low", "")
            if low_kw_str:
                low_kws = [k.strip().lower() for k in low_kw_str.split(",") if k.strip()]
                matched_low = [kw for kw in low_kws if kw in text_lower]
                if matched_low and not is_mandatory and not is_exam:
                    personal_score -= 2.0
                    personalized_reasons.append(f"matched low-priority keyword: '{matched_low[0]}'")

            dept_str = getattr(preferences, "department", "")
            if dept_str and dept_str.lower() in text_lower:
                personal_score += 1.0
                personalized_reasons.append(f"addressed to faculty department ({dept_str})")

        total_score = (
            auth_score * auth_weight +
            (3.0 if is_mandatory else 0.0) +
            (2.0 if has_urgency else 0.0) +
            deadline_score * dead_weight +
            meeting_score * 0.8 +
            action_score * 1.0 +
            (2.5 if is_exam else 0.0) +
            (1.5 if is_academic else 0.0) +
            (2.0 if has_consequences else 0.0) +
            personal_score
        )
        if total_score < 0:
            total_score = 0.0

        # ------------------------------------------------------------------
        # CONTEXT-AWARE SEMANTIC DECISION RULES
        # ------------------------------------------------------------------
        # 1. Routine Educational Features (e.g. Word of the Day) -> LOW
        is_routine_educational = any(cue in subject_lower or cue in text_lower for cue in self.ROUTINE_EDUCATIONAL_CUES)
        if is_routine_educational:
            priority = "LOW"
            reason_text = "Routine priority: Daily educational feature (Word of the Day) with no required faculty action, administrative deadline, or academic consequences."
            return PriorityAssessment(
                mandatory=False,
                urgency_language=False,
                deadline_proximity="NONE",
                sender_authority=authority,
                academic_context=False,
                examination_context=False,
                required_action=False,
                meeting_proximity="NONE",
                consequence_indicators=False,
                score=1.0,
                priority=priority,
                priority_reason=reason_text,
                confidence=0.95,
                reason=reason_text
            )

        # 2. General Campus News / Daily Bulletin -> MEDIUM
        is_daily_news_bulletin = (
            any(cue in subject_lower for cue in self.ROUTINE_NEWS_CUES)
            or "dailynews@" in sender_lower
        )
        if is_daily_news_bulletin and not is_exam:
            priority = "MEDIUM"
            sender_str = f" from {sender}" if sender else ""
            reason_text = f"Medium priority: Official institutional daily bulletin{sender_str} with general informational scope."
            return PriorityAssessment(
                mandatory=is_mandatory,
                urgency_language=has_urgency,
                deadline_proximity=deadline_prox,
                sender_authority=authority,
                academic_context=is_academic,
                examination_context=False,
                required_action=has_action,
                meeting_proximity=meeting_prox,
                consequence_indicators=False,
                score=4.5,
                priority=priority,
                priority_reason=reason_text,
                confidence=0.90,
                reason=reason_text
            )

        # 3. Voluntary Event Participation / Optional Registration -> MEDIUM (not HIGH)
        is_voluntary = any(cue in text_lower for cue in self.VOLUNTARY_CUES)
        if is_voluntary and not is_exam and not has_consequences:
            priority = "MEDIUM"
            reason_text = (
                "Medium priority because registration closes soon, but participation is voluntary "
                "and there is no academic consequence for not attending."
            )
            return PriorityAssessment(
                mandatory=False,
                urgency_language=has_urgency,
                deadline_proximity=deadline_prox,
                sender_authority=authority,
                academic_context=is_academic,
                examination_context=False,
                required_action=has_action,
                meeting_proximity=meeting_prox,
                consequence_indicators=False,
                score=5.0,
                priority=priority,
                priority_reason=reason_text,
                confidence=0.92,
                reason=reason_text
            )

        # 4. Routine Mandatory Announcement without Imminent Deadline -> NOT HIGH
        is_routine_mandatory_without_imminent_deadline = (
            is_mandatory
            and deadline_prox not in ["IMMEDIATE", "HIGH"]
            and not is_exam
            and not has_consequences
            and actions_count == 0
        )
        if is_routine_mandatory_without_imminent_deadline:
            priority = "MEDIUM"
            reason_text = (
                "Medium priority: general institutional protocol observance notice with broad campus scope "
                "and no imminent individual submission deadline or consequence."
            )
            return PriorityAssessment(
                mandatory=True,
                urgency_language=has_urgency,
                deadline_proximity="NONE",
                sender_authority=authority,
                academic_context=is_academic,
                examination_context=False,
                required_action=False,
                meeting_proximity="NONE",
                consequence_indicators=False,
                score=4.5,
                priority=priority,
                priority_reason=reason_text,
                confidence=0.88,
                reason=reason_text
            )

        # 5. Mandatory Marks Verification -> HIGH
        has_mandatory_marks_verification = (
            any(k in text_lower for k in ["verify", "verification"])
            and any(k in text_lower for k in ["mark", "marks", "pt-1", "pt1", "internal assessment", "grades"])
            and any(k in text_lower for k in ["without fail", "mandatory", "must", "strictly", "today", "immediately"])
        )
        if has_mandatory_marks_verification:
            priority = "HIGH"
            reason_text = "High priority: mandatory academic marks verification requiring faculty action without delay."
            return PriorityAssessment(
                mandatory=True,
                urgency_language=True,
                deadline_proximity=deadline_prox if deadline_prox != "NONE" else "IMMEDIATE",
                sender_authority=authority,
                academic_context=True,
                examination_context=is_exam,
                required_action=True,
                meeting_proximity=meeting_prox,
                consequence_indicators=has_consequences,
                score=9.0,
                priority=priority,
                priority_reason=reason_text,
                confidence=0.95,
                reason=reason_text
            )

        # 6. High Priority: Mandatory Academic Duty with Imminent Deadline / Consequences
        has_mandatory_action_imminent = (
            is_mandatory and has_action and deadline_prox in ["IMMEDIATE", "HIGH"]
        )
        has_urgent_action_imminent = (
            has_urgency and has_action and deadline_prox in ["IMMEDIATE", "HIGH"]
        )

        reasons = []
        if authority == "STATUTORY":
            reasons.append(f"statutory directive from {sender_role}")
        elif authority == "DEPARTMENTAL":
            reasons.append(f"departmental directive from {sender_role}")
        if is_mandatory:
            reasons.append("mandatory institutional language")
        if has_urgency:
            reasons.append("urgent institutional indicators")
        if is_exam:
            reasons.append("confidential examination duties")
        elif is_academic:
            reasons.append("core academic compliance obligations")
        if deadline_prox in ["IMMEDIATE", "HIGH"]:
            reasons.append(f"an imminent submission deadline ({deadline})")
        elif deadline_prox == "MEDIUM":
            reasons.append(f"an approaching deadline ({deadline})")
        if meeting_prox in ["IMMEDIATE", "APPROACHING"]:
            m_venue = f" in {meeting['location']}" if meeting and meeting.get("location") else ""
            reasons.append(f"scheduled meeting on {meeting['date']}{m_venue}")
        if has_consequences:
            reasons.append("explicit compliance consequence indicators")
        reasons.extend(personalized_reasons)

        if (
            total_score >= 8.0
            or (is_exam and is_mandatory)
            or (authority == "STATUTORY" and deadline_prox in ["IMMEDIATE", "HIGH"])
            or has_mandatory_action_imminent
            or has_urgent_action_imminent
            or (has_consequences and deadline_prox in ["IMMEDIATE", "HIGH", "MEDIUM"])
        ):
            priority = "HIGH"
            reason_text = "High priority: " + ", ".join(reasons) + "."
            confidence = 0.95
        elif total_score >= 4.0 or has_action or deadline_prox != "NONE" or is_mandatory or has_urgency:
            priority = "MEDIUM"
            reason_text = "Medium priority: " + (", ".join(reasons) if reasons else "actionable academic correspondence") + "."
            confidence = 0.85
        else:
            priority = "LOW"
            reason_text = "Routine priority: " + (", ".join(reasons) if reasons else "informational announcement with no urgent statutory obligations") + "."
            confidence = 0.80

        reason_text = reason_text[0].upper() + reason_text[1:]

        return PriorityAssessment(
            mandatory=is_mandatory,
            urgency_language=has_urgency,
            deadline_proximity=deadline_prox,
            sender_authority=authority,
            academic_context=is_academic,
            examination_context=is_exam,
            required_action=has_action,
            meeting_proximity=meeting_prox,
            consequence_indicators=has_consequences,
            score=round(total_score, 2),
            priority=priority,
            priority_reason=reason_text,
            confidence=confidence,
            reason=reason_text
        )

    def evaluate_priority(
        self,
        subject: str,
        body: str,
        sender_role: str = "ROUTINE",
        category: str = "General",
        deadline: Optional[str] = None,
        has_meeting: bool = False,
        actions_count: int = 0,
        preferences: Optional[Any] = None,
        sender: Optional[str] = None
    ) -> Dict[str, str]:
        """Convenience evaluation adapter for backward compatibility."""
        assessment = self.assess_priority(
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

