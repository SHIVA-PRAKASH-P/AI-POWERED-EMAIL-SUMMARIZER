import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.app.database.session import SessionLocal, reset_db
from backend.app.database.seed_data import seed_database
from backend.app.models import Email, ActionItem, AIAnalysis, Meeting, Evidence

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Seed clean academic database for frontend integration tests."""
    reset_db()
    db = SessionLocal()
    seed_database(db)
    db.close()

def test_frontend_dashboard_workflow():
    """Verify frontend Dashboard metrics and operational feeds."""
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert "metrics" in data
    metrics = data["metrics"]
    assert metrics["total_emails"] == 15
    assert metrics["unread_emails"] >= 0
    assert metrics["high_priority_count"] >= 0
    assert metrics["upcoming_deadlines_count"] >= 0
    assert metrics["upcoming_meetings_count"] >= 0
    assert metrics["pending_actions_count"] >= 0

    assert "priority_emails" in data
    assert "upcoming_deadlines" in data
    assert "upcoming_meetings" in data
    assert "pending_tasks" in data

def test_frontend_inbox_filtering_and_search_workflow():
    """Verify frontend Inbox search, dynamic categories, and filtering."""
    # 1. Fetch dynamic categories
    cat_res = client.get("/api/categories")
    assert cat_res.status_code == 200
    cats = cat_res.json()
    assert len(cats) > 0
    cat_names = [c["category"] for c in cats]

    # 2. Filter by category
    first_cat = cat_names[0]
    filtered_res = client.get(f"/api/emails?category={first_cat}")
    assert filtered_res.status_code == 200
    for em in filtered_res.json():
        assert em["category"] == first_cat

    # 3. Search query
    search_res = client.get("/api/emails?search=examination")
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) > 0

    # 4. Filter by unread
    unread_res = client.get("/api/emails?is_read=false")
    assert unread_res.status_code == 200
    for em in unread_res.json():
        assert em["is_read"] is False

def test_frontend_email_detail_and_read_tracking_workflow():
    """Verify two-panel Email Detail loading and automatic mark-as-read flow."""
    # Find an unread email
    emails_res = client.get("/api/emails?is_read=false")
    unreads = emails_res.json()
    assert len(unreads) > 0
    target_id = unreads[0]["id"]

    # View email detail
    detail_res = client.get(f"/api/emails/{target_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == target_id
    assert "body" in detail
    assert "analysis" in detail

    # Explicitly test mark as read endpoint
    read_res = client.patch(f"/api/emails/{target_id}/read?is_read=true")
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True

    # Verify persistence in DB
    check_res = client.get(f"/api/emails/{target_id}")
    assert check_res.json()["is_read"] is True

def test_frontend_ai_orchestration_trigger_workflow():
    """Verify triggering AI Orchestrator with force_refresh from the UI."""
    email_id = 1
    analyze_res = client.post(f"/api/emails/{email_id}/analyze?force_refresh=true")
    assert analyze_res.status_code == 200
    data = analyze_res.json()
    assert data["status"] == "completed"
    assert "analysis" in data
    analysis = data["analysis"]
    assert analysis["email_id"] == email_id
    assert "summary" in analysis
    assert "priority" in analysis
    assert "priority_reason" in analysis
    assert "evidences" in analysis

    # Verify grounded character spans
    for ev in analysis["evidences"]:
        assert "char_start" in ev
        assert "char_end" in ev
        assert ev["char_start"] >= 0
        assert ev["char_end"] > ev["char_start"]
        assert ev["validation_status"] in ["VERIFIED", "INFERRED", "AMBIGUOUS"]

def test_frontend_action_item_completion_toggle_workflow():
    """Verify instant checkbox toggle on Action Items board and persistence."""
    # Fetch action items
    actions_res = client.get("/api/action-items")
    assert actions_res.status_code == 200
    actions = actions_res.json()
    assert len(actions) > 0
    target_action = actions[0]
    initial_status = target_action["completed"]

    # Toggle
    patch_res = client.patch(f"/api/action-items/{target_action['id']}", json={"completed": not initial_status})
    assert patch_res.status_code == 200
    assert patch_res.json()["completed"] == (not initial_status)

    # Verify in DB
    db = SessionLocal()
    item = db.query(ActionItem).filter(ActionItem.id == target_action["id"]).first()
    assert item.completed == (not initial_status)
    db.close()

def test_frontend_deadlines_hub_workflow():
    """Verify Deadlines page status filtering and relationship metadata."""
    res_all = client.get("/api/deadlines?status=all")
    assert res_all.status_code == 200
    deadlines = res_all.json()
    assert len(deadlines) > 0

    for d in deadlines:
        assert "due_date" in d
        assert "task_description" in d
        assert "relationship_type" in d
        assert d["relationship_type"] in [
            "DUE_ON", "PREPARE_BEFORE", "ATTEND_BY", "COMMUNICATE_BY", "STANDALONE"
        ]

def test_frontend_meetings_hub_workflow():
    """Verify Meetings page extraction data."""
    res = client.get("/api/meetings")
    assert res.status_code == 200
    meetings = res.json()
    assert len(meetings) > 0
    for m in meetings:
        assert "title" in m
        assert "meeting_time" in m
        assert "location" in m

def test_frontend_settings_telemetry_workflow():
    """Verify Settings page live database and health telemetry."""
    # DB Status
    db_res = client.get("/api/db-status")
    assert db_res.status_code == 200
    db_data = db_res.json()
    assert db_data["status"] == "connected"
    counts = db_data["counts"]
    assert counts["emails"] == 15
    assert counts["analyses"] >= 10
    assert counts["action_items"] > 0
    assert counts["meetings"] > 0

    # Health
    health_res = client.get("/api/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["status"] == "healthy"
    assert "ai_mode" in health_data
