"""Faculty Personalization & Preferences API Endpoints (Stage 15).

Provides endpoints for retrieving, updating, and resetting personalized faculty profile
and priority determination criteria.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.core.auth import get_current_user
from backend.app.schemas.preference_schema import (
    FacultyPreferenceUpdate,
    FacultyPreferenceResponse
)
from backend.app.services.preference_service import preference_service

router = APIRouter(prefix="/api/preferences", tags=["Faculty Personalization"])

@router.get("", response_model=FacultyPreferenceResponse)
def get_faculty_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve current faculty personalization profile and priority settings for active user."""
    pref = preference_service.get_or_create_preferences(db, user_id=current_user.id)
    return pref

@router.put("", response_model=FacultyPreferenceResponse)
def update_faculty_preferences(
    updates: FacultyPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update faculty profile, custom keywords, focus categories, and urgency settings for active user."""
    updated = preference_service.update_preferences(db, updates, user_id=current_user.id)
    return updated

@router.post("/reset", response_model=FacultyPreferenceResponse)
def reset_faculty_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset faculty personalization settings to balanced academic defaults for active user."""
    reset_pref = preference_service.reset_preferences(db, user_id=current_user.id)
    return reset_pref

