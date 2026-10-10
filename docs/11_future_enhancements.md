# Future Enhancements Roadmap

This document details the planned technological evolution and architectural roadmap for the **AI Email Summarizer Agent for Faculty**.

---

## 1. On-Device Local Small Language Model (SLM) Inference

- **Objective**: Eliminate reliance on cloud LLM APIs while exceeding heuristic capabilities.
- **Architectural Proposal**:
  - Integrate a quantized local Small Language Model (e.g., **Google Gemma-2-2B-Instruct** or **Microsoft Phi-3.5-mini**) executing via `llama.cpp` or ONNX Runtime directly on consumer CPUs or Apple Silicon / NVIDIA GPUs.
  - Fine-tune the SLM on open-source academic administrative correspondence using LoRA (Low-Rank Adaptation) to achieve high ROUGE scores and domain-accurate extraction with zero network latency and zero data privacy risk.

---

## 2. Multi-Modal OCR Ingestion Pipeline

- **Objective**: Ingest and analyze scanned PDF circulars, official gazettes, and image-based event posters.
- **Architectural Proposal**:
  - Introduce an `AttachmentProcessingSubservice` into the ingestion gateway.
  - Employ local optical character recognition (e.g., `pytesseract` or lightweight `TrOCR`) to extract textual layers from image attachments before passing content to the `AIOrchestrator`.

---

## 3. Two-Way Calendar Synchronization (iCal / CalDAV / Google Calendar)

- **Objective**: Bridge the gap between extracted calendar intelligence and faculty scheduling tools.
- **Architectural Proposal**:
  - Expose an iCalendar feed endpoint (`GET /api/calendar/feed.ics`) that faculty can subscribe to directly from Apple Calendar, Microsoft Outlook, or Google Calendar.
  - Provide one-click CalDAV and Google Calendar event creation for extracted meetings and bound deadlines, automatically embedding source email citations into event descriptions.

---

## 4. Multi-Tenant Role-Based Access Control (RBAC)

- **Objective**: Scale from personal faculty workstation installations to campus-wide university deployments.
- **Architectural Proposal**:
  - Migrate persistence layer to PostgreSQL with row-level security (RLS).
  - Implement OAuth2 / SAML Single Sign-On (SSO) integrated with university identity providers (e.g., Shibboleth, Active Directory, Google Workspace).
  - Support hierarchical preference inheritance: University-wide priority policies inherited by Departments, with individual faculty customization bounds.

---

## 5. Real-Time Push Ingestion via IMAP IDLE & Webhooks

- **Objective**: Replace periodic polling with instant email processing.
- **Architectural Proposal**:
  - Implement a persistent background worker listening to IMAP IDLE sockets or Google Cloud Pub/Sub push webhooks.
  - Use WebSockets to push newly analyzed communications and priority alerts to the React frontend in real time without manual page refreshes.

---

## 6. Longitudinal Preference Adaptation via Online Learning

- **Objective**: Automatically adapt faculty priority weights based on user triage behavior.
- **Architectural Proposal**:
  - Track implicit and explicit user signals (manual priority overrides, reading order, star/flag actions).
  - Train an online logistic regression or Bayesian bandit model to subtly calibrate $w_{\text{authority}}$, $w_{\text{deadline}}$, and $w_{\text{consequence}}$ over consecutive academic terms without requiring manual slider adjustments.
