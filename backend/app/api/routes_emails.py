from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, func
from typing import List, Optional

from backend.app.database.session import get_db
from backend.app.models import User, Email, AIAnalysis, ActionItem, Meeting
from backend.app.core.auth import get_current_user
from backend.app.schemas import EmailSummaryResponse, EmailDetailResponse
from backend.app.utils.sanitizer import sanitize_sql_like

router = APIRouter(prefix="/api", tags=["Emails"])

def email_to_summary(email: Email) -> EmailSummaryResponse:
    """Helper to convert Email ORM model to EmailSummaryResponse."""
    has_analysis = email.analysis is not None
    body_clean = " ".join(email.body.split())
    preview = body_clean[:120] + ("..." if len(body_clean) > 120 else "")
    has_deadline = any(a.due_date is not None for a in email.action_items)
    
    return EmailSummaryResponse(
        id=email.id,
        sender=email.sender,
        recipient=email.recipient,
        subject=email.subject,
        body_preview=preview,
        received_at=email.received_at,
        is_read=email.is_read,
        created_at=email.created_at,
        has_analysis=has_analysis,
        category=email.analysis.category if has_analysis else None,
        priority=email.analysis.priority if has_analysis else None,
        priority_reason=email.analysis.priority_reason if has_analysis else None,
        action_items_count=len(email.action_items),
        meetings_count=len(email.meetings),
        has_deadline=has_deadline
    )

@router.get("/emails", response_model=List[EmailSummaryResponse])
def get_emails(
    search: Optional[str] = Query(None, max_length=200, description="Search subject, sender, body"),
    category: Optional[str] = Query(None, max_length=50, description="Filter by category"),
    priority: Optional[str] = Query(None, max_length=10, pattern=r"^(?i)(HIGH|MEDIUM|LOW)$", description="Filter by priority: HIGH, MEDIUM, LOW"),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    has_deadline: Optional[bool] = Query(None, description="Filter emails with deadlines"),
    deadline_status: Optional[str] = Query(None, max_length=20, pattern=r"^(?i)(UPCOMING|DUE_TODAY|EXPIRED)$", description="Filter emails by deadline status: UPCOMING, DUE_TODAY, EXPIRED"),
    is_analyzed: Optional[bool] = Query(None, description="Filter emails with AI analysis"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve emails with rich multi-parameter filtering and pagination, scoped to active user."""
    query = db.query(Email).outerjoin(AIAnalysis).filter(Email.user_id == current_user.id)

    if search:
        safe_search = sanitize_sql_like(search.strip())
        search_pattern = f"%{safe_search}%"
        query = query.filter(
            or_(
                Email.subject.ilike(search_pattern, escape="\\"),
                Email.sender.ilike(search_pattern, escape="\\"),
                Email.body.ilike(search_pattern, escape="\\"),
                AIAnalysis.summary.ilike(search_pattern, escape="\\")
            )
        )

    if category:
        query = query.filter(AIAnalysis.category.ilike(category))

    if priority:
        query = query.filter(AIAnalysis.priority == priority.upper())

    if is_read is not None:
        query = query.filter(Email.is_read == is_read)

    if deadline_status:
        from datetime import datetime, timezone
        current_date_str = datetime.now(timezone.utc).date().strftime("%Y-%m-%d")
        d_status = deadline_status.upper()
        if d_status == "UPCOMING":
            query = query.filter(
                or_(
                    Email.action_items.any(and_(ActionItem.due_date != None, ActionItem.due_date != "", ActionItem.due_date > current_date_str)),
                    and_(AIAnalysis.deadline_date != None, AIAnalysis.deadline_date > current_date_str)
                )
            )
        elif d_status == "DUE_TODAY":
            query = query.filter(
                or_(
                    Email.action_items.any(and_(ActionItem.due_date != None, ActionItem.due_date != "", ActionItem.due_date == current_date_str)),
                    and_(AIAnalysis.deadline_date != None, AIAnalysis.deadline_date == current_date_str)
                )
            )
        elif d_status == "EXPIRED":
            query = query.filter(
                or_(
                    Email.action_items.any(and_(ActionItem.due_date != None, ActionItem.due_date != "", ActionItem.due_date < current_date_str)),
                    and_(AIAnalysis.deadline_date != None, AIAnalysis.deadline_date < current_date_str)
                )
            )

    if is_analyzed is not None:
        if is_analyzed:
            query = query.filter(Email.analysis != None)
        else:
            query = query.filter(Email.analysis == None)

    emails = query.order_by(desc(Email.received_at)).offset(skip).limit(limit).all()

    # Filter has_deadline in Python or join
    results = [email_to_summary(e) for e in emails]
    if has_deadline is not None:
        results = [r for r in results if r.has_deadline == has_deadline]

    return results

@router.get("/emails/{id}", response_model=EmailDetailResponse)
def get_email_by_id(
    id: int = Path(..., ge=1, description="Positive integer email ID"),
    mark_as_read: bool = Query(True, description="Automatically mark email as read when opened"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve complete email details scoped strictly to active user."""
    email = db.query(Email).filter(Email.id == id, Email.user_id == current_user.id).first()
    if not email:
        raise HTTPException(status_code=404, detail=f"Email with ID {id} not found")

    if mark_as_read and not email.is_read:
        email.is_read = True
        db.commit()
        db.refresh(email)

    return email

@router.patch("/emails/{id}/read", response_model=EmailDetailResponse)
def mark_email_as_read(
    id: int = Path(..., ge=1, description="Positive integer email ID"),
    is_read: bool = Query(True, description="Mark as read or unread"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Explicitly mark an email as read or unread for the active user."""
    email = db.query(Email).filter(Email.id == id, Email.user_id == current_user.id).first()
    if not email:
        raise HTTPException(status_code=404, detail=f"Email with ID {id} not found")

    email.is_read = is_read
    db.commit()
    db.refresh(email)
    return email

@router.get("/search", response_model=List[EmailSummaryResponse])
def search_emails(
    q: str = Query(..., min_length=1, max_length=200, description="Query text to search"),
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Multi-field search across sender, subject, body, summary, and category for active user."""
    safe_q = sanitize_sql_like(q.strip())
    search_pattern = f"%{safe_q}%"
    emails = db.query(Email).outerjoin(AIAnalysis).filter(
        Email.user_id == current_user.id,
        or_(
            Email.subject.ilike(search_pattern, escape="\\"),
            Email.sender.ilike(search_pattern, escape="\\"),
            Email.body.ilike(search_pattern, escape="\\"),
            AIAnalysis.summary.ilike(search_pattern, escape="\\"),
            AIAnalysis.category.ilike(search_pattern, escape="\\")
        )
    ).order_by(desc(Email.received_at)).limit(limit).all()

    return [email_to_summary(e) for e in emails]

@router.get("/categories")
def get_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve list of distinct academic categories with associated email counts for active user."""
    analysis_counts = (
        db.query(AIAnalysis.category, func.count(AIAnalysis.id))
        .join(Email)
        .filter(Email.user_id == current_user.id)
        .group_by(AIAnalysis.category)
        .all()
    )

    result = [{"category": cat, "count": count} for cat, count in analysis_counts]
    
    # Check un-analyzed count
    unanalyzed_count = db.query(Email).filter(Email.user_id == current_user.id, Email.analysis == None).count()
    if unanalyzed_count > 0:
        result.append({"category": "Uncategorized", "count": unanalyzed_count})

    return result

