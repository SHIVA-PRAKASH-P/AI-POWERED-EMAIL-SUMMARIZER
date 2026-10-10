# Complete REST API Documentation

The **AI Email Summarizer Agent for Faculty** exposes a high-performance RESTful API developed with **FastAPI**. All responses adhere to standard HTTP status conventions and serialize structured JSON using **Pydantic v2**.

---

## 1. Global Conventions & Error Handling

- **Base URL**: `http://127.0.0.1:8000`
- **Interactive Documentation**: `GET /docs` (Swagger UI), `GET /redoc` (ReDoc)
- **Standard Error Response**:
  ```json
  {
    "status": "error",
    "message": "Human-readable error description.",
    "error_id": "uuid-v4-identifier"
  }
  ```
- **HTTP Status Codes**:
  - `200 OK`: Request succeeded.
  - `201 Created`: Resource successfully created.
  - `400 Bad Request`: Invalid parameters or malformed syntax.
  - `404 Not Found`: Target resource does not exist.
  - `413 Payload Too Large`: Request body exceeds 5MB limit.
  - `422 Unprocessable Entity`: Schema validation failure.
  - `500 Internal Server Error`: Server exception with contained `error_id`.

---

## 2. System & Health Endpoints

### `GET /api/health`
Returns system operational state, active AI configuration, and developmental stage.
- **Response `200 OK`**:
  ```json
  {
    "status": "healthy",
    "ai_mode": "mock",
    "llm_provider": "openai",
    "llm_model": "gpt-4o-mini",
    "llm_configured": false,
    "email_provider": "mock",
    "stage": "STAGE 18 — EVALUATION FRAMEWORK"
  }
  ```

### `GET /api/llm-status`
Returns cloud LLM provider configuration with masked credential telemetry.
- **Response `200 OK`**:
  ```json
  {
    "ai_mode": "mock",
    "provider": "openai",
    "model": "gpt-4o-mini",
    "masked_api_key": null,
    "temperature": 0.2,
    "fallback_on_error": true,
    "is_ready": true
  }
  ```

---

## 3. Email Ingestion & Management (`/api/emails`)

### `GET /api/emails`
Retrieves a paginated, filterable collection of email records with summary metadata.
- **Query Parameters**:
  - `search` (string, optional): Full-text search in subject, body, or sender.
  - `category` (string, optional): Filter by academic domain (*e.g., Examination, Administrative*).
  - `priority` (string, optional): Filter by priority tier (*HIGH, MEDIUM, LOW*).
  - `date_from` (string, optional): ISO date lower bound (`YYYY-MM-DD`).
  - `date_to` (string, optional): ISO date upper bound (`YYYY-MM-DD`).
  - `unread_only` (bool, optional, default: `false`): Restrict to unread communications.
  - `page` (int, optional, default: `1`): Page number (1-indexed).
  - `limit` (int, optional, default: `20`, max: `100`): Page size.
- **Response `200 OK`**:
  ```json
  {
    "total": 12,
    "page": 1,
    "limit": 20,
    "pages": 1,
    "items": [
      {
        "id": 1,
        "sender": "coe@university.edu",
        "subject": "URGENT: End-Semester Question Paper Submission Deadline",
        "received_at": "2026-09-10T09:00:00",
        "is_read": false,
        "category": "Examination",
        "priority": "HIGH",
        "priority_reason": "Statutory examination deadline from Controller of Examinations.",
        "deadline": "2026-09-25",
        "has_meeting": false,
        "action_item_count": 2
      }
    ]
  }
  ```

### `GET /api/emails/{id}`
Retrieves complete email details including body text, parsed AI analysis, action items with relational bindings, meeting slots, entities, and verified evidence spans.
- **Path Parameter**: `id` (integer, ge=1)
- **Response `200 OK`**:
  ```json
  {
    "id": 1,
    "sender": "coe@university.edu",
    "subject": "URGENT: End-Semester Question Paper Submission Deadline",
    "body": "Dear Faculty Members...\n",
    "received_at": "2026-09-10T09:00:00",
    "is_read": false,
    "analysis": {
      "id": 1,
      "summary": "CoE mandates submission of two question paper sets by September 25, 2026 at 5:00 PM.",
      "category": "Examination",
      "priority": "HIGH",
      "priority_reason": "Statutory examination deadline with punitive late submission notice.",
      "deadline": "2026-09-25"
    },
    "action_items": [
      {
        "id": 1,
        "description": "submit two sets of question papers along with detailed scheme of valuation",
        "due_date": "2026-09-25",
        "status": "PENDING",
        "relationship_type": "DUE_ON"
      }
    ],
    "meeting": null,
    "evidence": [
      {
        "id": 1,
        "field_name": "deadline",
        "extracted_value": "2026-09-25",
        "source_text": "September 25, 2026",
        "char_start": 284,
        "char_end": 302,
        "validation_status": "VERIFIED"
      }
    ]
  }
  ```

---

## 4. Dashboard Metrics (`/api/dashboard`)

### `GET /api/dashboard/stats`
Retrieves aggregated statistical metrics across the user's email repository.
- **Response `200 OK`**:
  ```json
  {
    "total_emails": 12,
    "unread_emails": 8,
    "high_priority_count": 4,
    "medium_priority_count": 5,
    "low_priority_count": 3,
    "pending_actions_count": 7,
    "upcoming_meetings_count": 3,
    "category_distribution": {
      "Examination": 2,
      "Administrative": 4,
      "Academic": 2,
      "Research": 2,
      "Placement": 1,
      "General Notice": 1
    }
  }
  ```

---

## 5. Action Items Lifecycle (`/api/actions`)

### `GET /api/actions`
Lists all extracted action items across emails.
- **Query Parameters**:
  - `status` (string, optional): Filter by status (`PENDING` or `COMPLETED`).
  - `email_id` (int, optional): Restrict to specific email.
- **Response `200 OK`**: List of `ActionItemResponse` objects.

### `PATCH /api/actions/{id}`
Toggles or updates the completion status of an extracted task.
- **Path Parameter**: `id` (integer, ge=1)
- **Request Body**:
  ```json
  {
    "status": "COMPLETED"
  }
  ```
- **Response `200 OK`**: Updated action item object.

---

## 6. On-Demand AI Analysis (`/api/analysis`)

### `POST /api/analysis/{id}`
Triggers an immediate re-orchestration of the multi-agent AI pipeline for an individual email.
- **Path Parameter**: `id` (integer, ge=1)
- **Response `200 OK`**: Newly synthesized `AIAnalysisResponse`.

### `POST /api/analysis/batch`
Triggers sequential AI orchestration across all unanalyzed emails.
- **Response `200 OK`**:
  ```json
  {
    "status": "success",
    "processed_count": 4,
    "message": "Batch AI analysis completed successfully."
  }
  ```

---

## 7. Cross-Email Intelligence (`/api/intelligence`)

### `GET /api/intelligence/clusters`
Performs multi-email semantic clustering, thread detection, and timeline consolidation.
- **Response `200 OK`**:
  ```json
  {
    "total_clusters": 3,
    "clusters": [
      {
        "cluster_id": "CLUST-EXAM-2026",
        "topic": "End-Semester Examination Directives",
        "primary_category": "Examination",
        "email_count": 2,
        "emails": [1, 5],
        "summary": "Coordinated schedule for question paper submissions and invigilation duties.",
        "key_entities": ["Controller of Examinations", "Evaluation Committee"],
        "critical_dates": ["2026-09-25", "2026-10-02"]
      }
    ],
    "timeline": [
      {
        "date": "2026-09-15",
        "event": "TechCorp student shortlist verification deadline",
        "email_id": 5,
        "priority": "HIGH"
      }
    ]
  }
  ```

---

## 8. Faculty Personalization Preferences (`/api/preferences`)

### `GET /api/preferences`
Retrieves the active faculty priority weighting configuration.
- **Response `200 OK`**:
  ```json
  {
    "id": 1,
    "profile_name": "Dean / Department Administrator",
    "weight_authority": 0.35,
    "weight_deadline": 0.35,
    "weight_consequence": 0.20,
    "weight_user_bias": 0.10,
    "high_priority_categories": ["Examination", "Accreditation", "Administrative"],
    "authority_boost_domains": ["university.edu", "ugc.gov.in", "aicte-india.org"]
  }
  ```

### `PUT /api/preferences`
Updates priority weights and category urgency overrides. Validates that weights sum approximately to 1.0.
- **Request Body**:
  ```json
  {
    "profile_name": "Research Heavy Faculty",
    "weight_authority": 0.20,
    "weight_deadline": 0.30,
    "weight_consequence": 0.20,
    "weight_user_bias": 0.30,
    "high_priority_categories": ["Research", "Academic"]
  }
  ```

---

## 9. Evaluation & Benchmarking (`/api/evaluation`)

### `GET /api/evaluation/benchmark`
Executes the comprehensive tripartite baseline evaluation against the 10-email golden benchmark corpus.
- **Query Parameter**: `refresh` (bool, default: `false`)
- **Response `200 OK`**:
  ```json
  {
    "timestamp": "2026-09-06T16:49:12.831000",
    "sample_count": 10,
    "empirical_results": {
      "heuristic_baseline": { ... },
      "unstructured_baseline": { ... },
      "proposed_agent_system": { ... }
    },
    "improvement_deltas": { ... },
    "experimental_metrics": [ ... ],
    "zero_fabrication_attestation": "All empirical metrics reported herein are calculated live at execution time..."
  }
  ```

### `GET /api/evaluation/metrics/catalog`
Returns the formal registry of evaluation metrics, distinguishing computable empirical metrics from metrics requiring human participant field trials.
