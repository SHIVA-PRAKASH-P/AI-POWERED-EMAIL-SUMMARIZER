"""Authentication & User Identity API Endpoints (Stage 19B).

Provides:
1. Server-controlled session creation/switching between verified pre-registered users.
2. Inspection of current active user identity.
3. Directory of available institutional user profiles.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.core.session_manager import session_manager
from backend.app.core.auth import get_current_user, extract_session_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["User Identity & Authentication"])

class SwitchSessionRequest(BaseModel):
    email: Optional[str] = None
    user_email: Optional[str] = None

    @property
    def target_email(self) -> str:
        return (self.email or self.user_email or "").strip().lower()

class UserProfileResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    provider_type: str

@router.get("/users", response_model=List[UserProfileResponse])
def list_registered_users(db: Session = Depends(get_db)):
    """List pre-registered institutional user identities."""
    users = db.query(User).order_by(User.id).all()
    return [
        UserProfileResponse(
            id=u.id,
            email=u.email,
            name=u.name,
            role=u.role,
            provider_type=u.provider_type
        )
        for u in users
    ]

@router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Return the authenticated user profile based on the verified server session."""
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        provider_type=current_user.provider_type
    )

@router.post("/switch-session")
def switch_user_session(
    body: SwitchSessionRequest,
    response: Response,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Switch active user identity by creating a new server-controlled session.
    
    Security Guarantee:
    - Only pre-registered users in the database can be activated.
    - Arbitrary email addresses are rejected with HTTP 400.
    """
    clean_email = body.target_email
    if not clean_email:
        raise HTTPException(status_code=400, detail="User not authorized: email required")

    user = db.query(User).filter(User.email.ilike(clean_email)).first()
    
    if not user:
        logger.warning("Session switch rejected for unregistered identity: %s", clean_email)
        raise HTTPException(
            status_code=400,
            detail=f"User not authorized. Identity '{clean_email}' is not permitted."
        )

    try:
        session_manager.register_allowed_email(user.email)
        token = session_manager.create_session(user_id=user.id, user_email=user.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"User not authorized: {str(e)}")

    # Set session cookie for seamless browser navigation
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=False,  # Allow frontend API client to read or supply in Authorization header
        samesite="lax",
        max_age=86400
    )

    return {
        "status": "success",
        "message": f"Successfully activated server session for {user.name}.",
        "session_token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "provider_type": user.provider_type
        }
    }

@router.post("/logout")
def logout_session(request: Request, response: Response):
    """Revoke active session token."""
    token = extract_session_token(request)
    if token:
        session_manager.revoke_session(token)
    response.delete_cookie("session_token")
    return {"status": "success", "message": "Session revoked."}
