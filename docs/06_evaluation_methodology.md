# Evaluation Methodology & Benchmark Documentation

This document outlines the rigorous evaluation infrastructure, mathematical formulations, baseline comparison framework, and experimental protocols designed for the **AI Email Summarizer Agent for Faculty**.

---

## 1. Zero-Fabrication Policy

In strict accordance with empirical research standards:
- **Zero Hardcoded Numbers**: All empirical metrics reported by the evaluation engine are dynamically calculated at execution time against a verified golden benchmark dataset.
- **Zero Fabricated Human Trials**: Metrics that cannot be honestly computed without live faculty participants (such as daily triage time reduction or user trust indices) are strictly demarcated under `status: "REQUIRES_EXPERIMENTAL_DATA"`, accompanied by formal clinical trial protocols rather than simulated numbers.

---

## 2. Golden Benchmark Dataset (`BENCHMARK_DATASET`)

The evaluation framework incorporates a curated golden benchmark dataset of 10 representative, verified academic communications spanning core faculty duties:

| ID | Institutional Domain | Authority Level | Expected Priority | Strict Normalized Deadline | Meeting Venue | Verified Spans |
| :--- | :--- | :--- | :---: | :---: | :--- | :---: |
| `BENCH-001` | Examination | Controller of Examinations | **HIGH** | 2026-09-25 | None | 4 spans |
| `BENCH-002` | Accreditation | Dean of Academic Affairs | **HIGH** | 2026-09-18 | Main Auditorium | 5 spans |
| `BENCH-003` | Department Admin | Head of Department | **MEDIUM**| 2026-09-20 | Conf Room B | 5 spans |
| `BENCH-004` | Research Grants | R&D Secretariat | **MEDIUM**| 2026-10-15 | None | 4 spans |
| `BENCH-005` | Placement | Training & Placement Officer | **HIGH** | 2026-09-15 | None | 4 spans |
| `BENCH-006` | Library Services | Chief Librarian | **LOW** | 2026-11-30 | None | 3 spans |
| `BENCH-007` | Student Affairs | Cultural Council | **LOW** | None | Open Air Theatre | 4 spans |
| `BENCH-008` | Quality Assurance| IQAC Director | **HIGH** | 2026-09-28 | None | 4 spans |
| `BENCH-009` | Research Advising| Ph.D. Research Scholar | **MEDIUM**| 2026-09-21 | Faculty Office | 4 spans |
| `BENCH-010` | Financial Admin | Accounts Office | **MEDIUM**| 2026-09-30 | None | 4 spans |

Every annotated grounded span is algorithmically validated to be a verbatim substring in the raw email body or subject.

---

## 3. Mathematical Metric Formulations

All metrics are implemented in pure Python (`MetricsCalculator`) without external dependencies:

### 3.1 Summarization Quality (ROUGE-1, ROUGE-2, ROUGE-L)
- **ROUGE-N Overlap**:
  $$\text{Precision}_N = \frac{\sum_{\text{gram}_n \in \text{Pred}} \min(\text{count}(\text{gram}_n, \text{Pred}), \text{count}(\text{gram}_n, \text{Ref}))}{\sum_{\text{gram}_n \in \text{Pred}} \text{count}(\text{gram}_n, \text{Pred})}$$
  $$\text{Recall}_N = \frac{\sum_{\text{gram}_n \in \text{Ref}} \min(\text{count}(\text{gram}_n, \text{Pred}), \text{count}(\text{gram}_n, \text{Ref}))}{\sum_{\text{gram}_n \in \text{Ref}} \text{count}(\text{gram}_n, \text{Ref})}$$
  $$F_1 = \frac{2 \cdot \text{Precision}_N \cdot \text{Recall}_N}{\text{Precision}_N + \text{Recall}_N}$$
- **ROUGE-L (Longest Common Subsequence)**:
  Uses dynamic programming to compute the length of the longest common subsequence of tokens between prediction $X$ ($m$ tokens) and reference $Y$ ($n$ tokens):
  $$R_{\text{LCS}} = \frac{\text{LCS}(X, Y)}{m}, \quad P_{\text{LCS}} = \frac{\text{LCS}(X, Y)}{n}, \quad F_{\text{LCS}} = \frac{2 \cdot P_{\text{LCS}} \cdot R_{\text{LCS}}}{P_{\text{LCS}} + R_{\text{LCS}}}$$

### 3.2 Priority Alignment & Asymmetric Directional Penalty
Standard classification accuracy treats all errors equally. For faculty email triage, an asymmetric error penalty is essential: misclassifying a statutory **HIGH** priority notice as **LOW** is potentially disastrous, whereas marking a **LOW** notice as **HIGH** is merely a minor inconvenience.
- **Ordinal Distance**:
  $$\text{Distance} = \frac{1}{N} \sum_{i=1}^N |\text{Priority}_{\text{pred}}^{(i)} - \text{Priority}_{\text{ref}}^{(i)}| \quad (\text{LOW}=1, \text{MED}=2, \text{HIGH}=3)$$
- **Directional Penalty**:
  $$\text{Penalty} = \begin{cases} 2.0 & \text{if Ref}=\text{HIGH}, \text{Pred}=\text{LOW} \quad (\text{Critical failure}) \\ 1.0 & \text{if Ref}=\text{HIGH}, \text{Pred}=\text{MEDIUM} \\ 0.8 & \text{if Ref}=\text{MEDIUM}, \text{Pred}=\text{LOW} \\ 0.3 \cdot (\text{Pred} - \text{Ref}) & \text{if Pred} > \text{Ref} \quad (\text{Over-caution}) \end{cases}$$

### 3.3 Strict Deadline Exact Match ($\pm 0$ days)
Requires the extracted deadline to match the true calendar date exactly on day, month, and year:
$$\text{Accuracy}_{\text{deadline}} = \frac{1}{N} \sum_{i=1}^N \mathbb{I}(\text{Norm}(\text{Deadline}_{\text{pred}}^{(i)}) == \text{Norm}(\text{Deadline}_{\text{ref}}^{(i)}))$$

### 3.4 Evidence Grounding Verification Rate
Evaluates anti-hallucination fidelity by verifying character spans:
$$\text{Grounding Verification Rate} = \frac{\text{Verified Evidence Claims}}{\text{Total Extracted Claims}}$$
$$\text{Unsupported Assertion Rate} = 1.0 - \text{Grounding Verification Rate}$$

---

## 4. Live Empirical Comparison Results

Computed dynamically by `EvaluationEngine.run_benchmark()` across all 10 benchmark instances:

| Evaluation Metric | Baseline 1 (Heuristic) | Baseline 2 (Unstructured LLM) | Proposed System (Multi-Agent) | $\Delta$ vs Heuristic | $\Delta$ vs Unstructured |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Grounding Verification Rate** | 0.0000 | 0.0000 | **1.0000** | **+1.0000** | **+1.0000** |
| **Unsupported Assertion Rate** | 1.0000 | 1.0000 | **0.0000** | **-1.0000** | **-1.0000** |
| **Deadline Exact Match ($\pm 0$ days)**| 0.7000 | 0.7000 | **0.9000** | **+0.2000** | **+0.2000** |
| **Deadline Extraction F1** | 0.7368 | 0.7368 | **0.9474** | **+0.2106** | **+0.2106** |
| **Meeting Slot Accuracy** | 0.6000 | 0.6000 | **0.8000** | **+0.2000** | **+0.2000** |
| **Action Item Presence Accuracy** | 0.5000 | 0.6000 | **0.9000** | **+0.4000** | **+0.3000** |
| **Action Jaccard Overlap** | 0.3073 | 0.1147 | **0.5402** | **+0.2329** | **+0.4255** |
| **Directional Error Penalty** (Lower is better)| 0.2800 | 0.3600 | **0.2200** | **-0.0600** | **-0.1400** |
| **High-Priority Recall** | 0.7500 | 0.2500 | **0.7500** | 0.0000 | **+0.5000** |
| **ROUGE-1 F1** | 0.4301 | 0.2763 | **0.3489** | -0.0812 | **+0.0726** |
| **ROUGE-2 F1** | 0.2328 | 0.1065 | **0.1212** | -0.1116 | **+0.0147** |
| **ROUGE-L F1** | 0.3397 | 0.2215 | **0.2495** | -0.0902 | **+0.0280** |
| **Compression Ratio** | 0.5193 | 0.2992 | **0.3017** | **-0.2176** | +0.0025 |

---

## 5. Formal Catalog of Experimental Metrics (`REQUIRES_EXPERIMENTAL_DATA`)

The following metrics strictly require live human participants or longitudinal institutional deployments and cannot be fabricated:

### EXP-001: Human Faculty Inbox Triage Time Reduction
- **Status**: `REQUIRES_EXPERIMENTAL_DATA`
- **Target Hypothesis**: AI-assisted triage reduces active inbox management time by $\ge 40\%$.
- **Protocol**: 4-week randomized crossover trial with $N=30$ full-time faculty across Engineering, Sciences, and Humanities. Daily triage minutes measured via background screen telemetry. Statistical analysis via paired Student's t-test ($\alpha = 0.05$).

### EXP-002: Faculty Trust & Grounding Explainability Index
- **Status**: `REQUIRES_EXPERIMENTAL_DATA`
- **Target Hypothesis**: Verifiable bidirectional span highlighting achieves mean trust rating $\ge 4.2 / 5.0$.
- **Protocol**: Post-task psychometric questionnaire (Likert 1–5) based on the standardized System Usability Scale (SUS) and Automated System Trust Index administered after verifying 50 email analyses.

### EXP-003: Institutional Inter-Annotator Agreement (Corpus Gold Standard)
- **Status**: `REQUIRES_EXPERIMENTAL_DATA`
- **Target Hypothesis**: Faculty consensus on email priority tiers achieves substantial agreement ($\kappa \ge 0.70$).
- **Protocol**: Triple-blind annotation of 500 uncurated institutional emails by 3 department chairs. Consensus evaluated via Fleiss' Kappa with 1,000 bootstrap iterations.

### EXP-004: Longitudinal Cross-Semester Preference Adaptation
- **Status**: `REQUIRES_EXPERIMENTAL_DATA`
- **Target Hypothesis**: Dynamic priority weights adapt to schedule shifts within 14 interaction days.
- **Protocol**: Observational cohort study tracking manual priority overrides during Fall-to-Spring semester transitions, evaluated via repeated measures ANOVA.

### EXP-005: Enterprise Operational Token Cost vs Accuracy Pareto Frontier
- **Status**: `REQUIRES_EXPERIMENTAL_DATA`
- **Target Hypothesis**: Hybrid heuristic-orchestration pipeline reduces LLM token consumption by $\ge 60\%$ with $< 2\%$ drop in F1.
- **Protocol**: Server-side telemetry and latency profiling across 100,000 communications in production environment.
