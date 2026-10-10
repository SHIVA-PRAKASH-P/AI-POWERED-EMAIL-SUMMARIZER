# Technical Invention Disclosure

> [!NOTE]
> **Legal Disclaimer**: This document is a technical invention disclosure prepared for engineering documentation and scientific review. It describes concrete algorithms, data structures, and computer-implemented systems. It does **not** assert legal claims of patentability, patent validity, or intellectual property exclusivity.

---

## 1. Title of the Technical Disclosure

**System, Method, and Computer-Readable Medium for Evidence-Grounded Multi-Agent Email Intelligence, Anchor-Relative Temporal Normalization, and Context-Aware Priority Triage**

---

## 2. Technical Field

The present disclosure relates generally to the fields of computer science, natural language processing (NLP), multi-agent software architectures, and automated information extraction. More particularly, the disclosure relates to computer-implemented systems and methods for extracting structured intelligence, normalizing temporal milestones relative to message arrival anchors, establishing relational semantic links between extracted actions and deadlines, and verifying claims via bidirectional character span grounding.

---

## 3. Technical Problem Addressed

1. **Context-Insensitive Urgency Assignment**: Conventional email systems rely on static boolean flags (e.g., standard MIME `X-Priority` headers) or basic keyword matches. Such mechanisms cannot weigh institutional authority hierarchies against deadline proximity and punitive consequence language.
2. **Temporal Drift in Relative Expressions**: Conversational language models normalize relative date references (*"tomorrow"*, *"next Wednesday"*) using the execution timestamp of the model prompt rather than the historical arrival timestamp of the communication, introducing severe calendar errors during asynchronous or delayed triage.
3. **Generative Hallucination & Citation Gap**: Generative language models synthesize fluent executive summaries but frequently introduce unsupported assertions or alter critical numbers/venues without providing inspectable character-level provenance.
4. **Cloud-Paralysis Single Point of Failure**: Modern AI assistants are monolithic cloud services that become entirely inoperative during network downtime, API rate limiting, or institutional security firewalls.

---

## 4. Detailed Technical Description of Embodiments

### 4.1 Reference-Anchored Temporal Normalization Engine
The system implements a computer-implemented method for resolving relative temporal expressions into unambiguous calendar dates:
1. An incoming communication $M$ contains raw text $T$ and a metadata header specifying arrival timestamp $T_0$.
2. The temporal extraction engine scans $T$ using token pattern regular expressions to identify temporal candidates $C = \{c_1, c_2, \dots, c_k\}$.
3. For each candidate $c_i$:
   - If $c_i$ represents an absolute date (e.g., *"September 25, 2026"*), it is parsed directly into an ISO 8601 calendar string $D_i$ (`YYYY-MM-DD`).
   - If $c_i$ represents a relative expression (e.g., *"tomorrow"*, *"in 3 days"*, *"next Monday"*), the engine calculates an offset vector $\Delta t$ and evaluates:
     $$D_i = \text{CalendarProject}(T_0 + \Delta t)$$
4. The resolved calendar date $D_i$ is bound strictly to $T_0$, ensuring that regardless of when the email is subsequently analyzed, the normalized date remains invariant and chronologically accurate.

### 4.2 Multi-Factor Context-Aware Priority Engine
The system computes an objective urgency score $S \in [0.0, 1.0]$ through a multi-factor linear combination:
$$S = w_{\text{auth}} \cdot f_{\text{auth}}(\text{Sender}) + w_{\text{dead}} \cdot f_{\text{dead}}(D_{\text{min}} - T_0) + w_{\text{cons}} \cdot f_{\text{cons}}(T) + w_{\text{bias}} \cdot \text{UserBias}$$
Subject to:
$$w_{\text{auth}} + w_{\text{dead}} + w_{\text{cons}} + w_{\text{bias}} = 1.0$$
Where:
- $f_{\text{auth}}(\text{Sender}) \in [0.2, 1.0]$ evaluates the institutional hierarchy of the sender address against an authority dictionary (Statutory, Institutional, Departmental, Student, External).
- $f_{\text{dead}}(\Delta d)$ assigns a non-linear decay function to the minimum detected deadline proximity:
  $$f_{\text{dead}}(\Delta d) = \begin{cases} 1.0 & \text{if } \Delta d \le 24\text{ hours} \\ 0.8 & \text{if } 24\text{h} < \Delta d \le 72\text{ hours} \\ 0.5 & \text{if } 72\text{h} < \Delta d \le 168\text{ hours} \\ 0.2 & \text{if } \Delta d > 168\text{ hours} \\ 0.0 & \text{if no deadline detected} \end{cases}$$
- $f_{\text{cons}}(T) \in [0.0, 1.0]$ detects punitive, contractual, or compliance consequences (*"late submissions rejected"*, *"audit compliance"*).
- The continuous score $S$ is discretized into ordinal tiers: **HIGH** ($S \ge 0.70$), **MEDIUM** ($0.40 \le S < 0.70$), and **LOW** ($S < 0.40$).

### 4.3 Action-Deadline Semantic Binding (`DUE_ON`)
The system links extracted imperative tasks to specific calendar milestones:
1. Imperative sentences are identified by detecting leading imperative verbs and polite modal prefixes.
2. If an imperative clause is syntactically proximate to a normalized deadline $D_i$, a relational edge is instantiated:
   $$\text{Edge}(\text{Action}_j, D_i, \text{type}="DUE\_ON")$$
3. The relationship is stored in the relational schema, enabling task managers to sort actions chronologically rather than merely listing unanchored text strings.

### 4.4 Bidirectional Character-Offset Evidence Grounding
To prevent generative hallucination, every extracted entity, deadline, action, and summary assertion is subjected to a verification routine:
1. For an assertion $A$ containing target text $V$, the engine searches the raw message body $T$ for matching character sequences.
2. Upon identifying a match, the engine extracts exact 0-indexed character offsets:
   $$\text{Span} = (\text{char\_start}, \text{char\_end}) \quad \text{such that } T[\text{char\_start}:\text{char\_end}] == V$$
3. An evidence object is persisted with `validation_status = "VERIFIED"` and confidence score 1.0.
4. The client user interface renders interactive visual links connecting the summary claim to the highlighted source span in the raw email display.

### 4.5 Deterministic Dual-Mode Fallback Architecture
The orchestrator maintains architectural parity between a cloud-based LLM engine and a local deterministic heuristic engine:
1. The system attempts inference via the configured cloud LLM using strict JSON schema validation.
2. If an API exception, network timeout, or malformed JSON payload occurs, a graceful fallback interceptor routes the raw email to the local deterministic heuristic sub-services.
3. Both engines output the identical `AIServiceOutput` data structure, ensuring zero database schema disruption and continuous offline operational availability.
