"""Security Logging & Secret Redaction (Stage 16).

Provides a specialized logging filter that intercepts log records and redacts
exposed secrets, bearer tokens, API keys, and credential strings before they reach
console or file sinks.
"""

import logging
import re
from typing import List, Pattern

# Regular expressions for detecting and redacting sensitive credentials
SECRET_PATTERNS: List[Pattern] = [
    # OpenAI API Keys
    re.compile(r'(sk-[a-zA-Z0-9T3BlbkFJ]{20,})', re.IGNORECASE),
    # Google Gemini / Cloud API Keys
    re.compile(r'(AIza[0-9A-Za-z\-_]{35})'),
    # Bearer Authorization Tokens
    re.compile(r'(Bearer\s+)([a-zA-Z0-9\-_.~+/]+=*)', re.IGNORECASE),
    # OAuth Client Secrets, Refresh Tokens, and PKCE verifiers in query or json strings
    re.compile(r'((?:client_secret|refresh_token|api_key|password|token|code_verifier|verifier)\s*[:=]\s*["\']?)([^"\'&\s]{6,})(["\']?)', re.IGNORECASE),
    # Basic Authorization headers
    re.compile(r'(Basic\s+)([a-zA-Z0-9+/=]{10,})', re.IGNORECASE),
]

class SensitiveDataFilter(logging.Filter):
    """Logging filter that scrubs sensitive credential tokens from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.redact_text(record.msg)
        if record.args:
            # Handle formatted logging args tuple/dict safely
            if isinstance(record.args, dict):
                record.args = {k: (self.redact_text(v) if isinstance(v, str) else v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.redact_text(a) if isinstance(a, str) else a for a in record.args)
        return True

    @classmethod
    def redact_text(cls, text: str) -> str:
        """Apply redaction regex patterns to mask sensitive tokens."""
        if not text or not isinstance(text, str):
            return text

        redacted = text
        # Redact OpenAI Keys
        redacted = SECRET_PATTERNS[0].sub(r'sk-***[REDACTED_KEY]***', redacted)
        # Redact Gemini Keys
        redacted = SECRET_PATTERNS[1].sub(r'AIza***[REDACTED_KEY]***', redacted)
        # Redact Bearer Tokens
        redacted = SECRET_PATTERNS[2].sub(r'\1***[REDACTED_TOKEN]***', redacted)
        # Redact generic credential key-value pairs
        redacted = SECRET_PATTERNS[3].sub(r'\1***[REDACTED]***\3', redacted)
        # Redact Basic Auth
        redacted = SECRET_PATTERNS[4].sub(r'\1***[REDACTED_AUTH]***', redacted)

        return redacted

def setup_security_logging():
    """Attach SensitiveDataFilter to root logger and active uvicorn/fastapi loggers."""
    security_filter = SensitiveDataFilter()
    root_logger = logging.getLogger()
    
    # Avoid attaching duplicate filters
    if not any(isinstance(f, SensitiveDataFilter) for f in root_logger.filters):
        root_logger.addFilter(security_filter)

    # Attach to handlers
    for handler in root_logger.handlers:
        if not any(isinstance(f, SensitiveDataFilter) for f in handler.filters):
            handler.addFilter(security_filter)

    # Attach to key framework loggers
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi", "ai.llm_service"]:
        log = logging.getLogger(logger_name)
        if not any(isinstance(f, SensitiveDataFilter) for f in log.filters):
            log.addFilter(security_filter)
