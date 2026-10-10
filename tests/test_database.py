import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database.session import Base
from backend.app.models import Email, AIAnalysis, ActionItem, Meeting, Evidence, Entity
from backend.app.database.seed_data import seed_database
from fastapi.testclient import TestClient
from backend.main import app

# Test SQLite in-memory database
TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_models_table_creation(db_session):
    """Verify all 6 relational models exist in the database schema."""
    table_names = Base.metadata.tables.keys()
    assert "emails" in table_names
    assert "ai_analyses" in table_names
    assert "action_items" in table_names
    assert "meetings" in table_names
    assert "evidences" in table_names
    assert "entities" in table_names

def test_seed_database_count(db_session):
    """Verify synthetic dataset insertion creates at least 15 emails."""
    count = seed_database(db_session)
    assert count == 15
    assert db_session.query(Email).count() == 15
    assert db_session.query(AIAnalysis).count() == 10
    assert db_session.query(ActionItem).count() >= 10
    assert db_session.query(Meeting).count() >= 4
    assert db_session.query(Evidence).count() >= 10
    assert db_session.query(Entity).count() >= 10

def test_flagship_email_integrity(db_session):
    """Verify relational integrity for the Section 41 flagship email."""
    seed_database(db_session)
    email = db_session.query(Email).filter(Email.subject == "Internal Assessment Marks Submission").first()
    assert email is not None
    assert email.sender == "hod.cse@university.edu"
    assert "September 10" in email.body

    # Check 1:1 relationship with AIAnalysis
    assert email.analysis is not None
    assert email.analysis.category == "Academic"
    assert email.analysis.priority == "HIGH"
    assert "Mandatory" in email.analysis.priority_reason

    # Check 1:N ActionItems
    actions = email.action_items
    assert len(actions) == 2
    assert any("Submit internal assessment marks" in a.description for a in actions)
    assert any("2026-09-10" == a.due_date for a in actions)

    # Check 1:N Meetings
    meetings = email.meetings
    assert len(meetings) == 1
    assert meetings[0].title == "Internal Assessment Department Review Meeting"
    assert meetings[0].meeting_date == "2026-09-08"
    assert meetings[0].meeting_time == "10:00"
    assert meetings[0].location == "Seminar Hall"

    # Check 1:N Evidence
    evidences = email.analysis.evidences
    assert len(evidences) >= 3
    assert any(e.field_name == "deadline" and "2026-09-10" in e.extracted_value for e in evidences)

def test_cascade_delete_email(db_session):
    """Verify deleting an email automatically cascades to all associated child records."""
    seed_database(db_session)
    email = db_session.query(Email).filter(Email.subject == "Internal Assessment Marks Submission").first()
    email_id = email.id
    analysis_id = email.analysis.id

    # Delete email
    db_session.delete(email)
    db_session.commit()

    # Verify cascades
    assert db_session.query(Email).filter_by(id=email_id).first() is None
    assert db_session.query(AIAnalysis).filter_by(id=analysis_id).first() is None
    assert db_session.query(ActionItem).filter_by(email_id=email_id).count() == 0
    assert db_session.query(Meeting).filter_by(email_id=email_id).count() == 0
    assert db_session.query(Evidence).filter_by(analysis_id=analysis_id).count() == 0
    assert db_session.query(Entity).filter_by(email_id=email_id).count() == 0

def test_api_db_status():
    """Verify the /api/db-status endpoint accurately reflects database state."""
    client = TestClient(app)
    response = client.get("/api/db-status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"
    assert data["counts"]["emails"] >= 15
    assert data["counts"]["analyses"] >= 10
    assert data["counts"]["action_items"] >= 10
