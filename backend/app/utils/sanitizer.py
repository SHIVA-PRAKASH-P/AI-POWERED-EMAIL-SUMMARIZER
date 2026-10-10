"""Security Content Sanitization Utilities (Stage 16).

Provides defensive sanitization functions for:
1. Email body and subject text (stripping dangerous HTML/script tags, null bytes, prompt injection markers).
2. SQL LIKE parameter escaping (preventing wildcard-based search injection).
3. URL validation and scheme enforcement (blocking javascript: / data: URI vectors).
"""

import re
import html
from typing import Optional
from urllib.parse import urlparse

# Regular expression to identify dangerous or raw HTML tags
HTML_TAG_RE = re.compile(r'<(?:\/?[a-zA-Z][^>\n]*|!--[\s\S]*?--)>')

# Dangerous HTML tags that must always be completely expunged including their inner contents
DANGEROUS_BLOCK_TAGS_RE = re.compile(
    r'<(script|style|iframe|object|embed|applet|form|svg|meta|link)[^>]*>[\s\S]*?<\/\1>',
    re.IGNORECASE
)

# Unclosed dangerous tags
UNCLOSED_DANGEROUS_TAGS_RE = re.compile(
    r'<(script|style|iframe|object|embed|applet|form|svg|meta|link)[^>]*\/?>',
    re.IGNORECASE
)

# LLM delimiter injection sequences
PROMPT_INJECTION_TOKENS_RE = re.compile(
    r'(<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>|\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>)',
    re.IGNORECASE
)

ALLOWED_URL_SCHEMES = {"http", "https"}

def sanitize_email_text(text: Optional[str]) -> str:
    """Sanitize incoming email content, stripping HTML tags, script blocks, null bytes,
    and prompt injection delimiters while preserving legitimate academic text.
    
    Args:
        text: Raw text or HTML string.
        
    Returns:
        Clean, safe plain-text string.
    """
    if not text:
        return ""

    # 1. Remove null bytes and dangerous control characters (except newline, tab, carriage return)
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

    # 2. Expunge dangerous script/style/iframe blocks including inner contents
    cleaned = DANGEROUS_BLOCK_TAGS_RE.sub(' ', cleaned)
    cleaned = UNCLOSED_DANGEROUS_TAGS_RE.sub(' ', cleaned)

    # 3. Convert line-breaking HTML tags to newlines before stripping other tags
    cleaned = re.sub(r'<(br|p|div|tr|li)[^>]*\/?>', '\n', cleaned, flags=re.IGNORECASE)

    # 4. Strip remaining HTML tags
    cleaned = HTML_TAG_RE.sub('', cleaned)

    # 5. Decode safe HTML entities (&amp; -> &, &lt; -> <, etc.)
    cleaned = html.unescape(cleaned)

    # 6. Neutralize adversarial prompt injection control tokens
    cleaned = PROMPT_INJECTION_TOKENS_RE.sub('[FILTERED_TOKEN]', cleaned)

    # 7. Normalize linebreaks (limit consecutive newlines to maximum of 2)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    return cleaned.strip()

def sanitize_sql_like(term: Optional[str]) -> str:
    r"""Escape SQL LIKE wildcard characters to prevent wildcard search injection.
    
    Transforms:
        '\' -> '\\'
        '%' -> '\%'
        '_' -> '\_'
        
    Args:
        term: Raw search term from user query.
        
    Returns:
        Escaped search term safe for SQL ILIKE pattern matching with escape='\\'.
    """
    if not term:
        return ""
    
    # Escape backslash first, then % and _
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

def sanitize_url(url: Optional[str]) -> Optional[str]:
    """Validate and sanitize URL strings. Strictly permits http and https schemes.
    Blocks javascript:, data:, vbscript:, file:, and malformed URIs.
    
    Args:
        url: Candidate URL string.
        
    Returns:
        Sanitized URL string, or None if invalid/unsafe.
    """
    if not url:
        return None

    stripped = url.strip()
    # Reject javascript: and other pseudo-schemes directly
    if re.match(r'^(javascript|data|vbscript|file):', stripped, re.IGNORECASE):
        return None

    try:
        parsed = urlparse(stripped)
        if parsed.scheme.lower() in ALLOWED_URL_SCHEMES and parsed.netloc:
            return stripped
    except Exception:
        return None

    return None
