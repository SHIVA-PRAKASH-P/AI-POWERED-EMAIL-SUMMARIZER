from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func, case

from backend.app.database.session import get_db
from backend.app.models import User, Email, AIAnalysis, ActionItem, Meeting
from backend.app.core.auth import get_current_user
from backend.app.schemas import (
    DashboardResponse,
    DashboardMetrics,
    DeadlineItem,
    ActionItemResponse,
    MeetingResponse
)
from backend.app.api.routes_emails import email_to_summary
from backend.app.utils.date_parser import compute_temporal_status

router = APIRouter(prefix="/api", tags=["Dashboard"])

@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Compute and retrieve real-time operational dashboard metrics and feeds for the active user."""
    current_date = datetime.now(timezone.utc).date()
    current_date_str = current_date.strftime("%Y-%m-%d")

    total_emails = db.query(Email).filter(Email.user_id == current_user.id).count()
    unread_emails = db.query(Email).filter(Email.user_id == current_user.id, Email.is_read == False).count()
    high_priority_count = (
        db.query(AIAnalysis)
        .join(Email)
        .filter(Email.user_id == current_user.id, func.upper(AIAnalysis.priority) == "HIGH")
        .count()
    )
    medium_priority_count = (
        db.query(AIAnalysis)
        .join(Email)
        .filter(Email.user_id == current_user.id, func.upper(AIAnalysis.priority) == "MEDIUM")
        .count()
    )
    low_priority_count = (
        db.query(AIAnalysis)
        .join(Email)
        .filter(Email.user_id == current_user.id, func.upper(AIAnalysis.priority) == "LOW")
        .count()
    )
    upcoming_deadlines_count = (
        db.query(ActionItem)
        .join(Email)
        .filter(
            Email.user_id == current_user.id,
            ActionItem.due_date != None,
            ActionItem.due_date != "",
            ActionItem.due_date >= current_date_str,
            ActionItem.completed == False
        )
        .count()
    )
    expired_deadlines_count = (
        db.query(ActionItem)
        .join(Email)
        .filter(
            Email.user_id == current_user.id,
            ActionItem.due_date != None,
            ActionItem.due_date != "",
            ActionItem.due_date < current_date_str,
            ActionItem.completed == False
        )
        .count()
    )
    upcoming_meetings_count = (
        db.query(Meeting)
        .join(Email)
        .filter(Email.user_id == current_user.id)
        .count()
    )
    pending_actions_count = (
        db.query(ActionItem)
        .join(Email)
        .filter(Email.user_id == current_user.id, ActionItem.completed == False)
        .count()
    )

    metrics = DashboardMetrics(
        total_emails=total_emails,
        unread_emails=unread_emails,
        high_priority_count=high_priority_count,
        medium_priority_count=medium_priority_count,
        low_priority_count=low_priority_count,
        upcoming_deadlines_count=upcoming_deadlines_count,
        expired_deadlines_count=expired_deadlines_count,
        upcoming_meetings_count=upcoming_meetings_count,
        pending_actions_count=pending_actions_count
    )

    # Priority emails (HIGH first, then MEDIUM, ordered by received_at desc)
    priority_order = case(
        (func.upper(AIAnalysis.priority) == "HIGH", 1),
        (func.upper(AIAnalysis.priority) == "MEDIUM", 2),
        else_=3
    )
    priority_email_objs = (
        db.query(Email)
        .join(AIAnalysis)
        .filter(
            Email.user_id == current_user.id,
            func.upper(AIAnalysis.priority).in_(["HIGH", "MEDIUM"])
        )
        .order_by(priority_order, desc(Email.received_at))
        .limit(5)
        .all()
    )
    # If no HIGH/MEDIUM priority emails exist, fallback to recent emails of the user
    if not priority_email_objs:
        priority_email_objs = (
            db.query(Email)
            .filter(Email.user_id == current_user.id)
            .order_by(desc(Email.received_at))
            .limit(5)
            .all()
        )
    priority_emails = [email_to_summary(e) for e in priority_email_objs]

    # Upcoming Deadlines (pending, due_date >= current_date, chronologically sorted: nearest first)
    upcoming_items_objs = (
        db.query(ActionItem)
        .join(Email)
        .filter(
            Email.user_id == current_user.id,
            ActionItem.due_date != None,
            ActionItem.due_date != "",
            ActionItem.due_date >= current_date_str,
            ActionItem.completed == False
        )
        .order_by(asc(ActionItem.due_date))
        .limit(8)
        .all()
    )
    upcoming_deadlines = []
    for item in upcoming_items_objs:
        status, rel = compute_temporal_status(item.due_date, current_date=current_date)
        upcoming_deadlines.append(
            DeadlineItem(
                id=item.id,
                email_id=item.email_id,
                email_subject=item.email.subject if item.email else "Unknown Subject",
                email_sender=item.email.sender if item.email else "Unknown Sender",
                task_description=item.description,
                due_date=item.due_date or "",
                priority=item.priority,
                completed=item.completed,
                relationship_type=item.relationship_type or "DUE_ON",
                target_event=item.target_event,
                relationship_reason=item.relationship_reason,
                deadline_status=status,
                relative_status=rel
            )
        )

    # Expired Deadlines (pending, due_date < current_date, sorted most recently expired first)
    expired_items_objs = (
        db.query(ActionItem)
        .join(Email)
        .filter(
            Email.user_id == current_user.id,
            ActionItem.due_date != None,
            ActionItem.due_date != "",
            ActionItem.due_date < current_date_str,
            ActionItem.completed == False
        )
        .order_by(desc(ActionItem.due_date))
        .limit(8)
        .all()
    )
    expired_deadlines = []
    for item in expired_items_objs:
        status, rel = compute_temporal_status(item.due_date, current_date=current_date)
        expired_deadlines.append(
            DeadlineItem(
                id=item.id,
                email_id=item.email_id,
                email_subject=item.email.subject if item.email else "Unknown Subject",
                email_sender=item.email.sender if item.email else "Unknown Sender",
                task_description=item.description,
                due_date=item.due_date or "",
                priority=item.priority,
                completed=item.completed,
                relationship_type=item.relationship_type or "DUE_ON",
                target_event=item.target_event,
                relationship_reason=item.relationship_reason,
                deadline_status=status,
                relative_status=rel
            )
        )

    # Upcoming Meetings
    meeting_objs = (
        db.query(Meeting)
        .join(Email)
        .filter(Email.user_id == current_user.id)
        .order_by(asc(Meeting.meeting_date), asc(Meeting.meeting_time))
        .limit(5)
        .all()
    )
    upcoming_meetings = []
    for m in meeting_objs:
        resp = MeetingResponse.model_validate(m)
        resp.email_subject = m.email.subject if m.email else None
        resp.email_sender = m.email.sender if m.email else None
        upcoming_meetings.append(resp)

    # Pending Tasks
    task_objs = (
        db.query(ActionItem)
        .join(Email)
        .filter(Email.user_id == current_user.id, ActionItem.completed == False)
        .order_by(asc(ActionItem.due_date))
        .limit(6)
        .all()
    )
    pending_tasks = []
    for t in task_objs:
        resp = ActionItemResponse.model_validate(t)
        resp.email_subject = t.email.subject if t.email else None
        resp.email_sender = t.email.sender if t.email else None
        pending_tasks.append(resp)

    # Recent Emails
    recent_email_objs = (
        db.query(Email)
        .filter(Email.user_id == current_user.id)
        .order_by(desc(Email.received_at))
        .limit(5)
        .all()
    )
    recent_emails = [email_to_summary(e) for e in recent_email_objs]

    return DashboardResponse(
        metrics=metrics,
        priority_emails=priority_emails,
        upcoming_deadlines=upcoming_deadlines,
        expired_deadlines=expired_deadlines,
        upcoming_meetings=upcoming_meetings,
        pending_tasks=pending_tasks,
        recent_emails=recent_emails
    )
