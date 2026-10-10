from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import List, Optional

from backend.app.database.session import get_db
from backend.app.models import User, ActionItem, Meeting, Email
from backend.app.core.auth import get_current_user
from backend.app.schemas import (
    ActionItemResponse,
    ActionItemUpdate,
    MeetingResponse,
    DeadlineItem
)

router = APIRouter(prefix="/api", tags=["Actions, Deadlines & Meetings"])

@router.get("/action-items", response_model=List[ActionItemResponse])
@router.get("/actions", response_model=List[ActionItemResponse], include_in_schema=False)
def get_action_items(
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    priority: Optional[str] = Query(None, max_length=10, pattern=r"^(?i)(HIGH|MEDIUM|LOW)$", description="Filter by priority: HIGH, MEDIUM, LOW"),
    relationship_type: Optional[str] = Query(None, max_length=30, pattern=r"^(?i)(DUE_ON|PREPARE_BEFORE|ATTEND_BY|COMMUNICATE_BY|STANDALONE)$", description="Filter by relationship"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve action items for the active user with optional completion, priority, and relationship filters."""
    query = db.query(ActionItem).join(Email).filter(Email.user_id == current_user.id)

    if completed is not None:
        query = query.filter(ActionItem.completed == completed)

    if priority:
        query = query.filter(ActionItem.priority == priority.upper())

    if relationship_type:
        query = query.filter(ActionItem.relationship_type == relationship_type.upper())

    items = query.order_by(asc(ActionItem.completed), asc(ActionItem.due_date)).all()

    # Populate email metadata
    results = []
    for item in items:
        resp = ActionItemResponse.model_validate(item)
        resp.email_subject = item.email.subject if item.email else None
        resp.email_sender = item.email.sender if item.email else None
        results.append(resp)

    return results

@router.patch("/action-items/{id}", response_model=ActionItemResponse)
@router.patch("/actions/{id}", response_model=ActionItemResponse, include_in_schema=False)
def update_action_item(
    id: int = Path(..., ge=1, description="Positive action item ID"),
    update_data: ActionItemUpdate = ...,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update action item status (e.g., mark completed/pending) scoped strictly to the active user."""
    item = db.query(ActionItem).join(Email).filter(ActionItem.id == id, Email.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Action item with ID {id} not found")

    if update_data.completed is not None:
        item.completed = update_data.completed

    if update_data.priority is not None:
        item.priority = update_data.priority.upper()

    if update_data.due_date is not None:
        item.due_date = update_data.due_date

    if update_data.description is not None:
        item.description = update_data.description

    if update_data.relationship_type is not None:
        item.relationship_type = update_data.relationship_type.upper()

    if update_data.target_event is not None:
        item.target_event = update_data.target_event

    if update_data.relationship_reason is not None:
        item.relationship_reason = update_data.relationship_reason

    if update_data.binding_confidence is not None:
        item.binding_confidence = update_data.binding_confidence

    db.commit()
    db.refresh(item)

    resp = ActionItemResponse.model_validate(item)
    resp.email_subject = item.email.subject if item.email else None
    resp.email_sender = item.email.sender if item.email else None
    return resp

@router.get("/deadlines", response_model=List[DeadlineItem])
def get_deadlines(
    status: Optional[str] = Query("all", max_length=20, pattern=r"^(?i)(all|pending|completed)$", description="Options: 'all', 'pending', 'completed'"),
    deadline_status: Optional[str] = Query(None, max_length=20, pattern=r"^(?i)(UPCOMING|DUE_TODAY|EXPIRED)$", description="Options: 'UPCOMING', 'DUE_TODAY', 'EXPIRED'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all upcoming deadlines chronologically linked to tasks and source emails for active user."""
    from datetime import datetime, timezone
    from backend.app.utils.date_parser import compute_temporal_status

    current_date = datetime.now(timezone.utc).date()
    current_date_str = current_date.strftime("%Y-%m-%d")

    query = db.query(ActionItem).join(Email).filter(Email.user_id == current_user.id, ActionItem.due_date != None, ActionItem.due_date != "")

    if status == "pending":
        query = query.filter(ActionItem.completed == False)
    elif status == "completed":
        query = query.filter(ActionItem.completed == True)

    if deadline_status:
        d_status = deadline_status.upper()
        if d_status == "UPCOMING":
            query = query.filter(ActionItem.due_date > current_date_str)
        elif d_status == "DUE_TODAY":
            query = query.filter(ActionItem.due_date == current_date_str)
        elif d_status == "EXPIRED":
            query = query.filter(ActionItem.due_date < current_date_str)

    # Sort expired descending (most recent first), upcoming/due_today ascending (nearest first)
    if deadline_status and deadline_status.upper() == "EXPIRED":
        query = query.order_by(desc(ActionItem.due_date))
    else:
        query = query.order_by(asc(ActionItem.due_date))

    items = query.all()

    deadlines = []
    for item in items:
        status_computed, rel = compute_temporal_status(item.due_date, current_date=current_date)
        deadlines.append(
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
                deadline_status=status_computed,
                relative_status=rel
            )
        )

    return deadlines

@router.get("/meetings", response_model=List[MeetingResponse])
def get_meetings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all scheduled meetings sorted chronologically for active user."""
    meetings = (
        db.query(Meeting)
        .join(Email)
        .filter(Email.user_id == current_user.id)
        .order_by(asc(Meeting.meeting_date), asc(Meeting.meeting_time))
        .all()
    )

    results = []
    for m in meetings:
        resp = MeetingResponse.model_validate(m)
        resp.email_subject = m.email.subject if m.email else None
        resp.email_sender = m.email.sender if m.email else None
        results.append(resp)

    return results
