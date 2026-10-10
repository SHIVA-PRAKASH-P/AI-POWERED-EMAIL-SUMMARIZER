# AI-Agent Architecture Documentation

This document provides a comprehensive technical specification of the **AI Agent Orchestration Pipeline** (`AIOrchestrator`) and its constituent specialized sub-services.

---

## 1. Orchestration Philosophy

Rather than routing raw emails into an unconstrained, monolithic single-prompt Large Language Model (LLM)—which suffers from hallucination, inconsistent formatting, and high token costs—the system utilizes a **Modular Multi-Agent Pipeline**. 

Each sub-agent performs a narrow, bounded extraction task, validating its output against strict Pydantic schemas and grounding its findings in the source text.

```
Raw Email (Sender, Subject, Body, Received Date)
                       |
                       v
         +-----------------------------+
         |     1. Context Analysis     |
         +--------------+--------------+
                        |
                        v
         +-----------------------------+
         | 2. Academic Classification  |
         +--------------+--------------+
                        |
                        v
         +-----------------------------+
         |   3. Temporal Normalizer    |
         +--------------+--------------+
                        |
                        v
         +-----------------------------+
         | 4. Action & Meeting Parser  |
         +--------------+--------------+
                        |
                        v
         +-----------------------------+
         |  5. Semantic Action Binding |
         +--------------+--------------+
                        |
                        v
         +-----------------------------+
         |  6. Context Priority Engine |
         +--------------+--------------+
                        |
                        v
         +-----------------------------+
         |   7. Executive Summarizer   |
         +--------------+--------------+
                        |
                        v
         +-----------------------------+
         | 8. Evidence Grounding & Val |
         +--------------+--------------+
                        |
                        v
        Structured Output (`AIServiceOutput`)
```

---

## 2. Specialized Sub-Services Deep-Dive

### 2.1 Context Analysis & Task Detection
- **Module**: `ContextAnalysisService`
- **Function**: Inspects email headers, sender address format, and lexical structure to determine processing paths.
- **Edge Case Guard**: Detects completely empty or whitespace-only emails immediately, short-circuiting downstream heavy extraction to return a safe fallback without throwing unhandled exceptions.

### 2.2 Academic Classification Service
- **Module**: `ClassificationService`
- **Target Taxonomy**: Classifies messages into 10 distinct institutional domains:
  1. `Examination` (Question papers, invigilation, marks entry, moderation)
  2. `Administrative` (Deans, Registrar, circulars, compliance directives)
  3. `Academic` (Curriculum revision, syllabi, course outcomes)
  4. `Research` (Grant calls, DST/SERB, Ph.D. committees, paper reviews)
  5. `Placement` (Corporate drives, student shortlist verification, interviews)
  6. `Student Affair` (Disciplinary committees, student council, grievances)
  7. `Accreditation / IQAC` (NAAC, NBA, ABET peer team visits, course files)
  8. `Finance / Accounts` (Travel grants, reimbursement claims, payroll)
  9. `Campus Events` (Inaugurations, cultural fests, conferences)
  10. `General Notice` (Routine library notices, facility maintenance)
- **Algorithm**: Multi-tier keyword frequency weighting coupled with sender domain heuristics (e.g., `coe@` strongly weights Examination).

### 2.3 Temporal Normalization Service
- **Module**: `TemporalExtractionService`
- **Core Challenge**: Faculty emails frequently use relative temporal references (*"tomorrow at 3 PM"*, *"submit by next Friday"*, *"within 48 hours"*). Without anchor normalization, generic models cannot compute deadline proximity.
- **Reference-Anchored Normalization**:
  - The service accepts the email's explicit `received_at` timestamp as its temporal anchor ($T_0$).
  - Evaluates regex patterns for absolute dates (`September 25, 2026`, `25/09/2026`).
  - Evaluates relative offsets ($\Delta t$):
    - *"Tomorrow"* $\rightarrow T_0 + 1\text{ day}$
    - *"Next Monday"* $\rightarrow \text{Next occurrence of Monday relative to } T_0$
    - *"Within 3 days"* $\rightarrow T_0 + 3\text{ days}$
  - Emits a standardized ISO 8601 calendar date (`YYYY-MM-DD`).

### 2.4 Action Item Extraction Service
- **Module**: `ActionExtractionService`
- **Function**: Extracts imperative directives requiring faculty action.
- **Syntactic Parsing**:
  - Detects imperative verbs (*submit, review, verify, attend, upload, forward, prepare*).
  - Recognizes modal auxiliary politeness markers (*"Please ensure"*, *"Kindly submit"*, *"Faculty are requested to"*).
  - Handles leading grammatical conjuncts: parses complex multi-clause sentences starting with *"Also"*, *"Additionally"*, *"Furthermore"*, *"Moreover"*.

### 2.5 Joint Meeting Slot Extraction Service
- **Module**: `MeetingExtractionService`
- **Function**: Performs joint extraction across four complementary meeting slots:
  - `title`: Agenda or purpose of the meeting
  - `date`: Normalized ISO date (`YYYY-MM-DD`)
  - `time`: Scheduled time window (`02:30 PM`, `10:00 AM`)
  - `location`: Physical or virtual venue (*"Main Auditorium"*, *"Department Conference Room B"*, *"Google Meet"*)
  - `preparation`: Mandatory prerequisite materials (*"bring course files and mentoring records"*)

### 2.6 Context-Aware Priority Engine
- **Module**: `ContextAwarePriorityEngine`
- **Scoring Rubric**: Combines four weighted factors into a unified urgency index:
  $$\text{Score} = w_{\text{auth}} \cdot S_{\text{auth}} + w_{\text{dead}} \cdot S_{\text{dead}} + w_{\text{cons}} \cdot S_{\text{cons}} + \text{Bias}_{\text{user}}$$
  1. **Sender Authority Score ($S_{\text{auth}}$)**:
     - Statutory (Vice Chancellor, CoE, Registrar): 1.0
     - Institutional (Dean, IQAC Director): 0.8
     - Departmental (HOD, Committee Chair): 0.6
     - Peer / External Collaborator: 0.4
     - Student / Automated Circular: 0.2
  2. **Deadline Proximity Score ($S_{\text{dead}}$)**:
     - $\le 24\text{ hours}$: 1.0 (Critical urgency)
     - $\le 3\text{ days}$: 0.8
     - $\le 7\text{ days}$: 0.5
     - $> 7\text{ days}$: 0.2
     - No deadline: 0.0
  3. **Consequence Severity Score ($S_{\text{cons}}$)**:
     - Detects punitive or high-stakes consequence markers: *"late submissions will not be entertained"*, *"disciplinary action"*, *"accreditation non-compliance"*, *"cancellation"*.
  4. **Dynamic User Preferences**:
     - Weights are adjustable via `FacultyPreference` profiles (`BALANCED`, `DEADLINE_HEAVY`, `AUTHORITY_FIRST`).
- **Priority Tier Categorization**:
  - $\text{Score} \ge 0.70 \rightarrow \mathbf{HIGH}$
  - $0.40 \le \text{Score} < 0.70 \rightarrow \mathbf{MEDIUM}$
  - $\text{Score} < 0.40 \rightarrow \mathbf{LOW}$
- **Transparent Reasoning Generation**: Synthesizes a human-readable explanation justifying the tier assignment.

### 2.7 Action-Deadline Semantic Binding (`DUE_ON`)
- **Function**: Associates extracted action items with specific calendar deadlines.
- **Relational Schema**: Generates `AIActionItemOutput` records where `relationship_type = "DUE_ON"`, assigning the normalized due date directly to the corresponding imperative task.

### 2.8 Bidirectional Evidence Grounding Service
- **Module**: `EvidenceValidationService`
- **Function**: Guarantees zero ungrounded assertions by validating every extracted fact against the source email.
- **Verification Routine**:
  1. For every extracted claim (summary claim, deadline string, action text, meeting venue), searches for the exact substring in the raw email body.
  2. Computes character start and end offsets (`char_start`, `char_end`).
  3. Assigns `validation_status = "VERIFIED"` and confidence score $1.0$.
  4. If an assertion has no matching span, it is tagged as `UNVERIFIED`, alerting the faculty user to potential ungrounded extrapolation.

---

## 3. Extensible LLM Integration Layer

The application incorporates a decoupled `LLMService` supporting:
- **Google Gemini** (e.g., `gemini-1.5-flash`, `gemini-1.5-pro` via official REST API with `x-goog-api-key` header).
- **OpenAI** (e.g., `gpt-4o-mini`, `gpt-4o` via Chat Completions API).
- **Graceful Fallback State Machine**: If external network requests time out or return error codes (HTTP 401, 429, 500), the orchestrator silently catches the error, logs a secure trace, and falls back to the deterministic local heuristic engine. No unhandled exception reaches the end user.
