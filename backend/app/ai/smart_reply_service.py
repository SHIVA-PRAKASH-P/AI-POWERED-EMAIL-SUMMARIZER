import re
from typing import Optional, Dict, Any

class SmartReplyService:
    """Context-aware Smart Reply Intent Detection and Grounded Draft Generation Service.

    Distinguishes:
    - Informational emails (newsletters, circulars, bulletins) -> NO reply
    - Action-only emails without reply requirement ('Submit marks by Sept 15') -> NO reply
    - Availability confirmation requests -> Reply expected
    - Information requests -> Reply expected (safe grounded fallback, no invented facts)
    - Acknowledgement requests -> Reply expected
    - Explicit response requests -> Reply expected

    Zero email sending. Read-only draft suggestion only.
    """

    INFORMATIONAL_PATTERNS = [
        r'\bnewsletter\b',
        r'\bcircular\b',
        r'\bword of the day\b',
        r'\bdaily news\b',
        r'\broutine announcement\b',
        r'\bgeneral awareness\b',
        r'\bfor your information\b',
        r'\bfyi\b',
        r'\bpress release\b',
        r'\bweekly bulletin\b',
        r'\bno reply\b',
        r'\bdo not reply\b',
        r'\bautomated notification\b'
    ]

    ACTION_ONLY_PATTERNS = [
        r'\bsubmit (?:the )?(?:marks|grades|scores|report|proposal|assignment|documents?)\b',
        r'\bcomplete (?:the )?(?:form|verification|profile|registration|survey)\b',
        r'\bupload (?:the )?(?:marks|syllabus|files?)\b',
        r'\battend (?:the )?(?:meeting|session|hall|event)\b',
        r'\bbring (?:the )?(?:mark sheet|documents?|laptop)\b'
    ]

    def detect_reply_intent(
        self,
        subject: str,
        body: str,
        sender: str = ""
    ) -> Dict[str, Any]:
        """Evaluate contextual email intent to determine if a response is expected from the recipient."""
        full_text = f"{subject}\n{body}".lower()

        # 1. Immediate rejection for automated / no-reply senders
        if re.search(r'\b(?:no-?reply|donotreply|dailynews|newsletter|circular|notification)@', sender.lower()):
            return {
                "reply_expected": False,
                "reply_reason": None,
                "intent_type": None
            }

        # 2. Check for informational / announcement content
        is_informational = any(re.search(p, full_text) for p in self.INFORMATIONAL_PATTERNS)
        
        # 3. Detection of specific reply-intent categories
        # A) Availability Confirmation
        availability_match = re.search(
            r'\b(?:please |kindly )?(?:confirm (?:your |whether you are )?availability|let (?:us|me) know if you can attend|confirm your attendance)\b',
            full_text
        )
        if availability_match:
            return {
                "reply_expected": True,
                "reply_reason": "Availability Confirmation Requested",
                "intent_type": "AVAILABILITY"
            }

        # B) Acknowledgement Request
        ack_match = re.search(
            r'\b(?:kindly |please )?(?:acknowledge (?:the )?receipt|confirm receipt|reply to acknowledge)\b',
            full_text
        )
        if ack_match:
            return {
                "reply_expected": True,
                "reply_reason": "Acknowledgement Requested",
                "intent_type": "ACKNOWLEDGEMENT"
            }

        # C) Information Request (questions or requests directed to faculty)
        info_match = re.search(
            r'\b(?:could you (?:please )?|can you (?:please )?|please |kindly )?(?:provide|share|send|forward)\s+(?:us\s+|me\s+)?(?:with\s+)?(?:the\s+)?(?:updated\s+|revised\s+)?(?:syllabus|details|number|count|information|data|update|feedback|report|list|copy|documents?)\b',
            full_text
        )
        if info_match:
            return {
                "reply_expected": True,
                "reply_reason": "Information Requested",
                "intent_type": "INFORMATION"
            }

        # D) Explicit Response Request
        response_match = re.search(
            r'\b(?:please |kindly )?(?:let us know|let me know|reply (?:to this|with|by)|respond (?:to this|with|by)|send your response|reply with your confirmation)\b',
            full_text
        )
        if response_match:
            return {
                "reply_expected": True,
                "reply_reason": "Response Requested",
                "intent_type": "RESPONSE"
            }

        # 4. Action-only rejection: If email has action commands (submit marks, upload) without reply cues
        has_action_only = any(re.search(p, full_text) for p in self.ACTION_ONLY_PATTERNS)
        if has_action_only or is_informational:
            return {
                "reply_expected": False,
                "reply_reason": None,
                "intent_type": None
            }

        # Default fallback: safe False (never hallucinate reply expectations)
        return {
            "reply_expected": False,
            "reply_reason": None,
            "intent_type": None
        }

    def generate_reply(
        self,
        subject: str,
        body: str,
        sender: str = "",
        intent_info: Optional[Dict[str, Any]] = None,
        user_name: Optional[str] = None
    ) -> Optional[str]:
        """Generate a concise, professional draft reply grounded strictly in the email content."""
        if not intent_info:
            intent_info = self.detect_reply_intent(subject, body, sender)

        if not intent_info.get("reply_expected"):
            return None

        intent_type = intent_info.get("intent_type")

        # Construct safe grounded signoff
        if user_name and user_name.strip() and not user_name.startswith("User"):
            signoff = f"Regards,\n{user_name.strip()}"
        else:
            signoff = "Regards"

        if intent_type == "ACKNOWLEDGEMENT":
            doc_match = re.search(r'\b(?:attached |this )?(document|circular|file|communication|email|letter|schedule)\b', body, re.IGNORECASE)
            doc_noun = doc_match.group(1).lower() if doc_match else "document"
            return f"Dear Sir/Madam,\n\nI acknowledge receipt of the {doc_noun}. Thank you.\n\n{signoff}"

        elif intent_type == "AVAILABILITY":
            # Extract meeting topic and date/time if present
            meeting_match = re.search(r'\b(department meeting|faculty meeting|review meeting|meeting|discussion|seminar)\b', f"{subject} {body}", re.IGNORECASE)
            event_name = meeting_match.group(1).lower() if meeting_match else "meeting"
            
            date_match = re.search(r'\b(?:on\s+)([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?|\d{1,2}[./]\d{1,2}[./]\d{4}|\d{4}-\d{2}-\d{2}|friday|monday|tuesday|wednesday|thursday)\b', body, re.IGNORECASE)
            time_match = re.search(r'\b(?:at\s+)(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b', body, re.IGNORECASE)
            
            event_details = event_name
            if date_match:
                event_details += f" on {date_match.group(1)}"
            if time_match:
                event_details += f" at {time_match.group(1)}"

            return f"Dear Sir/Madam,\n\nI confirm my availability for the {event_details}.\n\n{signoff}"

        elif intent_type == "INFORMATION":
            # Never invent unknown student counts, data, or departmental numbers!
            return f"Dear Sir/Madam,\n\nThank you for your email. I will review the requested information and get back to you shortly.\n\n{signoff}"

        elif intent_type == "RESPONSE":
            return f"Dear Sir/Madam,\n\nThank you for reaching out. I have noted your communication and will follow up with the requested details shortly.\n\n{signoff}"

        return f"Dear Sir/Madam,\n\nThank you for your email. I will review and respond shortly.\n\n{signoff}"