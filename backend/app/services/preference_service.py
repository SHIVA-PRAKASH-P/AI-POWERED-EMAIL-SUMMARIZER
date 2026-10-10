"""Faculty Personalization & Preference Management Service (Stage 15).

Handles retrieval, persistence, and default initialization of user-configured
faculty preferences and priority tuning criteria in the database.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.app.models.preference import FacultyPreference
from backend.app.schemas.preference_schema import FacultyPreferenceUpdate

DEFAULT_ROLE = "Professor & Academic Incharge"
DEFAULT_DEPT = "Computer Science & Engineering"
DEFAULT_CATEGORIES = "Examination,Academic"
DEFAULT_HIGH_KW = "marks,question paper,naac,accreditation,urgent"
DEFAULT_LOW_KW = "newsletter,invitation,webinar,sports"

class PreferenceService:
    """Manages CRUD persistence for faculty personalization profiles with multi-user isolation."""

    @staticmethod
    def get_or_create_preferences(db: Session, user_id: int = 1) -> FacultyPreference:
        """Fetch stored faculty preferences for the specified user or initialize defaults if missing."""
        pref = db.query(FacultyPreference).filter(FacultyPreference.user_id == user_id).first()
        if not pref:
            # Fallback check for legacy record without user_id if user_id == 1
            if user_id == 1:
                pref = db.query(FacultyPreference).filter(FacultyPreference.id == 1).first()
                if pref:
                    pref.user_id = 1
                    db.commit()
                    db.refresh(pref)
                    return pref

            name = "Shivaprakash P" if user_id == 2 else "Dr. Faculty"
            role = "Faculty / Student Researcher" if user_id == 2 else DEFAULT_ROLE
            pref = FacultyPreference(
                user_id=user_id,
                faculty_name=name,
                role=role,
                department=DEFAULT_DEPT,
                priority_mode="BALANCED",
                high_priority_categories=DEFAULT_CATEGORIES,
                custom_keywords_high=DEFAULT_HIGH_KW,
                custom_keywords_low=DEFAULT_LOW_KW,
                deadline_urgency_days=3,
                authority_weight=1.0,
                deadline_weight=1.0,
                updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.add(pref)
            db.commit()
            db.refresh(pref)
        return pref

    @staticmethod
    def update_preferences(db: Session, update_data: FacultyPreferenceUpdate, user_id: int = 1) -> FacultyPreference:
        """Update existing faculty preferences for the specified user with validated input."""
        pref = PreferenceService.get_or_create_preferences(db, user_id=user_id)
        
        updates = update_data.model_dump(exclude_unset=True)
        for key, value in updates.items():
            if value is not None:
                setattr(pref, key, value)

        pref.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        db.refresh(pref)
        return pref

    @staticmethod
    def reset_preferences(db: Session, user_id: int = 1) -> FacultyPreference:
        """Reset preferences for the specified user to standard balanced academic defaults."""
        pref = PreferenceService.get_or_create_preferences(db, user_id=user_id)
        pref.faculty_name = "Shivaprakash P" if user_id == 2 else "Dr. Faculty"
        pref.role = "Faculty / Student Researcher" if user_id == 2 else DEFAULT_ROLE
        pref.department = DEFAULT_DEPT
        pref.priority_mode = "BALANCED"
        pref.high_priority_categories = DEFAULT_CATEGORIES
        pref.custom_keywords_high = DEFAULT_HIGH_KW
        pref.custom_keywords_low = DEFAULT_LOW_KW
        pref.deadline_urgency_days = 3
        pref.authority_weight = 1.0
        pref.deadline_weight = 1.0
        pref.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        db.refresh(pref)
        return pref

preference_service = PreferenceService()
