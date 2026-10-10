"""Comprehensive Automated Tests for Cross-Email Intelligence (Stage 14).

Validates:
1. Subject normalization (prefix and bracket tag stripping).
2. Thread linking (predecessor and follow-up relationship identification).
3. Entity and sender cross-correlation scoring.
4. Chronological multi-event timeline synthesis.
5. Inbox topic clustering and metrics aggregation.
6. REST API endpoints (/api/emails/{id}/cross-intelligence and /api/cross-intelligence/clusters).
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.app.database.session import Base
from backend.app.models.email import Email
from backend.app.models.analysis import AIAnalysis
from backend.app.models.action_item import ActionItem
from backend.app.models.meeting import Meeting
from backend.app.models.entity import Entity
from backend.app.ai.cross_email_service import CrossEmailIntelligenceService

client = TestClient(app)

@pytest.fixture
def mock_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# --------------------------------------------------------------------------
# 1. Subject Normalization Tests
# --------------------------------------------------------------------------

def test_normalize_subject_basic():
    service = CrossEmailIntelligenceService()
    assert service.normalize_subject("Internal Assessment Marks Submission") == "internal assessment marks submission"
    assert service.normalize_subject("Re: Internal Assessment Marks Submission") == "internal assessment marks submission"
    assert service.normalize_subject("Fwd: Re: Internal Assessment Marks Submission") == "internal assessment marks submission"

def test_normalize_subject_with_brackets_and_multiple_prefixes():
    service = CrossEmailIntelligenceService()
    subj = "Fwd: [FACULTY] Urgent: [CSE] Re: BOS Curriculum Meeting"
    assert service.normalize_subject(subj) == "bos curriculum meeting"

def test_normalize_subject_empty():
    service = CrossEmailIntelligenceService()
    assert service.normalize_subject("") == ""
    assert service.normalize_subject(None) == ""

# --------------------------------------------------------------------------
# 2. Thread Linking & Related Emails Tests
# --------------------------------------------------------------------------

def test_thread_predecessor_and_followup_matching(mock_db):
    service = CrossEmailIntelligenceService()
    now = datetime(2026, 9, 6, 10, 0, 0)

    # 1. Initial email
    e1 = Email(
        sender="hod.cse@university.edu",
        recipient="faculty@university.edu",
        subject="Internal Assessment Marks Submission",
        body="Please submit marks by Sept 10.",
        received_at=now - timedelta(days=2),
        is_read=True
    )
    mock_db.add(e1)
    mock_db.commit()
    mock_db.refresh(e1)

    a1 = AIAnalysis(
        email_id=e1.id,
        summary="Submit marks before Sept 10",
        category="Academic",
        priority="HIGH",
        priority_reason="Department internal assessment deadline"
    )
    mock_db.add(a1)

    # 2. Follow-up reply email in thread
    e2 = Email(
        sender="faculty.lead@university.edu",
        recipient="hod.cse@university.edu",
        subject="Re: Internal Assessment Marks Submission",
        body="Marksheet format query and clarification.",
        received_at=now - timedelta(days=1),
        is_read=False
    )
    mock_db.add(e2)
    mock_db.commit()
    mock_db.refresh(e2)

    a2 = AIAnalysis(
        email_id=e2.id,
        summary="Clarification on marksheet format",
        category="Academic",
        priority="MEDIUM",
        priority_reason="Follow-up clarification query"
    )
    mock_db.add(a2)
    mock_db.commit()

    # Find related for initial email (e1) -> should find e2 as THREAD_FOLLOWUP
    rel_for_e1 = service.find_related_emails(mock_db, e1.id)
    assert len(rel_for_e1) == 1
    assert rel_for_e1[0]["id"] == e2.id
    assert rel_for_e1[0]["relationship_type"] == "THREAD_FOLLOWUP"
    assert rel_for_e1[0]["relevance_score"] >= 0.60

    # Find related for follow-up email (e2) -> should find e1 as THREAD_PREDECESSOR
    rel_for_e2 = service.find_related_emails(mock_db, e2.id)
    assert len(rel_for_e2) == 1
    assert rel_for_e2[0]["id"] == e1.id
    assert rel_for_e2[0]["relationship_type"] == "THREAD_PREDECESSOR"

def test_entity_overlap_correlation(mock_db):
    service = CrossEmailIntelligenceService()
    now = datetime(2026, 9, 6, 12, 0, 0)

    e1 = Email(
        sender="prof1@university.edu",
        recipient="faculty@university.edu",
        subject="Quiz 1 Schedule Announcement",
        body="Quiz 1 for CS2204 will be conducted soon.",
        received_at=now - timedelta(days=1)
    )
    mock_db.add(e1)
    mock_db.commit()
    mock_db.refresh(e1)

    ent1 = Entity(email_id=e1.id, entity_type="COURSE", entity_value="Advanced Algorithms")
    mock_db.add(ent1)

    e2 = Email(
        sender="student@university.edu",
        recipient="prof1@university.edu",
        subject="Request for Make-up Exam",
        body="Regarding Advanced Algorithms make-up test.",
        received_at=now
    )
    mock_db.add(e2)
    mock_db.commit()
    mock_db.refresh(e2)

    ent2 = Entity(email_id=e2.id, entity_type="COURSE", entity_value="Advanced Algorithms")
    mock_db.add(ent2)
    mock_db.commit()
    mock_db.expire_all()

    related = service.find_related_emails(mock_db, e2.id)
    assert len(related) >= 1
    match = next(r for r in related if r["id"] == e1.id)
    assert any("Shared entities" in reason for reason in match["relationship_reasons"])

# --------------------------------------------------------------------------
# 3. Cross-Email Insights & Timeline Synthesis Tests
# --------------------------------------------------------------------------

def test_cross_email_insights_and_timeline(mock_db):
    service = CrossEmailIntelligenceService()
    now = datetime(2026, 9, 6, 10, 0, 0)

    # Email with meeting
    e1 = Email(
        sender="hod.cse@university.edu",
        recipient="faculty@university.edu",
        subject="Internal Assessment Marks Submission",
        body="Review meeting on Sept 8 at 10 AM. Submit marks by Sept 10.",
        received_at=now - timedelta(days=1)
    )
    mock_db.add(e1)
    mock_db.commit()
    mock_db.refresh(e1)

    m1 = Meeting(
        email_id=e1.id,
        title="Department Review Meeting",
        meeting_date="2026-09-08",
        meeting_time="10:00",
        location="Seminar Hall"
    )
    act1 = ActionItem(
        email_id=e1.id,
        description="Submit assessment marks",
        due_date="2026-09-10",
        priority="HIGH",
        completed=False
    )
    mock_db.add_all([m1, act1])
    mock_db.commit()

    # Second email in thread with subsequent action
    e2 = Email(
        sender="faculty.lead@university.edu",
        recipient="hod.cse@university.edu",
        subject="Re: Internal Assessment Marks Submission",
        body="Uploading attendance logs by Sept 9.",
        received_at=now
    )
    mock_db.add(e2)
    mock_db.commit()
    mock_db.refresh(e2)

    act2 = ActionItem(
        email_id=e2.id,
        description="Upload attendance logs",
        due_date="2026-09-09",
        priority="MEDIUM",
        completed=False
    )
    mock_db.add(act2)
    mock_db.commit()

    insights = service.get_cross_email_insights(mock_db, e1.id)
    assert insights["email_id"] == e1.id
    assert insights["thread_count"] == 2
    assert len(insights["related_emails"]) == 1

    # Verify chronological timeline items
    timeline = insights["timeline"]
    assert len(timeline) >= 4  # 2 email received + 1 meeting + 2 deadlines
    timeline_types = [t["type"] for t in timeline]
    assert "EMAIL_RECEIVED" in timeline_types
    assert "MEETING" in timeline_types
    assert "DEADLINE" in timeline_types

    # Verify insights synthesis text
    assert len(insights["insights"]) > 0
    assert any("multi-message thread" in ins for ins in insights["insights"])

# --------------------------------------------------------------------------
# 4. Topic Clustering Tests
# --------------------------------------------------------------------------

def test_topic_clusters_grouping(mock_db):
    service = CrossEmailIntelligenceService()
    now = datetime(2026, 9, 6, 10, 0, 0)

    # Two emails about Marks
    e1 = Email(sender="hod@u.edu", recipient="f@u.edu", subject="Internal Assessment Marks", body="b1", received_at=now)
    e2 = Email(sender="f@u.edu", recipient="hod@u.edu", subject="Re: Internal Assessment Marks", body="b2", received_at=now)
    # One email about Wi-Fi
    e3 = Email(sender="it@u.edu", recipient="f@u.edu", subject="Campus Wi-Fi Maintenance", body="b3", received_at=now)
    mock_db.add_all([e1, e2, e3])
    mock_db.commit()

    clusters = service.get_topic_clusters(mock_db)
    assert len(clusters) == 2  # Marks cluster and Wi-Fi cluster

    marks_cluster = next(c for c in clusters if "marks" in c["normalized_topic"])
    assert marks_cluster["email_count"] == 2
    assert len(marks_cluster["participants"]) == 2

    wifi_cluster = next(c for c in clusters if "wi-fi" in c["normalized_topic"])
    assert wifi_cluster["email_count"] == 1

# --------------------------------------------------------------------------
# 5. REST API Integration Tests
# --------------------------------------------------------------------------

def test_api_email_cross_intelligence_endpoint():
    # Use existing seeded Email #1
    res = client.get("/api/emails/1/cross-intelligence")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "data" in data
    assert data["data"]["email_id"] == 1
    assert "timeline" in data["data"]
    assert "insights" in data["data"]

def test_api_email_cross_intelligence_not_found():
    res = client.get("/api/emails/99999/cross-intelligence")
    assert res.status_code == 404

def test_api_cross_intelligence_clusters_endpoint():
    res = client.get("/api/cross-intelligence/clusters")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "total_clusters" in data
    assert "clusters" in data
    assert data["total_clusters"] > 0
