# AI Email Summarizer Agent for Faculty

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5+-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4+-38B2AC?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![SQLite](https://img.shields.io/badge/Database-SQLite%20%2B%20SQLAlchemy-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org)
[![Tests](https://img.shields.io/badge/Tests-181%20Passed%20(100%25)-44CC11?logo=pytest&logoColor=white)](https://pytest.org)
[![Status](https://img.shields.io/badge/Development-Stage%2018%20Complete-success)](docs/)

An explainable, auditable, and evidence-grounded multi-agent artificial intelligence platform designed to assist university faculty and academic administrators in triaging high-volume departmental, institutional, and student communications.

---

## 1. Problem Statement

University faculty members receive dozens of unstructured communications daily spanning statutory directives, examination schedules, accreditation audits (e.g., NAAC, NBA, ABET), curriculum committees, grant calls, and student advisement requests.

In unassisted email clients:
- **Urgent Deadlines Are Lost**: Time-sensitive grade submissions and question-paper deadlines get buried in long conversational paragraphs.
- **Cognitive Fatigue & Context Switching**: Faculty spend 60–90 minutes daily manually parsing routine circulars.
- **Hallucination Skepticism**: Generic LLM assistants frequently hallucinate dates, confuse sender authority, or generate summaries without verifiable citations.
- **Fragile Cloud Dependency**: Cloud-only AI assistants fail completely in offline or air-gapped university campus networks.

---

## 2. Core Capabilities

1. **Multi-Agent Orchestrated Extraction**: A coordinated 8-stage pipeline decomposes emails into context, academic domain classification (10 categories), relative temporal normalization, imperative action detection, joint meeting slot filling, multi-factor priority reasoning, executive summarization, and evidence grounding.
2. **Anchor-Relative Temporal Normalization**: Converts colloquial time references (*"by next Tuesday"*, *"tomorrow 5 PM"*) into normalized ISO calendar dates (`YYYY-MM-DD`) anchored to the exact email reception timestamp.
3. **Context-Aware Academic Priority Engine**: Calibrates urgency through a 4-factor scoring rubric:
   - **Sender Authority** (Statutory, Institutional, Departmental, Student, External)
   - **Deadline Proximity** (Under 24h, 3 days, 7 days, long horizon)
   - **Consequence Keywords** (De-registration, punitive marks, cancellation, compliance audits)
   - **Faculty Personalization Tuning** (Custom authority weight, deadline weight, consequence weight)
4. **Action-Deadline Semantic Binding (`DUE_ON`)**: Automatically connects imperative tasks (*"Submit question papers"*) to their corresponding temporal milestones.
5. **Bidirectional Evidence Grounding**: Extracts exact character spans (`char_start`, `char_end`) from raw email text for every summary sentence, deadline, and action item. The frontend highlights verified textual evidence, eliminating hallucination risks.
6. **Cross-Email Intelligence**: Groups disparate communications into thematic clusters, detects conversational threads, and builds a chronological deadline timeline.
7. **Dual-Mode Execution (100% Offline Resilience)**:
   - **Mock AI Mode**: Deterministic, offline, dependency-free heuristic and template analysis requiring zero internet or API keys.
   - **LLM Mode**: Optional live inference via Google Gemini or OpenAI with structured JSON schemas and automatic fallback to Mock AI on failure.
8. **Empirical Evaluation Framework**: Integrated ROUGE-1/2/L, Classification Macro-F1, Strict Deadline Exact Match ($\pm 0$ days), Priority Ordinal Distance, and Grounding Verification Rate calculators evaluated against a curated 10-email golden academic benchmark dataset.

---

## 3. System Architecture

```
                                  +---------------------------------------+
                                  |    Email Providers (Ingestion)        |
                                  |    - Synthetic Mock Provider          |
                                  |    - Optional OAuth2 Gmail Provider   |
                                  +-------------------+-------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  |    Security & Sanitization Layer      |
                                  |    - OWASP Security Headers           |
                                  |    - Body Size Limiting (5MB limit)   |
                                  |    - Script / HTML / SQL Escaping     |
                                  +-------------------+-------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  |    FastAPI REST Backend (Uvicorn)     |
                                  |    - 8 Modular API Routers            |
                                  |    - Global Error ID Containment      |
                                  +-------------------+-------------------+
                                                      |
                                                      v
+---------------------------------------------------------------------------------------------------+
|                                 AI AGENT ORCHESTRATOR PIPELINE                                    |
|                                                                                                   |
|  [Context Analysis]  -->  [Classification (10 Domains)]  -->  [Temporal Normalization (ISO)]     |
|           |                                                                 |                     |
|  [Action Extraction] <--  [Meeting Slot Extractor]      <--  [Context-Aware Priority Engine]     |
|           |                                                                                       |
|  [Summarization Engine]  -->  [Bidirectional Evidence Grounding & Verification]                   |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
                                  +---------------------------------------+
                                  |    Relational Persistence Layer       |
                                  |    - SQLite + SQLAlchemy 2.0 ORM      |
                                  |    - Foreign Keys & Cascading Deletes |
                                  +-------------------+-------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  |    React 18 + TypeScript Frontend     |
                                  |    - Two-Panel Intelligence View      |
                                  |    - Interactive Evidence Highlighting|
                                  |    - Personalization Profile Tuning   |
                                  |    - Cross-Email Intelligence Matrix  |
                                  +---------------------------------------+
```

---

## 4. Technology Stack

| Layer | Technology | Key Libraries & Utilities |
| :--- | :--- | :--- |
| **Frontend** | React 18.3, TypeScript 5.5, Vite 5.4 | Tailwind CSS, Lucide React, HeadlessUI, React Router 6 |
| **Backend** | Python 3.11–3.13, FastAPI 0.115 | Uvicorn (ASGI), Pydantic v2, SQLAlchemy 2.0 |
| **Database** | SQLite 3 | SQLAlchemy ORM with foreign key cascades, WAL mode |
| **AI / NLP** | Pure-Python Multi-Agent Architecture | Context engine, Regex temporal resolver, LCS ROUGE calculator |
| **Testing** | Pytest, TestClient, Node.js Test Runner | AnyIO, Starlette TestClient, Node native runner |

---

## 5. Development Stages Completed

- [x] **Stage 0**: Requirements, User Stories & System Architecture
- [x] **Stage 1**: Project Scaffolding & Virtual Environments
- [x] **Stage 2**: Relational Database Architecture & Synthetic Seed Dataset
- [x] **Stage 3**: FastAPI Core REST APIs & Multi-Parameter Filter Matrix
- [x] **Stage 4**: Deterministic Mock AI Engine (100% Offline)
- [x] **Stage 5**: Multi-Agent Orchestrator Pipeline
- [x] **Stage 6**: Information Extraction & Anchor-Relative Temporal Normalization
- [x] **Stage 7**: Context-Aware Priority Engine & Explainable Justifications
- [x] **Stage 8**: Action-Deadline Relational Semantic Mapping (`DUE_ON`)
- [x] **Stage 9**: Bidirectional Evidence Grounding & Character Span Verification
- [x] **Stage 10**: Modern React 18 + TypeScript + Tailwind Frontend
- [x] **Stage 11**: End-to-End Frontend/Backend Integration & Live Synchronization
- [x] **Stage 12**: Extensible LLM Integration (OpenAI & Gemini with Fallbacks)
- [x] **Stage 13**: Optional Gmail Provider Abstraction & Offline Mock Preservation
- [x] **Stage 14**: Cross-Email Intelligence (Thematic Clustering & Thread Timeline)
- [x] **Stage 15**: Faculty Personalization Tuning & Priority Weight Configuration
- [x] **Stage 16**: Security Review, OWASP Hardening & Input Sanitization
- [x] **Stage 17**: Comprehensive Automated Testing (181 Tests, 100% Green)
- [x] **Stage 18**: Evaluation Framework, Baseline Benchmarking & Non-Fabricated Metrics

---

## 6. Quickstart & Local Installation

### Prerequisites
- Python 3.11, 3.12, or 3.13
- Node.js v18+ or v20+ and npm

### Step 1: Clone and Set Up Virtual Environment
```bash
git clone <repository_url>
cd "Email Summarizer Agent"

# Create Python virtual environment
python -m venv backend/venv

# Activate virtual environment
# On Windows (PowerShell):
.\backend\venv\Scripts\Activate.ps1
# On Linux/macOS:
source backend/venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt
```

### Step 2: Configure Environment Variables
Copy the secure environment template:
```bash
cp .env.example .env
```
Default `.env` settings operate in **100% offline Mock AI mode** without requiring external credentials:
```env
APP_ENV=development
DEBUG=True
AI_MODE=mock
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=
EMAIL_PROVIDER=mock
```

### Step 3: Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

### Step 4: Run the Application
Open two terminal windows:

**Terminal 1 — Backend (FastAPI)**:
```bash
# From workspace root with venv activated:
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Swagger Documentation: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/api/health`

**Terminal 2 — Frontend (Vite + React)**:
```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```
- Web Application: `http://127.0.0.1:5173`

---

## 7. REST API Overview

| Router Prefix | Method & Path | Description |
| :--- | :--- | :--- |
| **System** | `GET /api/health` | Service health, active AI mode, email provider, and stage. |
| **System** | `GET /api/llm-status` | Provider status, active model, and masked credential telemetry. |
| **Emails** | `GET /api/emails` | Filterable email list (search, category, priority, date, pagination). |
| **Emails** | `GET /api/emails/{id}` | Complete email details with structured AI analysis and evidence. |
| **Dashboard** | `GET /api/dashboard/stats` | Aggregated priority counts, category distribution, upcoming deadlines. |
| **Actions** | `GET /api/actions` | All extracted action items with deadline relationships and completion status. |
| **Actions** | `PATCH /api/actions/{id}` | Toggle completion status (`PENDING` / `COMPLETED`). |
| **Analysis** | `POST /api/analysis/{id}` | Trigger on-demand multi-agent re-analysis for an individual email. |
| **Analysis** | `POST /api/analysis/batch` | Trigger batch analysis across all unanalyzed emails. |
| **Provider** | `GET /api/provider/status` | Current email provider status (mock vs gmail). |
| **Provider** | `POST /api/provider/sync` | Trigger synchronization cycle. |
| **Cross-Intelligence**| `GET /api/intelligence/clusters` | Thematic cross-email clusters, threads, and deadline timeline. |
| **Preferences** | `GET /api/preferences` | Retrieve active faculty personalization profile. |
| **Preferences** | `PUT /api/preferences` | Update faculty priority weights and category urgency overrides. |
| **Evaluation** | `GET /api/evaluation/benchmark` | Run baseline evaluation comparison across golden benchmark corpus. |
| **Evaluation** | `GET /api/evaluation/metrics/catalog` | Empirical vs experimental metrics registry. |

---

## 8. Empirical Evaluation & Baseline Comparison

In strict compliance with the **Zero-Fabrication Policy**, all reported numbers are computed live against the 10-email golden academic benchmark dataset (`BENCHMARK_DATASET`):

| Evaluation Metric | Baseline 1 (Heuristic) | Baseline 2 (Unstructured LLM) | Proposed System (Multi-Agent) | Relative $\Delta$ |
| :--- | :---: | :---: | :---: | :---: |
| **Grounding Verification Rate** | 0.0000 | 0.0000 | **1.0000** | **+1.0000 (100% verified spans)** |
| **Unsupported Assertion Rate** | 1.0000 | 1.0000 | **0.0000** | **-1.0000 (0% hallucinations)** |
| **Deadline Exact Match ($\pm 0$ days)**| 0.7000 | 0.7000 | **0.9000** | **+0.2000 (+20% accuracy)** |
| **Deadline Extraction F1** | 0.7368 | 0.7368 | **0.9474** | **+0.2106** |
| **Meeting Joint Slot Accuracy** | 0.6000 | 0.6000 | **0.8000** | **+0.2000 (+20% accuracy)** |
| **Action Presence Accuracy** | 0.5000 | 0.6000 | **0.9000** | **+0.4000 (+40% accuracy)** |
| **Action Jaccard Overlap** | 0.3073 | 0.1147 | **0.5402** | **+0.2329** |
| **Directional Error Penalty** (Lower is better)| 0.2800 | 0.3600 | **0.2200** | **-0.0600 (Fewer urgent misses)** |
| **Summary Compression Ratio** | 0.5193 | 0.2992 | **0.3017** | **-0.2176 (70% conciseness)** |

### Demarcation of Experimental Metrics
Metrics requiring human participant studies or longitudinal enterprise deployments are explicitly flagged with `status: "REQUIRES_EXPERIMENTAL_DATA"`:
- `EXP-001`: Human Faculty Inbox Triage Time Reduction (Minutes Saved / Day)
- `EXP-002`: Faculty Trust & Grounding Explainability Index (5-point Likert Scale)
- `EXP-003`: Institutional Inter-Annotator Agreement (Cohen's / Fleiss' Kappa)
- `EXP-004`: Longitudinal Cross-Semester Preference Adaptation
- `EXP-005`: Enterprise Operational Token Cost vs Accuracy Pareto Frontier

---

## 9. Automated Testing

The application includes an exhaustive automated test suite covering all architectural tiers:

```powershell
# Run the complete Python Pytest suite:
python -m pytest -v

# Run the frontend unit test suite:
cd frontend
node --test test/frontend_unit.test.mjs

# Verify frontend TypeScript build:
npm run build
```

- **Backend Pytest Results**: **181 passed** across 17 test modules (100% green).
- **Frontend Unit Results**: **7 passed** native Node.js tests (100% green).
- **Frontend Build**: **1,521 modules transformed**, 0 build errors in 3.53s.

---

## 10. Documentation Index

Detailed architectural and scientific documentation is provided in the [`docs/`](docs/) directory:
- [01. System Architecture Documentation](docs/01_system_architecture.md)
- [02. AI-Agent Orchestrator Documentation](docs/02_ai_agent_architecture.md)
- [03. Complete REST API Documentation](docs/03_api_documentation.md)
- [04. Database Relational Architecture Documentation](docs/04_database_documentation.md)
- [05. Technical Workflow & Email Lifecycle](docs/05_technical_workflow.md)
- [06. Evaluation Methodology & Scientific Protocol](docs/06_evaluation_methodology.md)
- [07. Prior-Art Analysis Structure](docs/07_prior_art_analysis_structure.md)
- [08. Technical Invention Disclosure](docs/08_invention_disclosure.md)
- [09. Patent-Oriented Technical Figure Descriptions](docs/09_patent_technical_figure_descriptions.md)
- [10. Known Limitations](docs/10_known_limitations.md)
- [11. Future Enhancements Roadmap](docs/11_future_enhancements.md)

---

## 11. Disclaimer

This software is developed for educational, institutional, and research evaluation purposes. Technical descriptions contained in the documentation and invention disclosure describe computational systems, data structures, and algorithms factually and do **not** constitute legal claims of patentability or patent rights.
