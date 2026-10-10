# Technical Workflow & Email Lifecycle Documentation

This document describes the end-to-end operational workflow of an email within the **AI Email Summarizer Agent for Faculty**, tracing its path from ingestion to interactive presentation and user feedback.

---

## 1. End-to-End Email Processing Lifecycle

```
[1. INGESTION]
Raw MIME / JSON Payload (Mock Provider or Gmail API)
       |
       v
[2. SANITIZATION & SECURITY]
Length Limiting (5MB) -> Script Stripping -> SQL Sanitization
       |
       v
[3. MULTI-AGENT AI ORCHESTRATION]
Context -> Classification -> Temporal Normalization -> Action/Meeting Parsing
       -> Action-Deadline Binding -> Priority Scoring -> Evidence Grounding
       |
       v
[4. ATOMIC RELATIONAL PERSISTENCE]
Commit to SQLite (Email + Analysis + ActionItems + Meeting + Evidences)
       |
       v
[5. CLIENT-SIDE SYNCHRONIZATION]
React Inbox Fetch -> Cache Invalidation -> Priority Sorting
       |
       v
[6. INTERACTIVE TRIAGE]
Two-Panel View -> Verifiable Evidence Hover -> Action Item Checkoff
       |
       v
[7. PERSONALIZATION FEEDBACK LOOP]
Faculty updates priority weights -> Re-evaluates urgency across inbox
```

---

## 2. Stage-by-Stage Workflow Breakdown

### Stage 1: Ingestion
- **Trigger**: System startup seeding, manual provider sync (`POST /api/provider/sync`), or direct API submission (`POST /api/emails`).
- **Provider Abstraction**:
  - `MockEmailProvider`: Ingests rich synthetic emails mimicking real university administrative correspondence.
  - `GmailEmailProvider`: If configured with OAuth2 tokens, polls the user's Gmail inbox for unread university messages (`is:unread`).

### Stage 2: Security & Preprocessing
- **Payload Gatekeeper**: Enforces a strict 5MB limit on incoming message payloads.
- **Sanitization**: Strips potential cross-site scripting vectors (`<script>`, `<iframe>`, `javascript:`) from the body and subject.
- **Normalization**: Preserves paragraph breaks and whitespace structure while ensuring ASCII/UTF-8 consistency.

### Stage 3: Multi-Agent AI Orchestration
1. **Context & Domain Routing**: Detects institutional role markers and assigns one of 10 academic domains (*e.g., Examination, Accreditation*).
2. **Temporal Resolution**: Binds relative phrases (*"tomorrow by 5 PM"*) to the email's arrival timestamp $T_0$ to output normalized calendar dates (`YYYY-MM-DD`).
3. **Action & Meeting Extraction**: Isolates actionable tasks and meeting slots (date, time, room, prerequisites).
4. **Action-Deadline Linking**: Binds tasks to specific dates using the `DUE_ON` semantic relationship.
5. **Context-Aware Priority Engine**: Evaluates authority, deadline proximity, and consequence markers against the faculty member's active weighting profile.
6. **Bidirectional Grounding**: Validates all generated claims against the raw email, locating exact character boundaries.

### Stage 4: Atomic Persistence
- All extracted intelligence is committed to the local SQLite database inside an atomic transaction:
  ```python
  db.add(email_record)
  db.flush()
  db.add(analysis_record)
  db.add_all(action_items)
  db.add(meeting_record)
  db.add_all(evidence_spans)
  db.commit()
  ```
- If an unexpected error occurs at any point during orchestration, `db.rollback()` executes, guaranteeing the database remains in a consistent state.

### Stage 5: Client-Side Presentation
- The React frontend fetches the updated inbox state via `GET /api/emails`.
- Emails are categorized and prioritized in the left sidebar list.
- Selecting an email loads its comprehensive analysis in the right-hand detail panel.

### Stage 6: Interactive Faculty Triage
- **Evidence Verification**: The faculty member can inspect the executive summary. Hovering over a claim or clicking a verified badge immediately highlights the exact corresponding sentence in the original email text.
- **Task Management**: Faculty can mark extracted action items as `COMPLETED` (`PATCH /api/actions/{id}`), updating the global dashboard counter.

### Stage 7: Personalization Feedback Loop
- If the faculty member changes their priority tuning mode (e.g., switching from `BALANCED` to `DEADLINE_HEAVY`), the priority engine immediately recalibrates urgency scores for all messages based on the new weights:
  $$w_{\text{deadline}} = 0.50, \quad w_{\text{authority}} = 0.20, \quad w_{\text{consequence}} = 0.20, \quad w_{\text{bias}} = 0.10$$

---

## 3. State Machines

### 3.1 Email Lifecycle State Machine
```
[RECEIVED] --> [ANALYZING] --> [ANALYZED / UNREAD] --> [READ] --> [ARCHIVED / DELETED]
                    |
                    +--> [FALLBACK TO HEURISTIC] (on LLM timeout)
```

### 3.2 Action Item State Machine
```
[DETECTED & BOUND] --> [PENDING] --> [COMPLETED]
                           ^              |
                           +--------------+ (User toggle)
```
