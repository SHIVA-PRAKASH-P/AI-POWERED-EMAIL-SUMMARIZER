# Patent-Oriented Technical Figure Descriptions

This document provides formal technical descriptions of system figures, block diagrams, process flowcharts, and data structure transitions for the **AI Email Summarizer Agent for Faculty**.

> [!NOTE]
> **Notice**: These figure descriptions are structured in standard patent-oriented technical documentation format for engineering specifications and scientific disclosure. They do not constitute a patent application or assert patentability.

---

## FIG. 1 — Overall System Architecture and Operating Environment

```
               [FIG. 1: SYSTEM BLOCK DIAGRAM]

  +-----------------------------------------------------------+
  | 100: CLIENT TIER (User Computing Device)                  |
  |   +-----------------------------------------------------+ |
  |   | 102: Web Browser Execution Runtime                  | |
  |   |   +-----------------------------------------------+ | |
  |   |   | 104: Single-Page Application (SPA)            | | |
  |   |   |   ├── 106: Two-Panel Inbox & Detail View      | | |
  |   |   |   ├── 108: Interactive Evidence Span Renderer | | |
  |   |   |   └── 110: Personalization Tuning Interface   | | |
  |   |   +-----------------------------------------------+ | |
  |   +-----------------------------------------------------+ |
  +-----------------------------+-----------------------------+
                                | 112: HTTPS / JSON REST API
                                v
  +-----------------------------------------------------------+
  | 120: APPLICATION SERVER TIER (FastAPI / Uvicorn Runtime)  |
  |   +-----------------------------------------------------+ |
  |   | 122: Security & Sanitization Layer                  | |
  |   |   ├── 124: Payload Size Limiter (5MB Max)           | |
  |   |   ├── 126: OWASP Header Injection Filter            | |
  |   |   └── 128: Script & SQL Wildcard Sanitizer          | |
  |   +-----------------------------------------------------+ |
  |   +-----------------------------------------------------+ |
  |   | 130: RESTful API Routing Subsystem                  | |
  |   |   ├── 132: Emails & Dashboard Endpoints             | |
  |   |   ├── 134: Actions & Meeting Endpoints              | |
  |   |   ├── 136: Cross-Email Intelligence Endpoints       | |
  |   |   └── 138: Benchmark & Evaluation Telemetry         | |
  |   +-----------------------------------------------------+ |
  |   +-----------------------------------------------------+ |
  |   | 140: Multi-Agent AI Orchestrator Pipeline           | |
  |   +-----------------------------------------------------+ |
  +-------------------+-------------------+-------------------+
                      |                   |
        142: ORM      |                   | 144: Ext. Network
        Transactions  v                   v (Optional)
  +------------------------+        +-------------------------+
  | 150: PERSISTENCE TIER  |        | 160: EXTERNAL SERVICES  |
  |  (SQLite / SQLAlchemy) |        |   ├── 162: Gmail API    |
  |  ├── 152: Emails Table |        |   └── 164: Cloud LLM    |
  |  ├── 154: Analyses     |        +-------------------------+
  |  ├── 156: Actions      |
  |  └── 158: Evidences    |
  +------------------------+
```

### Technical Description of FIG. 1
FIG. 1 illustrates a block diagram of the distributed computing environment. A user computing device 100 executes a web browser runtime 102 hosting a single-page application (SPA) 104. The SPA provides a two-panel interface 106, an interactive evidence highlighter 108, and a personalization tuning interface 110. Communications traverse network channel 112 to the application server tier 120. A security layer 122 enforces payload constraints (124), OWASP headers (126), and text sanitization (128). An API routing subsystem 130 dispatches requests to the multi-agent AI orchestrator 140. Persistent state is maintained via transactional channel 142 in relational storage 150 comprising tables 152–158. Optional external services 160 are accessed over channel 144.

---

## FIG. 2 — Multi-Agent Orchestration Sequence & Pipeline Flow

```
               [FIG. 2: MULTI-AGENT PIPELINE FLOW]

                 [200: Raw Ingested Email]
                            |
                            v
               [202: Context Analysis Guard]
             /                              \
       (Valid Text)                    (Empty/Whitespace)
           /                                    \
          v                                      v
  [204: Domain Classification]             [220: Safe Empty]
  (Assigns 1 of 10 Categories)             [    Fallback   ]
          |
          v
  [206: Temporal Normalizer]
  (Resolves relative dates against T_0)
          |
          v
  [208: Action & Meeting Parser]
  (Extracts imperatives & calendar slots)
          |
          v
  [210: Action-Deadline Semantic Binder]
  (Instantiates DUE_ON relational links)
          |
          v
  [212: Multi-Factor Priority Engine]
  (Calculates urgency score & reasoning)
          |
          v
  [214: Executive Summarizer]
  (Generates structured summary text)
          |
          v
  [216: Bidirectional Grounding Validator]
  (Verifies spans & resolves char offsets)
          |
          v
  [218: Structured Output Serialization]
```

### Technical Description of FIG. 2
FIG. 2 depicts the execution flow of the multi-agent orchestration pipeline. The pipeline receives an ingested email 200. Step 202 evaluates message validity; empty messages short-circuit to fallback state 220. Valid messages advance to classification sub-agent 204. Temporal normalizer 206 calculates normalized ISO calendar dates anchored to arrival timestamp $T_0$. Action and meeting extractor 208 identifies tasks and venues. Semantic binder 210 establishes `DUE_ON` relationships. Context-aware priority engine 212 computes continuous urgency and discrete priority tiers. Executive summarizer 214 synthesizes summary sentences. Evidence validator 216 validates claims against source text. Finally, step 218 serializes the structured result into the database.

---

## FIG. 3 — Anchor-Bound Temporal Normalization Logic

```
         [FIG. 3: TEMPORAL NORMALIZATION STATE MACHINE]

               [300: Inbound Email Ingestion]
                            |
                            v
             [302: Extract Anchor Timestamp T_0]
                            |
                            v
             [304: Regex Candidate Scanning]
                            |
           +----------------+----------------+
           |                                 |
           v                                 v
   [306: Absolute Match]             [308: Relative Match]
   (e.g., "September 25, 2026")      (e.g., "tomorrow at 5 PM",
           |                          "within 3 business days")
           v                                 |
   [310: Direct Calendar Parser]             v
           |                         [312: Compute Offset Delta_t]
           |                                 |
           |                         [314: Project T_0 + Delta_t]
           |                                 |
           +----------------+----------------+
                            |
                            v
             [316: Standardize ISO 8601 Date]
                      ("YYYY-MM-DD")
                            |
                            v
             [318: Bind to Action / Meeting]
```

### Technical Description of FIG. 3
FIG. 3 illustrates the temporal normalization state machine. Following email ingestion 300, step 302 extracts arrival timestamp $T_0$. Step 304 identifies candidate phrases. Branch 306 handles absolute dates via direct parser 310. Branch 308 handles relative expressions by calculating offset vector $\Delta t$ (312) and projecting $T_0 + \Delta t$ (314). Step 316 standardizes the result into an ISO 8601 calendar date. Step 318 associates the date with corresponding actions and meetings.

---

## FIG. 4 — Multi-Factor Context-Aware Priority Engine Flowchart

```
         [FIG. 4: PRIORITY SCORING FLOWCHART]

             [400: Initiate Priority Evaluation]
                            |
     +----------------------+----------------------+
     |                      |                      |
     v                      v                      v
[402: Evaluate         [404: Calculate        [406: Scan Consequence]
 Sender Authority]      Deadline Proximity]    Markers]
 (Statutory=1.0,        (<=24h: 1.0,           (Penalties, late
  Dean=0.8, HOD=0.6,     <=3d: 0.8,             submission bans,
  Student=0.2)           <=7d: 0.5)             audit compliance)
     |                      |                      |
     v                      v                      v
  S_auth                 S_dead                 S_cons
     |                      |                      |
     +----------------------+----------------------+
                            |
                            v
             [408: Retrieve Personalization Weights]
             (w_auth, w_dead, w_cons, w_bias from Profile)
                            |
                            v
             [410: Compute Weighted Sum Score S]
             S = w_auth*S_auth + w_dead*S_dead + w_cons*S_cons + Bias
                            |
                            v
             [412: Ordinal Tier Thresholding]
              /             |            \
       (S >= 0.70)   (0.40 <= S < 0.70)   (S < 0.40)
            |               |                 |
            v               v                 v
     [414: HIGH]      [416: MEDIUM]      [418: LOW]
            |               |                 |
            +---------------+-----------------+
                            |
                            v
             [420: Generate Traceable Reasoning]
```

### Technical Description of FIG. 4
FIG. 4 diagrams the priority reasoning engine. Evaluation 400 branches into three parallel factor evaluators: sender authority 402, deadline proximity 404, and consequence severity 406. In step 408, active personalization weights are retrieved. Step 410 computes the composite urgency score $S$. In step 412, threshold logic assigns the message to HIGH (414), MEDIUM (416), or LOW (418). Step 420 synthesizes an explainable justification text.

---

## FIG. 5 — Bidirectional Evidence Grounding Verification Routine

```
         [FIG. 5: EVIDENCE GROUNDING ROUTINE]

             [500: Extracted Claim Assertion]
                            |
                            v
             [502: Load Raw Email Body Text T]
                            |
                            v
             [504: Exact Substring Search]
                            |
                 +----------+----------+
                 |                     |
             (Match Found)       (No Match Found)
                 |                     |
                 v                     v
     [506: Compute 0-Indexed   [514: Tag UNVERIFIED]
      char_start & char_end]   (Confidence = 0.0)
                 |                     |
                 v                     |
     [508: Tag VERIFIED]               |
      (Confidence = 1.0)               |
                 |                     |
                 +----------+----------+
                            |
                            v
             [510: Persist Evidence Record]
                            |
                            v
             [512: UI Hover-Highlight Binding]
```

### Technical Description of FIG. 5
FIG. 5 diagrams the anti-hallucination evidence grounding routine. An extracted assertion 500 is tested against raw email text $T$ (502) via substring matcher 504. When located, step 506 extracts precise character start and end offsets, and step 508 assigns `VERIFIED` status with confidence 1.0. If absent, step 514 flags the assertion as `UNVERIFIED`. Step 510 commits the evidence record to the database, and step 512 binds the coordinates to interactive frontend hover highlights.
