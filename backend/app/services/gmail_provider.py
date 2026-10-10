"""Optional Gmail Ingestion Provider for Faculty Email Summarizer.

Integrates with the Google Gmail REST API via OAuth 2.0.
Does not make credentials mandatory; defaults to unauthenticated if credentials are not provided.
"""

import base64
import os
import re
import email.utils
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging

from backend.app.config import settings
from backend.app.services.base_email_provider import BaseEmailProvider
from backend.app.utils.sanitizer import sanitize_email_text

logger = logging.getLogger(__name__)

class GmailProvider(BaseEmailProvider):
    """Modular Gmail API Provider.
    
    Supports OAuth2 credentials via environment variables or service account/token paths.
    Gracefully disables itself when credentials are not configured.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        gmail_service: Optional[Any] = None
    ):
        self.client_id = client_id if client_id is not None else settings.resolved_google_client_id
        self.client_secret = client_secret if client_secret is not None else settings.resolved_google_client_secret
        self.refresh_token = refresh_token if refresh_token is not None else settings.GMAIL_REFRESH_TOKEN
        self.credentials_path = credentials_path if credentials_path is not None else settings.GMAIL_CREDENTIALS_PATH
        self.token_path = token_path if token_path is not None else settings.GMAIL_TOKEN_PATH
        self._service = gmail_service

    @property
    def provider_name(self) -> str:
        return "gmail"

    @property
    def is_configured(self) -> bool:
        """Check if any credentials or paths have been supplied."""
        has_direct_oauth = bool(self.client_id and self.client_secret and self.refresh_token)
        has_file_token = bool(self.token_path and os.path.exists(self.token_path))
        has_file_creds = bool(self.credentials_path and os.path.exists(self.credentials_path))
        return has_direct_oauth or has_file_token or has_file_creds or (self._service is not None)

    def is_authenticated(self) -> bool:
        """Check if Gmail API is authenticated and ready to service queries."""
        if self._service is not None:
            return True
        if not self.is_configured:
            return False
        
        # If credentials parameters exist, attempt verification
        try:
            service = self._get_service()
            return service is not None
        except Exception as e:
            logger.warning(f"Gmail authentication verification failed: {e}")
            return False

    def _get_service(self) -> Any:
        """Internal helper to initialize or return Google API Resource client."""
        if self._service is not None:
            return self._service
        
        # Try importing Google API client libraries dynamically
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError:
            logger.warning("google-api-python-client or google-auth is not installed.")
            return None

        creds = None
        if self.token_path and os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, ['https://www.googleapis.com/auth/gmail.readonly'])
        elif self.client_id and self.client_secret and self.refresh_token:
            creds = Credentials(
                None,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=['https://www.googleapis.com/auth/gmail.readonly']
            )

        if creds and creds.valid:
            self._service = build('gmail', 'v1', credentials=creds)
            return self._service
        elif creds and creds.expired and creds.refresh_token:
            try:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                self._service = build('gmail', 'v1', credentials=creds)
                return self._service
            except Exception as exc:
                logger.error(f"Failed to refresh Gmail OAuth token: {exc}")
                return None

        return None

    def get_authenticated_user_email(self) -> Optional[str]:
        """Fetch the authenticated user's email address from the Gmail profile."""
        if not self.is_authenticated():
            return None
        service = self._get_service()
        if not service:
            return None
        try:
            profile = service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress')
        except Exception as e:
            logger.warning(f"Failed retrieving user profile from Gmail API: {e}")
            return None

    def get_messages(
        self,
        limit: int = 60,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch messages from Gmail API.
        
        Strict Stage 19C constraints:
        - Controlled batch: capped strictly to a maximum of 60 messages.
        - Per-message error isolation: an error fetching one message does not fail the batch.
        - Read-only scope: gmail.readonly only.
        
        Raises PermissionError if Gmail is not authenticated.
        """
        if not self.is_authenticated():
            raise PermissionError(
                "Gmail provider is not authenticated. Please configure GMAIL_CLIENT_ID, "
                "GMAIL_CLIENT_SECRET, and GMAIL_REFRESH_TOKEN or use the default 'mock' provider."
            )

        service = self._get_service()
        if not service:
            return []

        # Enforce hard ceiling of 60 messages (Stage 19C requirement)
        max_fetch = min(max(1, limit), 60)

        try:
            q = query or ""
            res = service.users().messages().list(userId='me', maxResults=max_fetch, q=q).execute()
            messages_meta = res.get('messages', [])[:max_fetch]
            
            parsed_messages = []
            for item in messages_meta:
                msg_id = item.get('id')
                if not msg_id:
                    continue
                try:
                    raw_msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
                    parsed = self._parse_gmail_payload(raw_msg)
                    if parsed:
                        parsed_messages.append(parsed)
                except Exception as msg_err:
                    logger.warning(f"Error retrieving individual Gmail message {msg_id}: {msg_err}")
                    continue
            
            return parsed_messages
        except Exception as e:
            logger.error(f"Error fetching Gmail messages: {e}")
            raise

    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific message from Gmail API by ID."""
        if not self.is_authenticated():
            raise PermissionError(
                "Gmail provider is not authenticated. Cannot retrieve message."
            )

        service = self._get_service()
        if not service:
            return None

        try:
            raw_msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
            return self._parse_gmail_payload(raw_msg)
        except Exception as e:
            logger.error(f"Error retrieving Gmail message {message_id}: {e}")
            return None

    def _parse_gmail_payload(self, raw_message: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Gmail API raw message payload into standard format."""
        msg_id = raw_message.get("id", "")
        payload = raw_message.get("payload", {})
        headers_list = payload.get("headers", [])
        
        headers = {}
        for h in headers_list:
            headers[h.get("name", "").lower()] = h.get("value", "")

        sender = headers.get("from", "unknown@gmail.com")
        recipient = headers.get("to", "faculty@university.edu")
        subject = headers.get("subject", "(No Subject)")
        date_str = headers.get("date", "")

        received_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if date_str:
            try:
                parsed_tuple = email.utils.parsedate_to_datetime(date_str)
                if parsed_tuple:
                    # Strip tzinfo for SQLite naive datetime compatibility
                    received_at = parsed_tuple.replace(tzinfo=None)
            except Exception:
                internal_date = raw_message.get("internalDate")
                if internal_date:
                    try:
                        received_at = datetime.fromtimestamp(int(internal_date) / 1000.0, timezone.utc).replace(tzinfo=None)
                    except Exception:
                        pass

        body = self._extract_body(payload)
        if not body or not body.strip():
            # Fallback to snippet if body payload was empty
            body = raw_message.get("snippet", "")

        label_ids = raw_message.get("labelIds", [])
        is_read = "UNREAD" not in label_ids

        return {
            "id": msg_id,
            "sender": sender,
            "recipient": recipient,
            "subject": sanitize_email_text(subject),
            "body": sanitize_email_text(body),
            "received_at": received_at,
            "is_read": is_read
        }

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Recursively decode text from Gmail message parts."""
        body_data = payload.get("body", {}).get("data")
        if body_data:
            try:
                decoded_bytes = base64.urlsafe_b64decode(body_data.encode('ASCII'))
                return decoded_bytes.decode('utf-8', errors='replace')
            except Exception:
                pass

        parts = payload.get("parts", [])
        for part in parts:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/plain":
                part_data = part.get("body", {}).get("data")
                if part_data:
                    try:
                        decoded_bytes = base64.urlsafe_b64decode(part_data.encode('ASCII'))
                        return decoded_bytes.decode('utf-8', errors='replace')
                    except Exception:
                        continue
            elif mime_type == "text/html":
                # Fallback to HTML if plain text isn't available
                part_data = part.get("body", {}).get("data")
                if part_data:
                    try:
                        decoded_bytes = base64.urlsafe_b64decode(part_data.encode('ASCII'))
                        html_text = decoded_bytes.decode('utf-8', errors='replace')
                        clean_text = re.sub(r'<[^>]+>', ' ', html_text)
                        clean_text = ' '.join(clean_text.split())
                        if clean_text:
                            return clean_text
                    except Exception:
                        continue
            elif mime_type.startswith("multipart/"):
                sub_body = self._extract_body(part)
                if sub_body:
                    return sub_body

        return ""
