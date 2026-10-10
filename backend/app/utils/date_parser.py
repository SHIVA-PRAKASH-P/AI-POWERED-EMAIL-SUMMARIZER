import re
from datetime import datetime, date, timedelta, timezone
from typing import Optional, Dict, Any, Tuple, Union

MONTH_NAMES = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12
}

WEEKDAY_MAP = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6
}

# Historical / past non-deadline patterns
PAST_INFORMATIONAL_PATTERNS = [
    r'\b(?:was|were)\s+held\s+on\b',
    r'\bheld\s+on\b',
    r'\btook\s+place\s+on\b',
    r'\b(?:was|were)\s+conducted\s+on\b',
    r'\bconducted\s+on\b',
    r'\b(?:was|were)\s+issued\s+on\b',
    r'\bissued\s+on\b',
    r'\b(?:was|were)\s+published\s+on\b',
    r'\bpublished\s+on\b',
    r'\b(?:was|were)\s+released\s+on\b',
    r'\breleased\s+on\b',
    r'\b(?:was|were)\s+organized\s+on\b',
    r'\borganized\s+on\b',
    r'\bminutes\s+of\s+(?:the\s+)?meeting\b',
    r'\battended\s+on\b',
    r'\bcircular\s+dated\b'
]

# Actionable deadline cues
ACTIONABLE_DEADLINE_CUES = [
    r'\bsubmit\b', r'\bsubmission\b', r'\bdue\b', r'\bdeadline\b',
    r'\blast\s+date\b', r'\bcomplete\s+by\b', r'\bapply\b', r'\bapplication\b',
    r'\bapplications\s+close\b', r'\bregister\b', r'\bregistration\b',
    r'\bpayment\b', r'\bpay\s+by\b', r'\bresponse\s+required\b',
    r'\breply\s+by\b', r'\brespond\s+by\b', r'\bverify\b', r'\bverification\b',
    r'\bcompliance\b', r'\battend\s+by\b', r'\bextension\s+till\b',
    r'\bextension\s+until\b', r'\bprior\s+to\b', r'\bbefore\b',
    r'\bby\s+(?:tomorrow|today|day\s+after\s+tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|[0-9])\b',
    r'\bcloses\s+on\b', r'\bon\s+or\s+before\b', r'\bwithout\s+fail\b',
    r'\bmandatory\s+submission\b', r'\blast\s+chance\b'
]

def resolve_weekday(target_weekday: int, ref_date: datetime, is_next_week: bool = False) -> datetime:
    """Compute the upcoming date for a given weekday relative to ref_date."""
    current_weekday = ref_date.weekday()
    days_ahead = target_weekday - current_weekday
    if days_ahead <= 0:
        days_ahead += 7
    if is_next_week:
        days_ahead += 7
    return ref_date + timedelta(days=days_ahead)

def normalize_temporal_expression(
    text: str,
    reference_date: Optional[datetime] = None
) -> Tuple[Optional[str], Optional[str], float]:
    """Parse and normalize absolute and relative temporal expressions.
    
    Supported expressions:
    - 'tomorrow'
    - 'monday', 'before friday', 'by this wednesday'
    - 'next week', 'next monday'
    - 'september 10', 'sept 10th', 'october 5, 2026'
    - 'by end of day', 'by eod'
    - 'at 10 am', 'by 4 pm on september 12'
    
    Returns: (iso_date_string, matched_source_substring, confidence_score)
    Returns: (None, None, 0.0) when dates cannot be reliably determined.
    """
    ref = reference_date or datetime(2026, 9, 6, 9, 0, 0)
    text_clean = text.strip()
    text_lower = text_clean.lower()

    # 1. Reject ambiguous or non-deterministic temporal phrases (Never invent dates)
    ambiguous_patterns = [
        r'\bas soon as possible\b',
        r'\basap\b',
        r'\bat your earliest convenience\b',
        r'\bsome time next month\b',
        r'\bin the coming weeks\b',
        r'\blater this semester\b',
        r'\bshortly\b'
    ]
    for ambig in ambiguous_patterns:
        if re.search(ambig, text_lower) and not re.search(r'\b(before|by|until|on)\s+[A-Za-z0-9]', text_lower):
            return None, None, 0.0

    # 2. 'Day after tomorrow' (check before tomorrow to avoid substring conflict)
    day_after_match = re.search(r'\b(?:by|before|on|until)?\s*(day\s+after\s+tomorrow)\b', text_lower)
    if day_after_match:
        target = ref + timedelta(days=2)
        return target.strftime("%Y-%m-%d"), day_after_match.group(0).strip(), 0.98

    # 3. 'Tomorrow'
    tomorrow_match = re.search(r'\b(?:by|before|on|until)?\s*(tomorrow)\b', text_lower)
    if tomorrow_match:
        target = ref + timedelta(days=1)
        return target.strftime("%Y-%m-%d"), tomorrow_match.group(0).strip(), 0.98

    # 4. 'Today'
    today_match = re.search(r'\b(?:by|before|on|until)?\s*(today)\b', text_lower)
    if today_match:
        return ref.strftime("%Y-%m-%d"), today_match.group(0).strip(), 0.98

    # 5. 'Within N days' / 'within a day' / 'within a week'
    within_match = re.search(r'\bwithin\s+(\d+)\s+days?\b', text_lower)
    if within_match:
        num_days = int(within_match.group(1))
        target = ref + timedelta(days=num_days)
        return target.strftime("%Y-%m-%d"), within_match.group(0).strip(), 0.95

    within_week_match = re.search(r'\bwithin\s+a\s+week\b', text_lower)
    if within_week_match:
        target = ref + timedelta(days=7)
        return target.strftime("%Y-%m-%d"), within_week_match.group(0).strip(), 0.92

    # 6. 'End of day' / 'EOD' (resolves to reference date)
    eod_match = re.search(r'\b(?:by\s+)?(?:end\s+of\s+(?:the\s+)?day|eod)\b', text_lower)
    if eod_match:
        return ref.strftime("%Y-%m-%d"), eod_match.group(0).strip(), 0.95

    # 7. Explicit DD Month YYYY or DD Mon YYYY (e.g. "15 September 2026", "8 Sep 2026", "25 Sept 2026")
    MONTH_PATTERN = r'(?:january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sept|sep|october|oct|november|nov|december|dec)'
    dd_month_regex = rf'\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTH_PATTERN})(?:\s*,?\s*(\d{{4}}))?\b'
    dd_match = re.search(dd_month_regex, text_lower)
    if dd_match:
        groups = dd_match.groups()
        day = int(groups[0])
        m_str = groups[1].lower()
        year = int(groups[2]) if groups[2] else ref.year
        month = MONTH_NAMES.get(m_str, ref.month)
        try:
            target = datetime(year, month, day)
            return target.strftime("%Y-%m-%d"), dd_match.group(0).strip(), 0.99
        except ValueError:
            pass

    # 8. Explicit Month + Day (e.g. "September 10", "before Sept 15, 2026", "September 8, 2026")
    month_regex = rf'\b({MONTH_PATTERN})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{{4}}))?\b'
    
    # Priority for deadline context prefixes
    context_prefix_regex = r'(?:before|by|until|prior to|due date:?|deadline:?|on or before|closes on)\s+' + month_regex
    match = re.search(context_prefix_regex, text_lower)
    if not match:
        match = re.search(month_regex, text_lower)

    if match:
        groups = match.groups()
        m_str = groups[-3].lower()
        day = int(groups[-2])
        year = int(groups[-1]) if groups[-1] else ref.year
        month = MONTH_NAMES.get(m_str, ref.month)

        try:
            target = datetime(year, month, day)
            return target.strftime("%Y-%m-%d"), match.group(0).strip(), 0.99
        except ValueError:
            return None, None, 0.0

    # 9. Relative Weekday: "Next Monday", "Before Friday", "By Thursday"
    weekday_regex = r'\b(?:by|before|until|on|this)?\s*(next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)\b'
    w_match = re.search(weekday_regex, text_lower)
    if w_match:
        is_next = bool(w_match.group(1))
        day_str = w_match.group(2)
        target_wd = WEEKDAY_MAP.get(day_str)
        if target_wd is not None:
            target = resolve_weekday(target_wd, ref, is_next_week=is_next)
            return target.strftime("%Y-%m-%d"), w_match.group(0).strip(), 0.95

    # 10. 'Next week' (anchors to Monday of next week)
    next_week_match = re.search(r'\b(?:by|before|during|in)?\s*(next\s+week)\b', text_lower)
    if next_week_match:
        target = resolve_weekday(0, ref, is_next_week=True)
        return target.strftime("%Y-%m-%d"), next_week_match.group(0).strip(), 0.90

    # 11. ISO Format (e.g. 2026-09-10)
    iso_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    if iso_match:
        return iso_match.group(1), iso_match.group(1), 1.0

    # 12. DD.MM.YYYY or DD/MM/YYYY Format (e.g. "Extension till 08.09.2026", "by 15/09/2026")
    dmy_regex = r'\b(?:(?:extension\s+)?(?:till|until)|by|before|on|due:?|deadline:?)?\s*(\d{1,2})[./](\d{1,2})[./](\d{4})\b'
    dmy_match = re.search(dmy_regex, text_lower)
    if dmy_match:
        try:
            d = int(dmy_match.group(1))
            m = int(dmy_match.group(2))
            y = int(dmy_match.group(3))
            target = datetime(y, m, d)
            return target.strftime("%Y-%m-%d"), dmy_match.group(0).strip(), 0.98
        except ValueError:
            pass

    # If no reliable date can be determined, return None (never invent)
    return None, None, 0.0

def is_actionable_deadline_sentence(sentence: str) -> bool:
    """Evaluate whether a sentence containing a date represents an actionable deadline
    vs a historical/informational mention.
    """
    sent_lower = sentence.lower()
    has_past_cue = any(re.search(p, sent_lower) for p in PAST_INFORMATIONAL_PATTERNS)
    has_action_cue = any(re.search(a, sent_lower) for a in ACTIONABLE_DEADLINE_CUES)

    if has_past_cue and not has_action_cue:
        return False
    return True

def extract_actionable_deadline(
    text: str,
    reference_date: Optional[datetime] = None
) -> Tuple[Optional[str], Optional[str], float]:
    """Scan text sentence by sentence to extract an actionable deadline,
    distinguishing actionable deadlines from past/historical non-deadline dates.
    """
    if not text or not text.strip():
        return None, None, 0.0

    HEADER_REGEX = r'^(?:date|sent|from|to|subject|received|cc|bcc):\s+|^---+|^\*+$'
    raw_sentences = [s.strip() for s in re.split(r'[.\n;!?]+', text) if s.strip()]
    sentences = [s for s in raw_sentences if not re.match(HEADER_REGEX, s, re.IGNORECASE)]

    # First pass: Check sentences with both date and actionable context
    for sent in sentences:
        iso_date, raw_text, conf = normalize_temporal_expression(sent, reference_date=reference_date)
        if iso_date and is_actionable_deadline_sentence(sent):
            return iso_date, raw_text, conf

    # Second pass: Check if full text matched a date, and inspect the sentence containing raw_text
    iso_date, raw_text, conf = normalize_temporal_expression(text, reference_date=reference_date)
    if iso_date:
        for sent in sentences:
            if raw_text and raw_text.lower() in sent.lower():
                if is_actionable_deadline_sentence(sent):
                    return iso_date, raw_text, conf
                else:
                    return None, None, 0.0
        if is_actionable_deadline_sentence(text):
            return iso_date, raw_text, conf

    return None, None, 0.0

def parse_date_expression(text: str, anchor_date: Optional[datetime] = None) -> Optional[datetime]:
    """Convenience helper returning a datetime object or None from temporal text."""
    iso_str, _, _ = normalize_temporal_expression(text, reference_date=anchor_date)
    if iso_str:
        try:
            return datetime.strptime(iso_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None

def compute_temporal_status(
    target_date: Union[str, date, datetime],
    current_date: Optional[date] = None
) -> Tuple[str, str]:
    """Dynamically determine temporal status: UPCOMING, DUE_TODAY, or EXPIRED,
    along with human-readable relative label. Never hardcodes today's date.
    """
    if current_date is None:
        current_date = datetime.now(timezone.utc).date()
    elif isinstance(current_date, datetime):
        current_date = current_date.date()

    if isinstance(target_date, str):
        target_str = target_date.strip()
        match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', target_str)
        if match:
            target_str = match.group(1)
        try:
            t_date = datetime.strptime(target_str, "%Y-%m-%d").date()
        except ValueError:
            parsed_iso, _, _ = normalize_temporal_expression(target_str)
            if parsed_iso:
                t_date = datetime.strptime(parsed_iso, "%Y-%m-%d").date()
            else:
                return "UPCOMING", "Upcoming"
    elif isinstance(target_date, datetime):
        t_date = target_date.date()
    elif isinstance(target_date, date):
        t_date = target_date
    else:
        return "UPCOMING", "Upcoming"

    if t_date > current_date:
        delta = (t_date - current_date).days
        status = "UPCOMING"
        if delta == 1:
            rel = "Due tomorrow"
        else:
            rel = f"Due in {delta} days"
    elif t_date == current_date:
        status = "DUE_TODAY"
        rel = "Due today"
    else:
        delta = (current_date - t_date).days
        status = "EXPIRED"
        if delta == 1:
            rel = "Expired 1 day ago"
        elif delta > 1:
            rel = f"Expired {delta} days ago"
        else:
            rel = "Expired today"

    return status, rel

def normalize_time_expression(text: str) -> Optional[str]:
    """Parse time of day into 24-hour HH:MM format."""
    time_match = re.search(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', text, re.IGNORECASE)
    if time_match:
        h = int(time_match.group(1))
        m = int(time_match.group(2)) if time_match.group(2) else 0
        meridiem = time_match.group(3).lower()
        if meridiem == "pm" and h < 12:
            h += 12
        elif meridiem == "am" and h == 12:
            h = 0
        return f"{h:02d}:{m:02d}"

    # 24-hour match: 14:30
    h24_match = re.search(r'\b([01]?\d|2[0-3]):([0-5]\d)\b', text)
    if h24_match:
        return f"{int(h24_match.group(1)):02d}:{int(h24_match.group(2)):02d}"

    return None
