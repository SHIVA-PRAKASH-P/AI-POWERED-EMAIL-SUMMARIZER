"""Email Provider Manager & Ingestion Coordinator.

Orchestrates modular email providers (Mock, Gmail), manages fallback policies,
and idempotently synchronizes incoming emails into the SQLite database with AI processing.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.email import Email
from backend.app.services.base_email_provider import BaseEmailProvider
from backend.app.services.mock_email_provider import MockEmailProvider
from backend.app.services.gmail_provider import GmailProvider
from backend.app.ai.orchestrator import AIOrchestrator
from backend.app.utils.sanitizer import sanitize_email_text

logger = logging.getLogger(__name__)

class EmailProviderManager:
    """Manages active email ingestion provider and synchronization pipeline."""

    def __init__(self, default_provider_name: Optional[str] = None):
        self.default_provider_name = (default_provider_name or settings.EMAIL_PROVIDER).lower()

    def get_provider(self, provider_type: Optional[str] = None, user_id: Optional[int] = None) -> BaseEmailProvider:
        """Resolve and instantiate email provider with graceful fallback to Mock.
        
        Security Guarantee (Stage 19B/Multi-User):
        - User 1 operates exclusively with MockEmailProvider.
        - Connected Gmail users (User 2, 3, etc.) resolve credentials via oauth_service.get_token_path(user_id).
        - Unauthenticated callers or User 1 fallback to MockEmailProvider.
        """
        target = (provider_type or self.default_provider_name).lower()

        if target == "gmail":
            if not user_id or user_id == 1:
                return MockEmailProvider()
            from backend.app.services.oauth_service import oauth_service
            token_path = oauth_service.get_token_path(user_id=user_id)
            gmail_provider = GmailProvider(token_path=token_path)
            if gmail_provider.is_authenticated():
                return gmail_provider
            
            logger.warning(
                "Gmail provider requested but not authenticated (missing or invalid credentials). "
                "Falling back to MockEmailProvider."
            )
            return MockEmailProvider()

        # Default to MockEmailProvider
        return MockEmailProvider()

    def get_status(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Telemetry status of configured and active email providers."""
        configured = settings.EMAIL_PROVIDER.lower()
        token_path = ""
        if user_id and user_id != 1:
            from backend.app.services.oauth_service import oauth_service
            token_path = oauth_service.get_token_path(user_id=user_id)
        gmail = GmailProvider(token_path=token_path)
        gmail_configured = gmail.is_configured
        gmail_auth = gmail.is_authenticated()

        active = self.get_provider(user_id=user_id)
        fallback_active = (configured == "gmail" and active.provider_name == "mock")

        return {
            "configured_provider": configured,
            "active_provider": active.provider_name,
            "is_authenticated": active.is_authenticated(),
            "available_providers": ["mock", "gmail"],
            "fallback_active": fallback_active,
            "gmail_configured": gmail_configured,
            "gmail_authenticated": gmail_auth
        }

    def sync_emails(
        self,
        db: Session,
        limit: int = 15,
        provider_type: Optional[str] = None,
        run_ai_pipeline: bool = True,
        user_id: int = 1
    ) -> Dict[str, Any]:
        """Fetch emails from provider and synchronize them into the database idempotently.
        
        Args:
            db: Active SQLAlchemy database session.
            limit: Maximum count of emails to retrieve from provider.
            provider_type: Optional provider selector ('mock' or 'gmail').
            run_ai_pipeline: Whether to trigger multi-agent analysis on newly imported emails.
            user_id: Target user ID to associate newly ingested emails with.
        
        Returns:
            Dict containing synchronization statistics.
        """
        provider = self.get_provider(provider_type=provider_type, user_id=user_id)
        
        # Hard cap of 60 messages for Gmail / User >= 2 (Stage 19C requirement)
        effective_limit = min(limit, 60) if (provider.provider_name == "gmail" or (user_id and user_id != 1)) else limit
        messages = provider.get_messages(limit=effective_limit)

        imported_count = 0
        skipped_count = 0
        failed_count = 0
        orchestrator = AIOrchestrator() if run_ai_pipeline else None

        for msg in messages:
            provider_msg_id = str(msg["id"]) if msg.get("id") is not None else None
            clean_subject = sanitize_email_text(msg.get("subject", "(No Subject)"))
            clean_body = sanitize_email_text(msg.get("body", ""))

            # Stage 19C Deduplication:
            # 1. Match on provider_message_id for exact provider message deduplication
            existing = None
            if provider_msg_id:
                existing = (
                    db.query(Email)
                    .filter(
                        Email.user_id == user_id,
                        Email.provider_message_id == provider_msg_id
                    )
                    .first()
                )
            
            # 2. Fallback to sender, subject, and received_at
            if not existing:
                query = db.query(Email).filter(
                    Email.user_id == user_id,
                    Email.subject == clean_subject,
                    Email.sender == msg.get("sender")
                )
                if msg.get("received_at"):
                    query = query.filter(Email.received_at == msg.get("received_at"))
                existing = query.first()

            if existing:
                # If email was previously imported without AI analysis, backfill analysis now
                if run_ai_pipeline and orchestrator and existing.analysis is None:
                    try:
                        orchestrator.process_email(db, existing)
                        logger.info(f"Backfilled missing AI analysis for email #{existing.id}")
                    except Exception as e:
                        logger.error(f"Failed to run AI orchestration on existing email #{existing.id}: {e}")
                skipped_count += 1
                continue

            # Create new Email record with defensively sanitized text and provider_message_id
            try:
                new_email = Email(
                    user_id=user_id,
                    provider_message_id=provider_msg_id,
                    sender=msg.get("sender", "unknown@gmail.com"),
                    recipient=msg.get("recipient", "faculty@university.edu"),
                    subject=clean_subject,
                    body=clean_body,
                    received_at=msg.get("received_at"),
                    is_read=msg.get("is_read", False)
                )
                db.add(new_email)
                db.commit()
                db.refresh(new_email)
            except Exception as db_err:
                db.rollback()
                logger.error(f"Failed to persist email record: {db_err}")
                failed_count += 1
                continue

            if orchestrator:
                try:
                    orchestrator.process_email(db, new_email)
                except Exception as e:
                    logger.error(f"Failed to run AI orchestration on synced email #{new_email.id}: {e}")

            imported_count += 1

        return {
            "status": "success",
            "provider": provider.provider_name,
            "user_id": user_id,
            "fetched": len(messages),
            "imported": imported_count,
            "skipped": skipped_count,
            "skipped_duplicates": skipped_count,
            "failed": failed_count,
            "fallback_active": (settings.EMAIL_PROVIDER.lower() == "gmail" and provider.provider_name == "mock")
        }

# Global manager instance
email_provider_manager = EmailProviderManager()
