# System Architecture Documentation

This document describes the high-level and component-level architecture of the **AI Email Summarizer Agent for Faculty**. It provides a structural decomposition using C4-style architectural abstractions, detailing the interaction models, security boundaries, and persistence mechanisms.

---

## 1. Architectural Principles

1. **Explainability by Design**: No claim, summary sentence, or priority assignment is presented to the user without traceable, inspectable reasoning and verifiable source-text citations.
2. **Offline-First Resilience**: The platform operates with full fidelity in air-gapped, firewalled, or unconfigured environments via a deterministic, dependency-free heuristic engine.
3. **Defense-in-Depth Security**: Email text is inherently untrusted. Strict boundary sanitization, payload size constraints, and SQL escaping protect the processing pipeline.
4. **Decoupled Multi-Agent Orchestration**: Specialized sub-services handle distinct semantic tasks (temporal resolution, action extraction, meeting parsing, priority scoring) rather than relying on an unconstrained single-prompt model.
5. **Auditable Relational Integrity**: All extracted intelligence is persisted in structured relational tables with strict foreign-key cascades, supporting atomic rollback and historical auditing.

---

## 2. C4 Context Diagram (Level 1)

The following diagram illustrates how the system interacts with external entities and users:

```mermaid
graph TD
    User["Faculty Member / Academic Administrator"]
    System["AI Email Summarizer Agent"]
    Gmail["Optional Google Gmail API (OAuth2)"]
    LLM["Optional External LLM (Gemini / OpenAI)"]
    Disk["Local Encrypted SQLite Storage"]

    User -->|Views Triaged Inbox, Adjusts Weights, Completes Actions| System
    System -->|Fetches Real Correspondence (Optional)| Gmail
    System -->|Invokes Structured Inference (Optional)| LLM
    System -->|Persists Structured Entities, Evidences, Insights| Disk
```

---

## 3. C4 Container Diagram (Level 2)

The system consists of three primary execution containers:

```mermaid
graph LR
    subgraph Browser["Client Container (Web Browser)"]
        SPA["React 18 Single Page Application<br/>(TypeScript, Tailwind CSS, Vite)"]
    end

    subgraph Host["Application Host (Local Server / Workstation)"]
        API["FastAPI REST Application Server<br/>(Uvicorn ASGI, Python 3.11+)"]
        Engine["Multi-Agent AI Orchestrator<br/>(Pure-Python Engine)"]
        DB[("SQLite Relational Database<br/>(SQLAlchemy 2.0 ORM)")]
    end

    subgraph External["External Cloud APIs (Optional)"]
        CloudLLM["Cloud LLM Providers<br/>(OpenAI GPT-4o-mini / Google Gemini 1.5)"]
        GoogleAPI["Google Workspace Gmail API<br/>(OAuth 2.0 / REST)"]
    end

    SPA -->|JSON over HTTPS/WSS<br/>REST APIs| API
    API -->|Synchronous Processing Pipeline| Engine
    API -->|ORM Transactions (Read/Write)| DB
    Engine -.->|Structured JSON Prompts (if enabled)| CloudLLM
    API -.->|Message Synchronization (if enabled)| GoogleAPI
```

---

## 4. Component Architecture (Level 3)

### 4.1 Backend Component Breakdown

The backend application structure (`backend/app/`) is partitioned into decoupled layers:

1. **Security & Middleware Layer**:
   - `limit_payload_size`: Intercepts inbound HTTP requests and rejects bodies exceeding 5MB (HTTP 413) to prevent denial-of-service via large attachments.
   - `add_security_headers`: Injects OWASP-compliant security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy`, `Referrer-Policy`).
   - `sanitizer.py`: Sanitizes email text, escapes HTML/script tags, and cleans SQL wildcard characters.
   - `security_logging.py`: Configures regex logging filters (`SensitiveDataFilter`) to scrub API keys and bearer tokens from application logs.

2. **API Layer (`backend/app/api/`)**:
   - `routes_emails.py`: Filtering, search, pagination, and retrieval of email records.
   - `routes_dashboard.py`: Statistical aggregations, urgency counters, and distribution matrices.
   - `routes_actions.py`: Action item lifecycle management and status toggling (`PENDING` / `COMPLETED`).
   - `routes_analysis.py`: On-demand individual and batch AI re-orchestration.
   - `routes_provider.py`: Email ingestion abstraction (Mock provider vs Gmail provider).
   - `routes_cross_intelligence.py`: Multi-email thematic clustering, thread detection, and timeline generation.
   - `routes_preferences.py`: Faculty priority weight customization and role overrides.
   - `routes_evaluation.py`: Automated benchmark evaluation and empirical telemetry reporting.

3. **AI Orchestration Layer (`backend/app/ai/`)**:
   - `orchestrator.py`: Master pipeline coordinator executing task detection, dispatch, and result aggregation.
   - `classification_service.py`: Multi-class academic domain classifier (10 categories).
   - `temporal_service.py`: Reference-anchored temporal extraction and ISO normalization.
   - `action_service.py`: Imperative action item detector with leading conjunct handling.
   - `meeting_service.py`: Joint meeting slot extractor (date, time, venue, prerequisites).
   - `priority_engine.py`: 4-factor context-aware priority engine with consequence scoring.
   - `summarization_service.py`: Executive summarizer synthesizing key imperatives.
   - `evidence_service.py`: Bidirectional character span validator verifying claims against raw text.
   - `llm_service.py`: Unified abstraction layer for cloud LLMs (Gemini / OpenAI) with fallback to deterministic heuristics.

4. **Persistence Layer (`backend/app/database/` & `models/`)**:
   - `session.py`: Database engine configuration, session pooling, and table creation.
   - `seed_data.py`: Idempotent seed initialization populating diverse synthetic academic emails.
   - Relational models: `Email`, `AIAnalysis`, `ActionItem`, `Meeting`, `Evidence`, `Entity`, `FacultyPreference`, `CrossEmailCluster`, `CrossEmailInsight`.

---

## 5. Layered Architecture & Data Flow

```
+-----------------------------------------------------------------------------------+
| 1. PRESENTATION LAYER (React 18 + TypeScript)                                     |
|    - Two-Panel Intelligence View (Inbox List & Rich Detail Panel)                 |
|    - Interactive Evidence Highlighting (Hover link between claims and raw spans)  |
|    - Personalization Configuration UI & Real-Time Priority Recalculation          |
+-----------------------------------------+-----------------------------------------+
                                          | JSON / REST
                                          v
+-----------------------------------------------------------------------------------+
| 2. API & SECURITY GATEWAY (FastAPI + Pydantic v2)                                 |
|    - HTTP 413 Payload Limiter (5MB)  - OWASP Security Headers                     |
|    - Pydantic Schema Validation       - Sensitive Data Redaction Log Filter        |
+-----------------------------------------+-----------------------------------------+
                                          | Validated Models
                                          v
+-----------------------------------------------------------------------------------+
| 3. MULTI-AGENT AI ORCHESTRATION PIPELINE                                          |
|    - Context Analysis       -> Academic Categorization                            |
|    - Temporal Normalization -> Action-Deadline Semantic Binding                   |
|    - Joint Meeting Parsing  -> Multi-Factor Priority Scoring                      |
|    - Executive Summary      -> Bidirectional Span Evidence Validation             |
+-----------------------------------------+-----------------------------------------+
                                          | Structured Domain Objects
                                          v
+-----------------------------------------------------------------------------------+
| 4. RELATIONAL PERSISTENCE (SQLAlchemy 2.0 + SQLite)                               |
|    - Foreign-Key Cascading Deletes    - Index-Optimized Triage Queries            |
|    - Idempotent Seeding Transactions  - WAL Concurrency Journaling                |
+-----------------------------------------------------------------------------------+
```

---

## 6. Offline-First Isolation Boundary

A major architectural vulnerability of existing enterprise email AI systems is complete operational paralysis when external cloud APIs fail, rate limits are hit, or internet connectivity is disrupted.

This architecture introduces a **Deterministic Offline Boundary**:
1. When `AI_MODE=mock` (or when external LLM credentials fail), the orchestrator immediately switches to pure-Python heuristic algorithms without interrupting user operations.
2. The heuristic sub-services utilize regex parsing, keyword weight dictionaries, and longest common subsequence algorithms that execute locally in sub-millisecond timeframes.
3. The offline mode maintains 100% schema parity with the LLM mode; the frontend dashboard and database schema are completely oblivious to which engine generated the structured output.

---

## 7. Security Architecture

- **Untrusted Input Sanitization**: All inbound text fields (`subject`, `body`, `sender`) undergo script tag stripping and HTML entity replacement before entering the database or AI pipeline.
- **SQL Injection Prevention**: All queries utilize SQLAlchemy ORM parameterized statements. Wildcard characters (`%`, `_`) in user search inputs are sanitized using `sanitize_sql_like`.
- **Credential Protection**: LLM API keys are stored in server-side environment variables (`.env`). The `/api/llm-status` endpoint exposes only masked representations (e.g., `sk-proj...X89a`), and custom logging filters redact key patterns from standard error streams.
- **Payload Denial-of-Service Defense**: A global middleware inspects the `Content-Length` header on all inbound requests, immediately rejecting payloads exceeding `5,242,880` bytes.
