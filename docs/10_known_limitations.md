# Known Limitations

This document articulates the current architectural, algorithmic, and operational boundaries of the **AI Email Summarizer Agent for Faculty**. Documenting these constraints ensures engineering transparency and establishes a rigorous baseline for future iterations.

---

## 1. Architectural & Deployment Boundaries

### 1.1 Single-Faculty Tenant Model
- **Current Behavior**: The system operates with a single global `FacultyPreference` record (`id=1`) representing the active user's personalization profile.
- **Limitation**: While ideal for personal faculty workstations or department chair desktops, it does not support concurrent multi-tenant role isolation (e.g., separating Dean preferences from Assistant Professor preferences on a shared enterprise server) without deploying isolated instances or implementing multi-user JWT authentication.

### 1.2 SQLite Storage Concurrency
- **Current Behavior**: The application utilizes SQLite 3 with WAL (Write-Ahead Logging) journaling.
- **Limitation**: SQLite operates with single-writer serialization. While capable of sustaining thousands of reads and dozens of sequential writes per second on a personal machine, it will experience database lock contention (`sqlite3.OperationalError: database is locked`) under heavy concurrent multi-user write traffic exceeding 50 concurrent transactions. Enterprise scaling requires pointing the SQLAlchemy URI to PostgreSQL or MySQL.

---

## 2. Information Extraction & AI Boundaries

### 2.1 Absence of Embedded OCR for Attachments
- **Current Behavior**: The ingestion pipeline parses email subject lines, text bodies, and MIME headers. Large payloads are guarded via the 5MB middleware limiter.
- **Limitation**: Academic offices occasionally circulate administrative orders as scanned image PDFs or graphic posters without machine-readable text layers. The current architecture does not include an optical character recognition (OCR) sub-agent (e.g., Tesseract or Google Cloud Vision), meaning image-only circulars cannot be summarized.

### 2.2 Heuristic Sensitivity in Offline Mode
- **Current Behavior**: In deterministic Mock AI mode, the orchestrator relies on rule-based keyword extraction, regex temporal matching, and lead-paragraph synthesis.
- **Limitation**: While guaranteed to be 100% stable and fast, heuristic rules cannot detect subtle rhetorical nuances, indirect politeness strategies (*"I was wondering if you might perhaps glance over this draft when time permits"*), or complex multi-hop temporal deductions (*"three days after the election results are ratified"*). High-order semantic nuances require activating `AI_MODE=llm`.

### 2.3 English-Language Specialization
- **Current Behavior**: The regex patterns, imperative verb lists, Bloom's taxonomy markers, and statutory titles are tailored to English-language university correspondence.
- **Limitation**: Emails written in other languages, or bilingual mixed-script communications, cannot be parsed accurately by the deterministic heuristic sub-services.

---

## 3. Provider & Synchronization Boundaries

### 3.1 Polling vs Real-Time Webhooks
- **Current Behavior**: The email ingestion provider abstraction operates on periodic polling or explicit manual synchronization requests (`POST /api/provider/sync`).
- **Limitation**: It does not currently implement real-time server push mechanisms (such as Google Cloud Pub/Sub webhooks or IMAP IDLE sockets). Consequently, new emails are not instantly pushed to the interface until the next poll cycle or manual refresh.

### 3.2 Read-Only Email Operation
- **Current Behavior**: The agent acts as an analytical companion, extracting intelligence, managing action items, and highlighting evidence.
- **Limitation**: It does not perform destructive write actions on the remote email server (e.g., it does not automatically draft replies, send emails, or permanently delete messages from Gmail), prioritizing data safety and avoiding unintended mail actions.
