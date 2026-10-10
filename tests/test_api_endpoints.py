import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.app.database.session import SessionLocal, init_db, reset_db
from backend.app.database.seed_data import seed_database
from backend.app.models import ActionItem, Email

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database is seeded for API tests."""
    reset_db()
    db = SessionLocal()
    seed_database(db)
    db.close()

def test_get_emails_default():
    """Test GET /api/emails returns list with expected schema."""
    response = client.get("/api/emails")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 15
    first = data[0]
    assert "id" in first
    assert "sender" in first
    assert "subject" in first
    assert "body_preview" in first
    assert "is_read" in first
    assert "has_analysis" in first

def test_get_emails_filtering():
    """Test filtering emails by category, priority, is_read, has_deadline, and is_analyzed."""
    # Filter by category
    resp_cat = client.get("/api/emails?category=Academic")
    assert resp_cat.status_code == 200
    for item in resp_cat.json():
        assert item["category"] == "Academic"

    # Filter by priority
    resp_prio = client.get("/api/emails?priority=HIGH")
    assert resp_prio.status_code == 200
    for item in resp_prio.json():
        assert item["priority"] == "HIGH"

    # Filter by read status
    resp_read = client.get("/api/emails?is_read=false")
    assert resp_read.status_code == 200
    for item in resp_read.json():
        assert item["is_read"] is False

    # Filter by is_analyzed
    resp_unanalyzed = client.get("/api/emails?is_analyzed=false")
    assert resp_unanalyzed.status_code == 200
    assert len(resp_unanalyzed.json()) == 5
    for item in resp_unanalyzed.json():
        assert item["has_analysis"] is False

def test_get_email_by_id():
    """Test GET /api/emails/{id} with full nested relational data."""
    # Find email #1
    response = client.get("/api/emails/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["subject"] == "Internal Assessment Marks Submission"
    assert data["is_read"] is True  # marked as read upon viewing
    assert data["analysis"] is not None
    assert data["analysis"]["category"] == "Academic"
    assert len(data["analysis"]["evidences"]) >= 3
    assert len(data["action_items"]) == 2
    assert len(data["meetings"]) == 1
    assert data["meetings"][0]["location"] == "Seminar Hall"

def test_get_email_not_found():
    """Test GET /api/emails/{id} returns 404 for nonexistent id."""
    response = client.get("/api/emails/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_get_dashboard():
    """Test GET /api/dashboard returns comprehensive operational KPIs and feeds."""
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    metrics = data["metrics"]
    assert metrics["total_emails"] == 15
    assert metrics["high_priority_count"] >= 5
    assert metrics["upcoming_deadlines_count"] >= 5
    assert metrics["upcoming_meetings_count"] >= 4
    assert metrics["pending_actions_count"] >= 5

    assert len(data["priority_emails"]) > 0
    assert len(data["upcoming_deadlines"]) > 0
    assert len(data["upcoming_meetings"]) > 0
    assert len(data["pending_tasks"]) > 0
    assert len(data["recent_emails"]) == 5

def test_get_deadlines():
    """Test GET /api/deadlines returns sorted upcoming deadlines."""
    response = client.get("/api/deadlines")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 8
    # Verify chronological ordering
    due_dates = [item["due_date"] for item in data if item["due_date"]]
    assert due_dates == sorted(due_dates)

def test_get_meetings():
    """Test GET /api/meetings returns scheduled meetings."""
    response = client.get("/api/meetings")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4
    assert any(m["title"] == "Internal Assessment Department Review Meeting" for m in data)

def test_get_action_items_and_patch():
    """Test GET /api/action-items and PATCH /api/action-items/{id} state toggle."""
    # Fetch action items
    response = client.get("/api/action-items?completed=false")
    assert response.status_code == 200
    items = response.json()
    assert len(items) > 0
    target_id = items[0]["id"]

    # Toggle to completed = True
    patch_resp = client.patch(f"/api/action-items/{target_id}", json={"completed": True})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["completed"] is True

    # Re-verify through GET
    db = SessionLocal()
    item = db.query(ActionItem).filter_by(id=target_id).first()
    assert item.completed is True
    db.close()

def test_patch_action_item_not_found():
    """Test PATCH /api/action-items/{id} returns 404 for invalid id."""
    response = client.patch("/api/action-items/99999", json={"completed": True})
    assert response.status_code == 404

def test_search_emails():
    """Test GET /api/search across sender, subject, body, summary."""
    # Search subject
    res1 = client.get("/api/search?q=Assessment")
    assert res1.status_code == 200
    assert any("Assessment" in e["subject"] for e in res1.json())

    # Search sender
    res2 = client.get("/api/search?q=hod.cse")
    assert res2.status_code == 200
    assert len(res2.json()) >= 1

    # Search body content
    res3 = client.get("/api/search?q=biometric")
    assert res3.status_code == 200
    assert len(res3.json()) >= 1

def test_get_categories():
    """Test GET /api/categories returns academic categories with counts."""
    response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    categories = [c["category"] for c in data]
    assert "Academic" in categories
    assert "Examination" in categories
    assert "Uncategorized" in categories

def test_get_analysis():
    """Test GET /api/analysis/{email_id} for analyzed and unanalyzed emails."""
    # Email 1 is analyzed
    res1 = client.get("/api/analysis/1")
    assert res1.status_code == 200
    data = res1.json()
    assert data["category"] == "Academic"
    assert data["priority"] == "HIGH"
    assert len(data["evidences"]) >= 3

    # Email 11 is unanalyzed -> 404
    res2 = client.get("/api/analysis/11")
    assert res2.status_code == 404

    # Email 99999 does not exist -> 404
    res3 = client.get("/api/analysis/99999")
    assert res3.status_code == 404

def test_post_email_analyze():
    """Test POST /api/emails/{id}/analyze in Stage 3."""
    # Existing analysis
    res1 = client.post("/api/emails/1/analyze")
    assert res1.status_code == 200
    assert res1.json()["status"] == "completed"

    # Unanalyzed email - now analyzed by MockAIService
    res2 = client.post("/api/emails/11/analyze")
    assert res2.status_code == 200
    assert res2.json()["status"] == "completed"
    assert "analysis" in res2.json()

    # Nonexistent email
    res3 = client.post("/api/emails/99999/analyze")
    assert res3.status_code == 404
