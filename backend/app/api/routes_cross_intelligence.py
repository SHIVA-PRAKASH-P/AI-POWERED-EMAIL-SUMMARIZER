"""Cross-Email Intelligence API Endpoints.

Provides endpoints for thread context, related emails, chronological milestone timelines,
and inbox topic clustering.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.email import Email
from backend.app.models.user import User
from backend.app.core.auth import get_current_user
from backend.app.ai.cross_email_service import cross_email_service

router = APIRouter(tags=["Cross-Email Intelligence"])

@router.get("/api/emails/{email_id}/cross-intelligence")
def get_email_cross_intelligence(
    email_id: int = Path(..., ge=1, description="Positive integer email ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve related correspondence, thread timeline, and cross-email action progression."""
    email = db.query(Email).filter(Email.id == email_id, Email.user_id == current_user.id).first()
    if not email:
        raise HTTPException(status_code=404, detail=f"Email #{email_id} not found")

    insights = cross_email_service.get_cross_email_insights(db, email_id, user_id=current_user.id)
    return {
        "success": True,
        "data": insights
    }

@router.get("/api/cross-intelligence/clusters")
def get_inbox_topic_clusters(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve global academic topic clusters across the current user's inbox."""
    clusters = cross_email_service.get_topic_clusters(db, user_id=current_user.id)
    return {
        "success": True,
        "total_clusters": len(clusters),
        "clusters": clusters
    }

