"""Stage 21 Comprehensive Test Suite — Intelligent Email Understanding.

Tests:
A. Structured AI Summarization (grounded, structured format: Summary/Action/Deadline)
B. Temporal & Date Parsing (diverse date formats, rejection of past non-deadlines, dynamic status)
C. Dynamic Deadline Status Computation (UPCOMING, DUE_TODAY, EXPIRED, relative strings)
D. Context-Aware Smart Reply Suggestions (intent detection, rejection of non-reply emails, grounded drafts)
E. AI Orchestration & Mock Enrichment (all 5 Stage 21 columns persisted)
F. API Integrations & Dashboard Separation (upcoming vs expired deadlines, filtering)
G. Multi-User Isolation & Readonly Scope Security Enforcement
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.database.session import SessionLocal, init_db
from backend.app.models import User, Email, AIAnalysis, ActionItem, Meeting
from backend.app.utils.date_parser import (
    parse_date_expression,
    extract_actionable_deadline,
    is_actionable_deadline_sentence,
    compute_temporal_status,
)
from backend.app.ai.summarization_service import SummarizationService
from backend.app.ai.smart_reply_service import SmartReplyService
from backend.app.ai.orchestrator import AgentOrchestrator
from backend.app.ai.mock_service import MockAIService
from backend.app.config import get_settings

client = TestClient(app)

USER1_EMAIL = "mock.faculty@university.edu"
USER2_EMAIL = "shivaprakashp.cs24@bitsathy.ac.in"


@pytest.fixture(scope="module", autouse=True)
def init_test_db():
    init_db()
    yield


@pytest.fixture
def user1_session():
    resp = client.post("/api/auth/switch-session", json={"email": USER1_EMAIL})
    assert resp.status_code == 200
    token = resp.json()["session_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user2_session():
    resp = client.post("/api/auth/switch-session", json={"email": USER2_EMAIL})
    assert resp.status_code == 200
    token = resp.json()["session_token"]
    return {"Authorization": f"Bearer {token}"}


# =====================================================================
# A. SUMMARIZATION SERVICE TESTS (5 tests)
# =====================================================================
class TestSummarizationService:
    def test_structured_summary_format(self):
        """Summary must follow structured 2-4 sentence layout with Summary/Action/Deadline markers."""
        svc = SummarizationService()
        email_text = (
            "Dear Faculty,\nPlease submit the final internal assessment marks "
            "for the 6th semester by September 30, 2026. This is required for the COE office audit.\n"
            "Regards,\nDean Academics"
        )
        summary = svc.summarize(
            "Submission of Internal Assessment Marks",
            email_text,
            "dean@university.edu",
        )
        assert "Summary:" in summary
        assert "Action:" in summary
        assert "Deadline:" in summary

    def test_summarization_grounding(self):
        """Summary content must be strictly derived from the provided email subject and body."""
        svc = SummarizationService()
        subject = "NBA Accreditation Meeting on Friday"
        body = "All department coordinators must gather in Conference Hall B at 3:00 PM for the NBA mock audit."
        summary = svc.summarize(subject, body, "hod.cse@university.edu")
        assert "NBA" in summary or "accreditation" in summary.lower()
        # Verify no hallucinated institutions
        assert "Stanford" not in summary
        assert "Harvard" not in summary

    def test_summarization_empty_or_short(self):
        """Gracefully handles very brief or minimal email content."""
        svc = SummarizationService()
        summary = svc.summarize("Quick Note", "Please see attached.", "colleague@univ.edu")
        assert len(summary) > 0
        assert "Summary:" in summary

    def test_summarization_with_imminent_deadline(self):
        """Summary clearly highlights the deadline when present."""
        svc = SummarizationService()
        subject = "Urgent: Grade Submission Deadline"
        body = "Please upload all final exam grades by tomorrow 5 PM without fail."
        summary = svc.summarize(subject, body, "coe@university.edu")
        assert "Deadline:" in summary
        assert "tomorrow" in summary.lower() or "5 PM" in summary or "None specified" not in summary

    def test_summarization_no_hallucinated_action(self):
        """When no faculty action is required, indicates clearly rather than hallucinating tasks."""
        svc = SummarizationService()
        subject = "Circular: Independence Day Celebration"
        body = "The campus will observe holiday on August 15 for Independence Day. Sweets will be distributed at 9 AM."
        summary = svc.summarize(subject, body, "admin@university.edu")
        assert "Action:" in summary
        assert "No immediate faculty action required" in summary or "celebration" in summary.lower() or "holiday" in summary.lower()


# =====================================================================
# B. DATE PARSING & TEMPORAL INTELLIGENCE TESTS (12 tests)
# =====================================================================
class TestDateParserAndTemporalIntelligence:
    def test_date_format_dd_mm_yyyy_dots(self):
        """Parses DD.MM.YYYY format correctly."""
        res = parse_date_expression("Please submit the dossier by 25.09.2026 without delay.")
        assert res is not None
        assert res.strftime("%Y-%m-%d") == "2026-09-25"

    def test_date_format_dd_mm_yyyy_slashes(self):
        """Parses DD/MM/YYYY format correctly."""
        res = parse_date_expression("The project report must be submitted before 25/09/2026.")
        assert res is not None
        assert res.strftime("%Y-%m-%d") == "2026-09-25"

    def test_date_format_yyyy_mm_dd(self):
        """Parses standard ISO YYYY-MM-DD format correctly."""
        res = parse_date_expression("System audit scheduled for 2026-10-15.")
        assert res is not None
        assert res.strftime("%Y-%m-%d") == "2026-10-15"

    def test_date_format_dd_month_yyyy(self):
        """Parses '25 September 2026' and '25th September 2026'."""
        res1 = parse_date_expression("Deadline is 25 September 2026 at 5 PM.")
        assert res1 is not None
        assert res1.strftime("%Y-%m-%d") == "2026-09-25"

        res2 = parse_date_expression("Submit by 25th September 2026.")
        assert res2 is not None
        assert res2.strftime("%Y-%m-%d") == "2026-09-25"

    def test_date_format_dd_mon_yyyy(self):
        """Parses abbreviated month format e.g. '25 Sep 2026'."""
        res = parse_date_expression("Registration closes on 25 Sep 2026.")
        assert res is not None
        assert res.strftime("%Y-%m-%d") == "2026-09-25"

    def test_date_format_month_dd_yyyy(self):
        """Parses US style 'September 25, 2026'."""
        res = parse_date_expression("Grades are due on September 25, 2026.")
        assert res is not None
        assert res.strftime("%Y-%m-%d") == "2026-09-25"

    def test_relative_date_today(self):
        """Resolves 'today' to the anchor/system date."""
        now = datetime.now(timezone.utc)
        res = parse_date_expression("Please return the signed forms today.", anchor_date=now)
        assert res is not None
        assert res.date() == now.date()

    def test_relative_date_tomorrow(self):
        """Resolves 'tomorrow' to anchor date + 1 day."""
        now = datetime.now(timezone.utc)
        res = parse_date_expression("Please submit the report tomorrow.", anchor_date=now)
        assert res is not None
        assert res.date() == (now + timedelta(days=1)).date()

    def test_relative_date_day_after_tomorrow(self):
        """Resolves 'day after tomorrow' to anchor date + 2 days."""
        now = datetime.now(timezone.utc)
        res = parse_date_expression("The committee will reconvene day after tomorrow.", anchor_date=now)
        assert res is not None
        assert res.date() == (now + timedelta(days=2)).date()

    def test_relative_date_within_n_days(self):
        """Resolves 'within 3 days' to anchor date + 3 days."""
        now = datetime.now(timezone.utc)
        res = parse_date_expression("Please provide the requested details within 3 days.", anchor_date=now)
        assert res is not None
        assert res.date() == (now + timedelta(days=3)).date()

    def test_relative_weekday(self):
        """Resolves 'by next Friday' relative expression."""
        now = datetime.now(timezone.utc)
        res = parse_date_expression("Submit the dossier by Friday.", anchor_date=now)
        assert res is not None
        assert res.date() >= now.date()

    def test_reject_non_deadline_past_dates(self):
        """Historical past mentions like 'meeting was held on September 1' are NOT actionable deadlines."""
        text = "The previous faculty council meeting was held on September 1, 2026. Minutes are attached."
        iso_dl, raw_dl, conf = extract_actionable_deadline(text)
        assert iso_dl is None


# =====================================================================
# C. DYNAMIC DEADLINE STATUS COMPUTATION TESTS (6 tests)
# =====================================================================
class TestDynamicDeadlineStatus:
    def test_status_upcoming_future(self):
        """Future date (> today) must compute as UPCOMING with relative string 'Due in N days'."""
        today = datetime.now(timezone.utc).date()
        future_date = (today + timedelta(days=5)).strftime("%Y-%m-%d")
        status, rel_str = compute_temporal_status(future_date)
        assert status == "UPCOMING"
        assert "Due in 5 days" in rel_str

    def test_status_upcoming_tomorrow(self):
        """Target date 1 day in the future must compute as 'Due tomorrow'."""
        today = datetime.now(timezone.utc).date()
        tomorrow = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        status, rel_str = compute_temporal_status(tomorrow)
        assert status == "UPCOMING"
        assert rel_str == "Due tomorrow"

    def test_status_due_today(self):
        """Target date == today must compute as DUE_TODAY with 'Due today'."""
        today = datetime.now(timezone.utc).date().strftime("%Y-%m-%d")
        status, rel_str = compute_temporal_status(today)
        assert status == "DUE_TODAY"
        assert rel_str == "Due today"

    def test_status_expired_past(self):
        """Target date in the past must compute as EXPIRED with 'Expired N days ago'."""
        today = datetime.now(timezone.utc).date()
        past_date = (today - timedelta(days=4)).strftime("%Y-%m-%d")
        status, rel_str = compute_temporal_status(past_date)
        assert status == "EXPIRED"
        assert "Expired 4 days ago" in rel_str

    def test_old_email_with_future_deadline_is_upcoming(self):
        """An email received 10 days ago whose deadline is next week remains UPCOMING."""
        today = datetime.now(timezone.utc).date()
        future_deadline = (today + timedelta(days=7)).strftime("%Y-%m-%d")
        status, rel_str = compute_temporal_status(future_deadline)
        assert status == "UPCOMING"
        assert "Due in 7 days" in rel_str

    def test_old_email_with_past_deadline_is_expired(self):
        """An email received 10 days ago whose deadline was yesterday is EXPIRED."""
        today = datetime.now(timezone.utc).date()
        past_deadline = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        status, rel_str = compute_temporal_status(past_deadline)
        assert status == "EXPIRED"
        assert rel_str == "Expired 1 day ago"


# =====================================================================
# D. SMART REPLY SERVICE INTENT & GENERATION TESTS (8 tests)
# =====================================================================
class TestSmartReplyService:
    def test_detect_reply_intent_availability(self):
        """Detects availability confirmation intent."""
        svc = SmartReplyService()
        res = svc.detect_reply_intent(
            "Board of Studies Meeting",
            "Dear Professor, please confirm your availability for the BoS meeting next Tuesday at 10 AM.",
            "hod@university.edu"
        )
        assert res["reply_expected"] is True
        assert res["intent_type"] == "AVAILABILITY"
        assert "availability" in res["reply_reason"].lower()

    def test_detect_reply_intent_information(self):
        """Detects information request intent."""
        svc = SmartReplyService()
        res = svc.detect_reply_intent(
            "Updated Course Syllabus Needed",
            "Could you please share the syllabus copy and textbook list for CS602?",
            "curriculum@university.edu"
        )
        assert res["reply_expected"] is True
        assert res["intent_type"] == "INFORMATION"
        assert "information" in res["reply_reason"].lower()

    def test_detect_reply_intent_acknowledgement(self):
        """Detects acknowledgement intent."""
        svc = SmartReplyService()
        res = svc.detect_reply_intent(
            "Circular: Exam Duty Allocation",
            "Please acknowledge receipt of your assigned invigilation slots.",
            "coe@university.edu"
        )
        assert res["reply_expected"] is True
        assert res["intent_type"] == "ACKNOWLEDGEMENT"
        assert "acknowledgement" in res["reply_reason"].lower()

    def test_detect_reply_intent_response(self):
        """Detects general response request intent."""
        svc = SmartReplyService()
        res = svc.detect_reply_intent(
            "Proposal Review",
            "Please let us know your decision regarding the grant application.",
            "research@university.edu"
        )
        assert res["reply_expected"] is True
        assert res["intent_type"] == "RESPONSE"

    def test_reject_informational_email(self):
        """Informational broadcast email does NOT expect a reply."""
        svc = SmartReplyService()
        res = svc.detect_reply_intent(
            "FYI: Campus Library Hours during Finals",
            "This is an announcement that the central library will remain open until midnight.",
            "librarian@university.edu"
        )
        assert res["reply_expected"] is False
        assert res["reply_reason"] is None

    def test_reject_action_only_email(self):
        """Email that only gives an action (no reply requested) does NOT expect a reply."""
        svc = SmartReplyService()
        res = svc.detect_reply_intent(
            "Mark Entry Portal Open",
            "All faculty members are requested to upload the continuous internal evaluation marks before Friday.",
            "dean.academics@university.edu"
        )
        assert res["reply_expected"] is False
        assert res["reply_reason"] is None

    def test_reject_newsletter_dailynews(self):
        """Automated newsletter emails from dailynews do NOT expect a reply."""
        svc = SmartReplyService()
        res = svc.detect_reply_intent(
            "Word of the Day: Ephemeral",
            "Today's word is Ephemeral, meaning lasting for a very short time. Have a nice day!",
            "dailynews@bitsathy.ac.in"
        )
        assert res["reply_expected"] is False
        assert res["reply_reason"] is None

    def test_generate_reply_draft_content(self):
        """Generates a grounded, polite academic draft reply."""
        svc = SmartReplyService()
        intent_info = {
            "reply_expected": True,
            "reply_reason": "Availability Confirmation",
            "intent_type": "AVAILABILITY"
        }
        draft = svc.generate_reply(
            "Board of Studies Meeting",
            "Please confirm your availability for the BoS meeting next Tuesday.",
            "hod.cse@university.edu",
            intent_info=intent_info
        )
        assert draft is not None
        assert len(draft) > 20
        assert "Dear" in draft or "Hi" in draft
        assert "available" in draft.lower() or "confirm" in draft.lower()
        assert "Regards" in draft or "Best" in draft


# =====================================================================
# E. AI ORCHESTRATION INTEGRATION TESTS (2 tests)
# =====================================================================
class TestAIOrchestrationStage21:
    def test_orchestrator_populates_stage21_fields(self):
        """AgentOrchestrator populates deadline_date, deadline_status, reply_expected, reply_reason, suggested_reply."""
        db = SessionLocal()
        email_id = None
        try:
            email = Email(
                user_id=1,
                sender="dr.sharma@university.edu",
                recipient="mock.faculty@university.edu",
                subject="Question regarding syllabus submission",
                body="Dear Professor,\nPlease confirm your availability for a short discussion tomorrow regarding the revised course syllabus.\nBest,\nDr. Sharma",
                received_at=datetime.now(timezone.utc),
                is_read=False
            )
            db.add(email)
            db.commit()
            db.refresh(email)
            email_id = email.id

            db.query(AIAnalysis).filter(AIAnalysis.email_id == email_id).delete()
            db.commit()

            orchestrator = AgentOrchestrator(db=db)
            analysis = orchestrator.process_email(email_id, db=db, force_refresh=True)

            assert analysis is not None
            assert analysis.reply_expected is True
            assert analysis.reply_reason is not None
            assert analysis.suggested_reply is not None
            assert len(analysis.suggested_reply) > 10
        finally:
            if email_id:
                db.query(AIAnalysis).filter(AIAnalysis.email_id == email_id).delete()
                db.query(Email).filter(Email.id == email_id).delete()
                db.commit()
            db.close()

    def test_mock_service_stage21_enrichment(self):
        """MockAIService provides consistent Stage 21 output enrichment."""
        mock_svc = MockAIService()
        output = mock_svc.analyze_email(
            "Urgent: Submit Midterm Grades by Tomorrow",
            "Please submit all midterm grades into the portal tomorrow.",
            "dean@university.edu"
        )
        assert "Summary:" in output.summary
        assert output.deadline_status in ("UPCOMING", "DUE_TODAY", "EXPIRED")
        assert output.reply_expected is not None


# =====================================================================
# F. API ENDPOINTS & DASHBOARD INTEGRATION TESTS (3 tests)
# =====================================================================
class TestStage21ApiEndpoints:
    def test_dashboard_partitions_upcoming_and_expired(self, user1_session):
        """Dashboard API cleanly separates upcoming and expired deadlines."""
        db = SessionLocal()
        today = datetime.now(timezone.utc).date()
        future_date = (today + timedelta(days=5)).strftime("%Y-%m-%d")
        past_date = (today - timedelta(days=5)).strftime("%Y-%m-%d")

        email = Email(
            user_id=1,
            sender="dean@univ.edu",
            recipient=USER1_EMAIL,
            subject="Deadlines Test Unique",
            body="Testing upcoming vs expired partitioning",
            received_at=datetime.now(timezone.utc),
            is_read=False
        )
        db.add(email)
        db.commit()
        db.refresh(email)
        email_id = email.id

        db.query(ActionItem).filter(ActionItem.email_id == email_id).delete()
        db.query(AIAnalysis).filter(AIAnalysis.email_id == email_id).delete()
        db.commit()

        a1 = ActionItem(
            email_id=email_id,
            description="Future Task Unique",
            due_date=future_date,
            priority="HIGH",
            completed=False,
            relationship_type="DUE_ON"
        )
        a2 = ActionItem(
            email_id=email_id,
            description="Past Expired Task Unique",
            due_date=past_date,
            priority="HIGH",
            completed=False,
            relationship_type="DUE_ON"
        )
        db.add_all([a1, a2])
        db.commit()
        db.close()

        try:
            resp = client.get("/api/dashboard", headers=user1_session)
            assert resp.status_code == 200
            data = resp.json()

            assert "upcoming_deadlines" in data
            assert "expired_deadlines" in data
            assert "expired_deadlines_count" in data["metrics"]

            # Check that upcoming deadlines only contain future/today dates
            for d in data["upcoming_deadlines"]:
                assert d["due_date"] >= today.strftime("%Y-%m-%d")
                assert d["deadline_status"] in ("UPCOMING", "DUE_TODAY")
                assert d["relative_status"] is not None

            # Check that expired deadlines only contain past dates
            for d in data["expired_deadlines"]:
                assert d["due_date"] < today.strftime("%Y-%m-%d")
                assert d["deadline_status"] == "EXPIRED"
                assert "Expired" in d["relative_status"]
        finally:
            db = SessionLocal()
            db.query(ActionItem).filter(ActionItem.email_id == email_id).delete()
            db.query(Email).filter(Email.id == email_id).delete()
            db.commit()
            db.close()

    def test_email_detail_includes_stage21_fields(self, user1_session):
        """GET /api/emails/{id} includes deadline and smart reply fields in analysis."""
        db = SessionLocal()
        email = Email(
            user_id=1,
            sender="hod@university.edu",
            recipient=USER1_EMAIL,
            subject="Smart Reply Test Email Unique",
            body="Please let us know your availability for the committee tomorrow.",
            received_at=datetime.now(timezone.utc),
            is_read=False
        )
        db.add(email)
        db.commit()
        db.refresh(email)
        email_id = email.id

        db.query(AIAnalysis).filter(AIAnalysis.email_id == email_id).delete()
        db.commit()

        tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).strftime("%Y-%m-%d")
        analysis = AIAnalysis(
            email_id=email_id,
            summary="Summary: Committee request.\nAction: Confirm availability.\nDeadline: Tomorrow.",
            category="Meeting",
            priority="HIGH",
            priority_reason="Imminent committee confirmation",
            deadline_date=tomorrow,
            deadline_status="UPCOMING",
            reply_expected=True,
            reply_reason="Availability confirmation requested",
            suggested_reply="Dear HOD,\n\nI confirm my availability for the committee.\n\nBest regards,"
        )
        db.add(analysis)
        db.commit()
        db.close()

        try:
            resp = client.get(f"/api/emails/{email_id}", headers=user1_session)
            assert resp.status_code == 200
            data = resp.json()
            assert data["analysis"] is not None
            an = data["analysis"]
            assert an["deadline_date"] == tomorrow
            assert an["deadline_status"] == "UPCOMING"
            assert an["reply_expected"] is True
            assert an["reply_reason"] == "Availability confirmation requested"
            assert "confirm my availability" in an["suggested_reply"]
        finally:
            db = SessionLocal()
            db.query(AIAnalysis).filter(AIAnalysis.email_id == email_id).delete()
            db.query(Email).filter(Email.id == email_id).delete()
            db.commit()
            db.close()

    def test_action_items_and_emails_filter_by_deadline_status(self, user1_session):
        """GET /api/deadlines and /api/emails filter by deadline_status."""
        resp_up = client.get("/api/deadlines?deadline_status=UPCOMING", headers=user1_session)
        assert resp_up.status_code == 200
        for item in resp_up.json():
            if item.get("due_date"):
                assert item["deadline_status"] in ("UPCOMING", "DUE_TODAY")

        resp_emails = client.get("/api/emails?deadline_status=UPCOMING", headers=user1_session)
        assert resp_emails.status_code == 200
        assert isinstance(resp_emails.json(), list)


# =====================================================================
# G. MULTI-USER ISOLATION & SECURITY HARDENING (2 tests)
# =====================================================================
class TestStage21MultiUserIsolationAndSecurity:
    def test_user_isolation_deadlines_and_replies(self, user1_session, user2_session):
        """User 1 and User 2 must never see each other's deadlines, analyses, or smart replies."""
        db = SessionLocal()
        u2_email = Email(
            user_id=2,
            sender="colleague@univ.edu",
            recipient=USER2_EMAIL,
            subject="Confidential Grant Proposal Review Unique",
            body="Please review and provide feedback on the grant proposal.",
            received_at=datetime.now(timezone.utc),
            is_read=False
        )
        db.add(u2_email)
        db.commit()
        db.refresh(u2_email)
        u2_email_id = u2_email.id

        db.query(AIAnalysis).filter(AIAnalysis.email_id == u2_email_id).delete()
        db.commit()

        u2_analysis = AIAnalysis(
            email_id=u2_email_id,
            summary="Summary: Grant review.\nAction: Review grant.\nDeadline: None.",
            category="Research",
            priority="MEDIUM",
            priority_reason="Research grant feedback",
            reply_expected=True,
            reply_reason="Feedback requested",
            suggested_reply="Dear Colleague,\n\nI will review the grant proposal.\n\nBest,"
        )
        db.add(u2_analysis)
        db.commit()
        db.close()

        try:
            # User 1 attempts to access User 2's email -> 404
            u1_resp = client.get(f"/api/emails/{u2_email_id}", headers=user1_session)
            assert u1_resp.status_code == 404

            # User 2 accesses their own email -> 200
            u2_resp = client.get(f"/api/emails/{u2_email_id}", headers=user2_session)
            assert u2_resp.status_code == 200
            assert u2_resp.json()["analysis"]["suggested_reply"] is not None
        finally:
            db = SessionLocal()
            db.query(AIAnalysis).filter(AIAnalysis.email_id == u2_email_id).delete()
            db.query(Email).filter(Email.id == u2_email_id).delete()
            db.commit()
            db.close()

    def test_gmail_readonly_scope_preservation(self):
        """Strictly validates that only gmail.readonly is configured, preventing send/compose/modify permissions."""
        settings = get_settings()
        scopes = settings.GMAIL_SCOPES
        assert "https://www.googleapis.com/auth/gmail.readonly" in scopes
        # Absolute security check: no send, write, or compose permissions
        for forbidden in ["gmail.send", "gmail.compose", "gmail.modify", "mail.google.com"]:
            assert not any(forbidden in s for s in scopes), f"Forbidden scope detected: {forbidden}"
