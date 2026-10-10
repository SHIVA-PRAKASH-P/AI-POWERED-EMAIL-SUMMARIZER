import logging
import urllib.parse
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.models.preference import FacultyPreference
from backend.app.core.session_manager import session_manager
from backend.app.core.auth import get_current_user, extract_session_token
from backend.app.services.email_provider_manager import email_provider_manager
from backend.app.services.oauth_service import oauth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/email-provider", tags=["Email Provider"])

@router.get("/status")
def get_provider_status(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Retrieve status of the configured and active email provider architecture,
    scoped strictly to the active user identity.
    """
    token = extract_session_token(request)
    if token and current_user.id == 1:
        # Explicit User 1 session: strictly isolated to Mock provider
        status = email_provider_manager.get_status(user_id=1)
        status["user_id"] = current_user.id
        status["user_email"] = current_user.email
        status["target_account"] = current_user.email
        status["active_provider"] = "mock"
        status["provider_name"] = "mock"
        status["is_mock"] = True
        status["is_authenticated"] = True
        status["fallback_active"] = False
        status["gmail_configured"] = False
        status["gmail_authenticated"] = False
        status["gmail_oauth"] = {
            "connected": False,
            "is_connected": False,
            "email": None,
            "provider": "gmail",
            "scope": settings.GMAIL_SCOPES,
            "configured": False,
            "college_account": settings.COLLEGE_GMAIL_ACCOUNT,
            "status_message": "User 1 (Mock User) operates exclusively with MockEmailProvider."
        }
        return status
    else:
        # User 2 or generic system inspection
        eff_user_id = current_user.id if token else 2
        status = email_provider_manager.get_status(user_id=eff_user_id)
        oauth_status = oauth_service.get_status(user_id=eff_user_id)
        status["gmail_oauth"] = oauth_status
        status["user_id"] = current_user.id
        status["user_email"] = current_user.email
        status["target_account"] = current_user.email
        if oauth_status.get("connected"):
            status["active_provider"] = "gmail"
            status["is_authenticated"] = True
        return status

@router.post("/sync")
def sync_emails_from_provider(
    limit: int = Query(15, ge=1, le=100, description="Max emails to fetch from provider"),
    provider: Optional[str] = Query(None, max_length=20, pattern=r"^(?i)(mock|gmail)$", description="Optional provider override ('mock' or 'gmail')"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger ingestion and idempotent database synchronization from provider scoped to user."""
    try:
        # User 1 cannot sync from gmail provider
        eff_provider = "mock" if current_user.id == 1 else provider
        result = email_provider_manager.sync_emails(
            db=db,
            limit=limit,
            provider_type=eff_provider,
            run_ai_pipeline=True,
            user_id=current_user.id
        )
        return {
            "success": True,
            "message": f"Synchronized emails using provider '{result['provider']}'.",
            "data": result
        }
    except Exception as exc:
        db.rollback()
        logger.error("Provider sync failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to synchronize emails from provider."
        )

# ==============================================================================
# Google OAuth 2.0 Endpoints for College Gmail (Stage 19A)
# ==============================================================================

@router.get("/gmail/connect")
def initiate_gmail_oauth(
    request: Request,
    redirect: bool = Query(False, description="Whether to automatically HTTP redirect to Google authorization page"),
    redirect_uri: Optional[str] = Query(None, description="Optional custom redirect URI override"),
    force_new: bool = Query(False, description="Allow initiating OAuth flow even if active session is User 1"),
    current_user: User = Depends(get_current_user)
):
    """Start Google OAuth 2.0 authorization flow requesting read-only Gmail access.
    
    Generates a cryptographically random, timestamped CSRF state and Google consent URL.
    """
    token = extract_session_token(request)
    if token and current_user.id == 1 and not force_new:
        raise HTTPException(
            status_code=403,
            detail="User 1 (Mock User) operates exclusively with MockEmailProvider. Only User 2 can connect College Gmail."
        )

    if not settings.is_google_oauth_configured:
        raise HTTPException(
            status_code=400,
            detail=(
                "Google OAuth credentials not configured. Please define GOOGLE_CLIENT_ID and "
                "GOOGLE_CLIENT_SECRET in environment variables or .env file."
            )
        )

    try:
        flow_data = oauth_service.generate_authorization_url(redirect_uri=redirect_uri)
        auth_url = flow_data["authorization_url"]

        if redirect:
            return RedirectResponse(url=auth_url, status_code=302)

        return {
            "status": "success",
            "authorization_url": auth_url,
            "state": flow_data["state"],
            "target_account": settings.COLLEGE_GMAIL_ACCOUNT,
            "scope": settings.GMAIL_SCOPES
        }
    except Exception as e:
        logger.error(f"Failed to generate Google OAuth authorization URL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate authorization URL: {str(e)}")

@router.get("/gmail/oauth/callback")
def handle_gmail_oauth_callback(
    code: Optional[str] = Query(None, description="Google authorization code"),
    state: Optional[str] = Query(None, description="CSRF state parameter"),
    error: Optional[str] = Query(None, description="Google OAuth error response"),
    redirect_uri: Optional[str] = Query(None, description="Optional redirect URI override matching initial request"),
    db: Session = Depends(get_db)
):
    """Handle the Google OAuth 2.0 authorization callback:
    
    1. Validates single-use CSRF state token.
    2. Exchanges authorization code for Google credentials.
    3. Queries Gmail API to verify authenticated Google account identity.
    4. Registers or loads User identity in database and sets up default preferences.
    5. Saves credentials securely per user.
    6. Issues a new server session token and sets cookie.
    7. Redirects user to frontend settings page with clean status parameters.
    """
    frontend_base = settings.cors_origins_list[0] if settings.cors_origins_list else "http://127.0.0.1:5173"

    if error:
        logger.warning(f"Google OAuth authorization denied by user or server: {error}")
        return RedirectResponse(
            url=f"{frontend_base}/settings?oauth=error&reason={urllib.parse.quote(error)}",
            status_code=302
        )

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing authorization code or state in OAuth callback.")

    # 1. CSRF State Validation
    if not oauth_service.validate_state(state):
        logger.warning("Rejected OAuth callback with invalid or expired CSRF state.")
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state parameter.")

    # 2. Token Exchange
    try:
        credentials = oauth_service.exchange_code(code=code, state=state, redirect_uri=redirect_uri)
    except Exception as e:
        logger.error(f"Failed to exchange authorization code for tokens: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{frontend_base}/settings?oauth=error&reason=token_exchange_failed",
            status_code=302
        )

    # 3. Account Identity Verification (accepts any authenticated Google account)
    try:
        is_verified, authenticated_email, verification_msg = oauth_service.verify_account_identity(credentials)
        if not is_verified:
            # Reject immediately — do NOT save credentials for unauthorized account
            logger.warning(f"OAuth account rejected: {verification_msg}")
            return RedirectResponse(
                url=f"{frontend_base}/settings?oauth=error&reason=wrong_account&attempted={urllib.parse.quote(authenticated_email or 'unknown')}",
                status_code=302
            )

        # 4. Resolve or create User in DB for this authenticated Gmail account
        user = db.query(User).filter(User.email.ilike(authenticated_email)).first()
        if not user:
            name_part = authenticated_email.split("@")[0].replace(".", " ").title()
            user = User(
                email=authenticated_email,
                name=name_part,
                role="Faculty",
                provider_type="gmail"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Ensure default preferences exist for new user
            pref = db.query(FacultyPreference).filter(FacultyPreference.user_id == user.id).first()
            if not pref:
                db.add(FacultyPreference(user_id=user.id))
                db.commit()
        else:
            if user.provider_type != "gmail" and user.id != 1:
                user.provider_type = "gmail"
                db.commit()

        # 5. Save credentials securely per user
        oauth_service.save_credentials(credentials, authenticated_email, user_id=user.id)
        logger.info(f"Google OAuth successfully established for user #{user.id} ({authenticated_email})")

        # 6. Register allowed email with server session manager and create session
        session_manager.register_allowed_email(authenticated_email)
        session_token = session_manager.create_session(user_id=user.id, user_email=user.email)

        # 7. Redirect with session cookie set so frontend is automatically switched
        redirect_url = f"{frontend_base}/settings?oauth=success&email={urllib.parse.quote(authenticated_email)}&user_id={user.id}"
        response = RedirectResponse(url=redirect_url, status_code=302)
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=False,
            samesite="lax",
            max_age=86400
        )
        return response
    except Exception as e:
        logger.error(f"Error during Gmail account identity verification: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{frontend_base}/settings?oauth=error&reason=verification_failed",
            status_code=302
        )

@router.get("/gmail/status")
def get_gmail_connection_status(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Retrieve connection status of the Gmail account.
    
    Safe telemetry: never exposes access tokens, refresh tokens, or client secrets.
    """
    token = extract_session_token(request)
    if token and current_user.id == 1:
        return {
            "connected": False,
            "is_connected": False,
            "email": None,
            "provider": "gmail",
            "scope": settings.GMAIL_SCOPES,
            "configured": False,
            "college_account": settings.COLLEGE_GMAIL_ACCOUNT,
            "status_message": "User 1 (Mock User) operates exclusively with MockEmailProvider."
        }
    eff_user_id = current_user.id if token else 2
    status = oauth_service.get_status(user_id=eff_user_id)
    status["is_connected"] = status.get("connected", False)
    return status

@router.post("/gmail/disconnect")
def disconnect_gmail_account(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Disconnect and revoke local credentials for the Gmail account."""
    token = extract_session_token(request)
    if token and current_user.id == 1:
        raise HTTPException(
            status_code=403,
            detail="User 1 (Mock User) cannot disconnect or modify College Gmail OAuth credentials."
        )
    return oauth_service.disconnect(user_id=current_user.id if token else 2)

@router.post("/gmail/sync")
def sync_gmail_emails(
    request: Request,
    limit: int = Query(60, ge=1, le=60, description="Max Gmail emails to fetch (capped strictly at 60 for Stage 19C)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Synchronize a controlled batch of latest emails from the connected Gmail account.
    
    Security & Isolation Guarantees (Stage 19C & Multi-Account):
    - Reserved for Gmail accounts (provider_type == 'gmail' or user_id >= 2). User 1 is rejected with HTTP 403 Forbidden.
    - Unauthenticated requests are rejected with HTTP 403 Forbidden.
    - Requires active Google OAuth connection (returns HTTP 400 Bad Request if disconnected).
    - Capped at maximum 60 messages (never fetches more than 60 messages).
    - Read-only scope: gmail.readonly only. Zero modify/trash/delete/send calls.
    - Persisted with current_user.id.
    - Deduplicated via provider_message_id.
    """
    token = extract_session_token(request)
    if not token or current_user.id == 1 or current_user.provider_type != "gmail":
        raise HTTPException(
            status_code=403,
            detail="Forbidden: User 1 (Mock User) operates exclusively with MockEmailProvider. Only User 2 can synchronize Gmail messages."
        )

    oauth_status = oauth_service.get_status(user_id=current_user.id)
    if not oauth_status.get("connected"):
        raise HTTPException(
            status_code=400,
            detail="College Gmail account is not connected. Please authenticate via Google OAuth in Settings before synchronizing."
        )

    effective_limit = min(max(1, limit), 60)

    try:
        result = email_provider_manager.sync_emails(
            db=db,
            limit=effective_limit,
            provider_type="gmail",
            run_ai_pipeline=True,
            user_id=current_user.id
        )
        return {
            "success": True,
            "message": f"Successfully synchronized {result.get('imported', 0)} emails from College Gmail.",
            "data": {
                "fetched": result.get("fetched", 0),
                "imported": result.get("imported", 0),
                "skipped_duplicates": result.get("skipped_duplicates", result.get("skipped", 0)),
                "failed": result.get("failed", 0),
                "user_id": current_user.id,
                "target_account": current_user.email,
                "provider": "gmail"
            }
        }
    except Exception as exc:
        db.rollback()
        logger.error("Gmail synchronization failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to synchronize emails from Gmail: {str(exc)}"
        )

