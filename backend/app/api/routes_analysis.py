import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.app.database.session import get_db
from backend.app.models import Email, AIAnalysis, ActionItem, Meeting, Evidence, Entity, User
from backend.app.core.auth import get_current_user
from backend.app.schemas import (
    AIAnalysisResponse,
    AssertionVerificationRequest,
    AssertionVerificationResponse
)
from backend.app.ai.orchestrator import AIOrchestrator
from backend.app.ai.evidence_service import EvidenceValidationService
from backend.app.services.preference_service import preference_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["AI Analysis & Agent Orchestrator"])

# Instantiate the multi-agent AI orchestrator
orchestrator = AIOrchestrator()

@router.get("/analysis/{email_id}", response_model=AIAnalysisResponse)
def get_analysis_by_email_id(
    email_id: int = Path(..., ge=1, description="Positive integer email ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve structured AI analysis and evidence anchors for a specific email."""
    email = db.query(Email).filter(Email.id == email_id, Email.user_id == current_user.id).first()
    if not email:
        raise HTTPException(status_code=404, detail=f"Email with ID {email_id} not found")

    analysis = db.query(AIAnalysis).filter(AIAnalysis.email_id == email_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail=f"No AI analysis found for email ID {email_id}")

    return analysis

@router.post("/emails/{id}/analyze")
def trigger_email_analysis(
    id: int = Path(..., ge=1, description="Positive integer email ID"),
    force_refresh: bool = Query(False, description="Re-run analysis even if already analyzed"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger multi-agent AI orchestration pipeline for an email.
    
    Coordinates: Context Analysis -> Task Detection -> Classification -> Temporal -> Meeting -> 
    Action -> Priority -> Summarization -> Evidence Grounding -> Persistence.
    """
    email = db.query(Email).filter(Email.id == id, Email.user_id == current_user.id).first()
    if not email:
        raise HTTPException(status_code=404, detail=f"Email with ID {id} not found")

    existing_analysis = db.query(AIAnalysis).filter(AIAnalysis.email_id == id).first()
    if existing_analysis and not force_refresh:
        return {
            "status": "completed",
            "message": "Existing AI analysis retrieved from database",
            "steps": ["Retrieved verified structured analysis from database cache"],
            "analysis": AIAnalysisResponse.model_validate(existing_analysis)
        }

    # Retrieve active faculty preferences for personalized priority scoring scoped to user
    faculty_pref = preference_service.get_or_create_preferences(db, user_id=current_user.id)

    try:
        # Execute the unified coordinated multi-agent orchestration pipeline
        analysis_record = orchestrator.process_email(db, email, preferences=faculty_pref)
        pipeline_steps = getattr(orchestrator, "last_steps", ["Orchestration pipeline complete: structured intelligence validated"])

        return {
            "status": "completed",
            "message": "Email successfully analyzed via Multi-Agent AI Orchestrator",
            "steps": pipeline_steps,
            "analysis": AIAnalysisResponse.model_validate(analysis_record)
        }

    except Exception as exc:
        db.rollback()
        logger.error("Analysis pipeline failed for email #%d: %s", id, exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="AI analysis pipeline encountered an error while processing the email."
        )

@router.post("/analysis/batch")
def batch_analyze_emails(
    force_refresh: bool = Query(False, description="Re-analyze emails even if already analyzed"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute AI analysis across all unanalyzed (or all if force_refresh=True) emails for current user."""
    if force_refresh:
        emails_to_process = db.query(Email).filter(Email.user_id == current_user.id).all()
    else:
        emails_to_process = db.query(Email).outerjoin(AIAnalysis).filter(
            Email.user_id == current_user.id,
            AIAnalysis.id == None
        ).all()

    processed = 0
    for em in emails_to_process:
        try:
            trigger_email_analysis(id=em.id, force_refresh=force_refresh, current_user=current_user, db=db)
            processed += 1
        except Exception as err:
            logger.warning("Failed analyzing email #%d during batch: %s", em.id, err)

    return {
        "status": "success",
        "processed_count": processed,
        "message": f"Successfully processed {processed} emails."
    }

@router.post("/analysis/verify-assertion", response_model=AssertionVerificationResponse)
def verify_assertion(
    payload: AssertionVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify whether an extracted value/assertion is grounded in email text, detecting hallucinations."""
    raw_text = payload.raw_text
    if payload.email_id:
        email = db.query(Email).filter(Email.id == payload.email_id, Email.user_id == current_user.id).first()
        if not email:
            raise HTTPException(status_code=404, detail=f"Email with ID {payload.email_id} not found")
        raw_text = f"{email.subject}\n{email.body}"

    if not raw_text:
        raise HTTPException(status_code=400, detail="Either email_id or raw_text must be provided for verification")

    val_service = EvidenceValidationService()
    result = val_service.validate_assertion(
        field_name=payload.field_name,
        extracted_value=payload.extracted_value,
        raw_text=raw_text
    )

    return AssertionVerificationResponse(
        is_valid=result["is_valid"],
        validation_status=result["validation_status"],
        confidence=result["confidence"],
        grounded_sentence=result["grounded_sentence"],
        char_start=result["char_start"],
        char_end=result["char_end"],
        grounding_method=result["grounding_method"],
        audit_explanation=result["audit_explanation"]
    )
