import re
from datetime import datetime
from typing import Optional, List, Dict, Any

from backend.app.ai.base_service import AIService
from backend.app.ai.relationship_mapper import ActionDeadlineMapper
from backend.app.schemas.ai_schema import (
    AIServiceOutput,
    AIMeetingOutput,
    AIEntityOutput,
    AIEvidenceOutput,
    AIActionItemOutput
)

class MockAIService(AIService):
    """Deterministic, domain-aware mock AI service for faculty email intelligence.
    
    Operates 100% offline without requiring external LLM API credentials, returning
    the exact same structured schema as live generative AI models.
    """

    def analyze_email(
        self,
        subject: str,
        body: str,
        sender: str,
        received_at: Optional[datetime] = None
    ) -> AIServiceOutput:
        raw_output = self._raw_analyze_email(subject, body, sender, received_at)
        actions_enriched = self._enrich_structured_actions(raw_output, body, subject, received_at)
        return self._enrich_stage21(actions_enriched, body, subject, sender)

    def _enrich_stage21(
        self,
        output: AIServiceOutput,
        body: str,
        subject: str,
        sender: str
    ) -> AIServiceOutput:
        from backend.app.ai.smart_reply_service import SmartReplyService
        from backend.app.utils.date_parser import compute_temporal_status

        # 1. Deadline date & dynamic status
        if output.deadline:
            output.deadline_date = output.deadline
            status, _ = compute_temporal_status(output.deadline)
            output.deadline_status = status

        # 2. Smart Reply Intent Detection & Grounded Draft Generation
        reply_service = SmartReplyService()
        intent_info = reply_service.detect_reply_intent(subject, body, sender)
        output.reply_expected = intent_info.get("reply_expected", False)
        output.reply_reason = intent_info.get("reply_reason")
        if output.reply_expected:
            output.suggested_reply = reply_service.generate_reply(subject, body, sender, intent_info)

        # 3. Format structured summary if not already formatted
        if not output.summary.startswith("Summary:"):
            structured_parts = [f"Summary:\n{output.summary}"]
            if output.action_items:
                act = output.action_items[0]
                if act.endswith("."):
                    act = act[:-1]
                structured_parts.append(f"Action:\n{act}.")
            if output.deadline:
                structured_parts.append(f"Deadline:\n{output.deadline}")
            output.summary = "\n\n".join(structured_parts)

        return output

    def _enrich_structured_actions(
        self,
        output: AIServiceOutput,
        body: str,
        subject: str,
        reference_date: Optional[datetime]
    ) -> AIServiceOutput:
        if not output.structured_actions and output.action_items:
            mapper = ActionDeadlineMapper()
            actions = [{"description": a, "source_text": a} for a in output.action_items]
            meeting_dict = None
            if output.meeting:
                meeting_dict = {
                    "title": output.meeting.title,
                    "date": output.meeting.date,
                    "time": output.meeting.time,
                    "location": output.meeting.location,
                    "preparation": output.meeting.preparation
                }
            mapped = mapper.map_relationships(
                actions=actions,
                body=body,
                subject=subject,
                reference_date=reference_date,
                email_deadline=output.deadline,
                meeting=meeting_dict,
                default_priority=output.priority
            )
            output.structured_actions = [
                AIActionItemOutput(
                    description=m["description"],
                    due_date=m.get("due_date"),
                    priority=m.get("priority", output.priority),
                    relationship_type=m.get("relationship_type", "DUE_ON"),
                    target_event=m.get("target_event"),
                    relationship_reason=m.get("relationship_reason"),
                    binding_confidence=m.get("binding_confidence", 1.0)
                )
                for m in mapped
            ]
        return output

    def _raw_analyze_email(
        self,
        subject: str,
        body: str,
        sender: str,
        received_at: Optional[datetime] = None
    ) -> AIServiceOutput:
        full_text = f"{subject}\n{body}".lower()

        # 1. HOD Office - Internal Assessment Marks Submission (Section 41 flagship)
        if "internal assessment" in full_text or "mark sheet" in full_text:
            return AIServiceOutput(
                summary="Faculty members must submit internal assessment marks before September 10 and attend a departmental review meeting on September 8 at 10 AM.",
                category="Academic",
                priority="HIGH",
                priority_reason="Mandatory academic submission with an approaching deadline and scheduled review meeting.",
                deadline="2026-09-10",
                meeting=AIMeetingOutput(
                    title="Department Review Meeting",
                    date="2026-09-08",
                    time="10:00",
                    location="Seminar Hall",
                    preparation="Bring updated mark sheet and student attendance logs"
                ),
                action_items=[
                    "Submit internal assessment marks",
                    "Bring updated mark sheet and attendance logs"
                ],
                important_entities=[
                    AIEntityOutput(type="DEPARTMENT", value="Computer Science & Engineering"),
                    AIEntityOutput(type="ROLE", value="Head of Department"),
                    AIEntityOutput(type="VENUE", value="Seminar Hall")
                ],
                evidence=[
                    AIEvidenceOutput(
                        field_name="deadline",
                        extracted_value="2026-09-10",
                        source_text="All members are requested to submit the internal assessment marks before September 10.",
                        confidence=0.98
                    ),
                    AIEvidenceOutput(
                        field_name="meeting",
                        extracted_value="2026-09-08 10:00 @ Seminar Hall",
                        source_text="A review meeting will be conducted on September 8 at 10 AM in the Seminar Hall.",
                        confidence=0.99
                    ),
                    AIEvidenceOutput(
                        field_name="action_item",
                        extracted_value="Submit internal assessment marks",
                        source_text="All members are requested to submit the internal assessment marks before September 10.",
                        confidence=0.95
                    )
                ]
            )

        # 2. Controller of Examinations - Question Paper Setting
        if "question paper" in full_text or "coe" in sender.lower() or "end semester" in full_text:
            return AIServiceOutput(
                summary="Submit two distinct sets of manuscript question papers with answer schemes to COE Confidential Section before September 15.",
                category="Examination",
                priority="HIGH",
                priority_reason="Statutory directive from Controller of Examinations with strict confidentiality and mandatory deadline.",
                deadline="2026-09-15",
                meeting=None,
                action_items=[
                    "Prepare two sets of manuscript question papers and answer schemes",
                    "Submit sealed envelopes to COE Confidential Section"
                ],
                important_entities=[
                    AIEntityOutput(type="OFFICE", value="COE Confidential Section"),
                    AIEntityOutput(type="ROLE", value="Chief Question Paper Setter")
                ],
                evidence=[
                    AIEvidenceOutput(
                        field_name="deadline",
                        extracted_value="2026-09-15",
                        source_text="submit two distinct sets of manuscript question papers along with detailed answer schemes in sealed envelopes to the COE Confidential Section before September 15.",
                        confidence=0.99
                    )
                ]
            )

        # 3. NAAC Accreditation Review
        if "naac" in full_text or "accreditation" in full_text:
            return AIServiceOutput(
                summary="Mandatory NAAC peer team preparation meeting on September 9 at 2:30 PM in the Main Board Room with course files and CO-PO attainment matrices.",
                category="Administrative",
                priority="HIGH",
                priority_reason="Institutional accreditation review chaired by Dean Academics with immediate audit requirements.",
                deadline="2026-09-09",
                meeting=AIMeetingOutput(
                    title="NAAC Peer Team Visit Preparation & File Audit",
                    date="2026-09-09",
                    time="14:30",
                    location="Main Board Room",
                    preparation="Updated course files, mentor-mentee records, and CO-PO attainment matrices"
                ),
                action_items=[
                    "Update course files, mentor-mentee records, and CO-PO attainment matrices"
                ],
                important_entities=[
                    AIEntityOutput(type="ACCREDITATION_BODY", value="NAAC"),
                    AIEntityOutput(type="VENUE", value="Main Board Room")
                ],
                evidence=[
                    AIEvidenceOutput(
                        field_name="meeting",
                        extracted_value="2026-09-09 14:30 @ Main Board Room",
                        source_text="mandatory file audit and criterion progress review will be held on September 9 at 2:30 PM in the Main Board Room.",
                        confidence=0.98
                    )
                ]
            )

        # 4. Student Leave / Re-test Appeal
        if "medical leave" in full_text or "re-test" in full_text or "student" in sender.lower():
            return AIServiceOutput(
                summary="Student requests an approved make-up re-test for Quiz 1 before September 12 following medical hospitalization.",
                category="Student",
                priority="MEDIUM",
                priority_reason="Student academic appeal with documented medical certificate requiring faculty discretionary scheduling.",
                deadline="2026-09-12",
                meeting=None,
                action_items=[
                    "Verify medical certificate with Health Center and schedule Quiz 1 re-test"
                ],
                important_entities=[
                    AIEntityOutput(type="CATEGORY", value="Student Appeal"),
                    AIEntityOutput(type="DOCUMENT", value="Medical Fitness Certificate")
                ],
                evidence=[
                    AIEvidenceOutput(
                        field_name="deadline",
                        extracted_value="2026-09-12",
                        source_text="Could you please allow me to take the make-up test before September 12 as per academic regulations?",
                        confidence=0.93
                    )
                ]
            )

        # 5. Board of Studies (BOS) Meeting
        if "board of studies" in full_text or "bos" in full_text or "curriculum" in full_text:
            return AIServiceOutput(
                summary="18th Board of Studies curriculum meeting on September 14 at 11:00 AM in Conference Hall B to review Cloud Computing and Generative AI syllabus drafts.",
                category="Meeting",
                priority="HIGH",
                priority_reason="Statutory academic board meeting involving external industry stakeholders requiring prior syllabus review.",
                deadline="2026-09-14",
                meeting=AIMeetingOutput(
                    title="18th Board of Studies (BOS) Curriculum Meeting",
                    date="2026-09-14",
                    time="11:00",
                    location="Conference Hall B",
                    preparation="Review attached draft syllabus for Cloud Computing and Generative AI electives"
                ),
                action_items=[
                    "Review draft syllabus for Cloud Computing and Generative AI electives"
                ],
                important_entities=[
                    AIEntityOutput(type="COMMITTEE", value="Board of Studies"),
                    AIEntityOutput(type="VENUE", value="Conference Hall B")
                ],
                evidence=[
                    AIEvidenceOutput(
                        field_name="meeting",
                        extracted_value="2026-09-14 11:00 @ Conference Hall B",
                        source_text="The 18th Board of Studies (BOS) meeting for curriculum modernization is scheduled for September 14 at 11:00 AM in Conference Hall B.",
                        confidence=0.98
                    )
                ]
            )

        # 6. IEEE Conference Review Invitation (Email #11)
        if "ieee" in full_text or "manuscript" in full_text or "easychair" in full_text:
            return AIServiceOutput(
                summary="Invitation from IEEE ICC 2026 to peer-review 3 research manuscripts via EasyChair before September 18.",
                category="Research",
                priority="MEDIUM",
                priority_reason="External professional scholarly peer-review invitation with explicit conference submission deadline.",
                deadline="2026-09-18",
                meeting=None,
                action_items=[
                    "Confirm availability to TPC Chair via reply",
                    "Complete peer reviews on EasyChair portal before September 18"
                ],
                important_entities=[
                    AIEntityOutput(type="ORGANIZATION", value="IEEE"),
                    AIEntityOutput(type="PLATFORM", value="EasyChair"),
                    AIEntityOutput(type="CONFERENCE", value="IEEE ICC 2026")
                ],
                evidence=[
                    AIEvidenceOutput(
                        field_name="deadline",
                        extracted_value="2026-09-18",
                        source_text="peer-review evaluations must be submitted through EasyChair before September 18.",
                        confidence=0.97
                    ),
                    AIEvidenceOutput(
                        field_name="action_item",
                        extracted_value="Confirm availability",
                        source_text="Please confirm your availability by replying to this email.",
                        confidence=0.94
                    )
                ]
            )

        # 7. Biometric Attendance Policy (Email #12)
        if "biometric" in full_text or "attendance policy" in full_text:
            return AIServiceOutput(
                summary="Office memorandum detailing revised 15-minute biometric grace period effective September 15 and mandatory digital movement register protocols.",
                category="Administrative",
                priority="MEDIUM",
                priority_reason="Institutional compliance directive with official implementation date issued by executive authority.",
                deadline="2026-09-15",
                meeting=None,
                action_items=[
                    "Note revised 15-minute biometric attendance grace period",
                    "Record official outdoor duties in digital movement register at Gate 1"
                ],
                important_entities=[
                    AIEntityOutput(type="AUTHORITY", value="Vice Chancellor"),
                    AIEntityOutput(type="POLICY", value="Biometric Attendance Policy")
                ],
                evidence=[
                    AIEvidenceOutput(
                        field_name="deadline",
                        extracted_value="2026-09-15",
                        source_text="Kindly note that effective September 15, the grace period for biometric punch-in will be revised to 15 minutes.",
                        confidence=0.96
                    )
                ]
            )

        # 8. Capstone Project Review (Email #13)
        if "capstone project" in full_text or "phase-1 evaluation" in full_text or "rubrics" in full_text:
            return AIServiceOutput(
                summary="Capstone Project Phase-1 review presentations scheduled for September 12 at 10:00 AM in Systems Lab 4 with marks submission by 4 PM.",
                category="Academic",
                priority="HIGH",
                priority_reason="Mandatory project jury evaluation with same-day consolidated marks submission requirement.",
                deadline="2026-09-12",
                meeting=AIMeetingOutput(
                    title="Capstone Project Phase-1 Review Presentations",
                    date="2026-09-12",
                    time="10:00",
                    location="Systems Lab 4",
                    preparation="Review project rubrics on LMS and prepare score sheets"
                ),
                action_items=[
                    "Conduct Phase-1 evaluation using LMS rubrics",
                    "Submit consolidated marks sheets to convener by 4 PM on September 12"
                ],
                important_entities=[
                    AIEntityOutput(type="COMMITTEE", value="Project Coordination Committee"),
                    AIEntityOutput(type="VENUE", value="Systems Lab 4")
                ],
                evidence=[
                    AIEvidenceOutput(
                        field_name="meeting",
                        extracted_value="2026-09-12 10:00 @ Systems Lab 4",
                        source_text="Phase-1 Capstone Project review presentations will be held on September 12 at 10:00 AM in Systems Lab 4.",
                        confidence=0.98
                    ),
                    AIEvidenceOutput(
                        field_name="deadline",
                        extracted_value="2026-09-12 16:00",
                        source_text="Consolidated marks sheets must be handed over to the project convener by 4 PM on the same day.",
                        confidence=0.95
                    )
                ]
            )

        # 9. IT Infrastructure Maintenance (Email #14)
        if "wi-fi" in full_text or "maintenance" in full_text or "downtime" in full_text:
            return AIServiceOutput(
                summary="Core switch firmware upgrades scheduled for September 7 at 11:00 PM causing intermittent Wi-Fi and ERP downtime until 4:00 AM.",
                category="General",
                priority="LOW",
                priority_reason="Informational announcement regarding nocturnal network downtime with no direct action required.",
                deadline=None,
                meeting=AIMeetingOutput(
                    title="Scheduled Core Network Maintenance Window",
                    date="2026-09-07",
                    time="23:00",
                    location="Campus Network Operations Center",
                    preparation=None
                ),
                action_items=[],
                important_entities=[
                    AIEntityOutput(type="SERVICE", value="Campus Wi-Fi / ERP Portals"),
                    AIEntityOutput(type="WING", value="IT Infrastructure Wing")
                ],
                evidence=[
                    AIEvidenceOutput(
                        field_name="meeting",
                        extracted_value="2026-09-07 23:00",
                        source_text="The IT Services team will perform scheduled firmware upgrades on core switches on September 7 starting at 11:00 PM.",
                        confidence=0.95
                    )
                ]
            )

        # 10. AICTE FDP (Email #15)
        if "faculty development program" in full_text or "fdp" in full_text or "aicte" in full_text:
            return AIServiceOutput(
                summary="Applications open for 5-day AICTE-ATAL FDP on Agentic AI (Oct 5-9); registration requires HOD clearance before September 14.",
                category="Event",
                priority="MEDIUM",
                priority_reason="Professional faculty upskilling opportunity with approaching registration portal deadline.",
                deadline="2026-09-14",
                meeting=None,
                action_items=[
                    "Secure HOD clearance for FDP attendance",
                    "Complete online registration on ATAL portal before September 14"
                ],
                important_entities=[
                    AIEntityOutput(type="PROGRAM", value="AICTE-ATAL FDP on Agentic AI"),
                    AIEntityOutput(type="ORGANIZER", value="Center for Continuing Education")
                ],
                evidence=[
                    AIEvidenceOutput(
                        field_name="deadline",
                        extracted_value="2026-09-14",
                        source_text="Faculty interested in attending should secure HOD clearance and complete portal registration before September 14.",
                        confidence=0.96
                    )
                ]
            )

        # Generic Fallback: Dynamic Heuristic Extraction
        return self._heuristic_analyze(subject, body, sender, received_at)

    def _heuristic_analyze(
        self,
        subject: str,
        body: str,
        sender: str,
        received_at: Optional[datetime] = None
    ) -> AIServiceOutput:
        """Dynamic heuristic analyzer for arbitrary or unseen emails."""
        text = f"{subject}\n{body}"
        sentences = [s.strip() for s in re.split(r'[.!?\n]', body) if len(s.strip()) > 10]
        
        # Priority inference
        high_cues = ["urgent", "mandatory", "immediate", "deadline", "strictly", "confidential"]
        medium_cues = ["request", "submit", "review", "schedule", "meeting", "action required"]
        
        is_high = any(cue in text.lower() for cue in high_cues)
        is_medium = any(cue in text.lower() for cue in medium_cues)
        
        priority = "HIGH" if is_high else ("MEDIUM" if is_medium else "LOW")
        priority_reason = (
            "Detected high-urgency directives requiring prompt faculty action." if is_high else
            ("Identified actionable academic correspondence requiring scheduling." if is_medium else
             "Informational correspondence with routine priority.")
        )

        # Category inference
        category = "Academic"
        if any(k in text.lower() for k in ["exam", "question paper", "quiz", "invigilation"]):
            category = "Examination"
        elif any(k in text.lower() for k in ["meeting", "minutes", "conference hall"]):
            category = "Meeting"
        elif any(k in text.lower() for k in ["research", "grant", "paper", "journal", "ieee"]):
            category = "Research"
        elif any(k in text.lower() for k in ["placement", "interview", "hiring"]):
            category = "Placement"
        elif any(k in text.lower() for k in ["student", "leave", "roll no"]):
            category = "Student"
        elif any(k in text.lower() for k in ["circular", "policy", "registrar", "dean"]):
            category = "Administrative"

        # Date extraction using actionable deadline extractor
        from backend.app.utils.date_parser import extract_actionable_deadline
        extracted_iso, raw_date_text, conf = extract_actionable_deadline(body, reference_date=received_at)
        deadline = extracted_iso
        evidences = []
        if deadline:
            matching_sent = next((s for s in sentences if raw_date_text and raw_date_text.lower() in s.lower()), sentences[0] if sentences else body[:100])
            evidences.append(
                AIEvidenceOutput(
                    field_name="deadline",
                    extracted_value=deadline,
                    source_text=matching_sent,
                    confidence=conf
                )
            )

        # Action items heuristic
        action_items = []
        for s in sentences:
            if re.match(r'^(?:please|kindly|all members|all faculty|you are requested|submit|bring|prepare|review)', s, re.IGNORECASE):
                action_items.append(s[:100].strip())
                if len(action_items) >= 2:
                    break

        if not action_items and sentences:
            action_items.append(sentences[0][:100].strip())

        # Summary
        summary = sentences[0] if sentences else subject

        return AIServiceOutput(
            summary=summary,
            category=category,
            priority=priority,
            priority_reason=priority_reason,
            deadline=deadline,
            meeting=None,
            action_items=action_items,
            important_entities=[
                AIEntityOutput(type="SENDER", value=sender)
            ],
            evidence=evidences
        )
