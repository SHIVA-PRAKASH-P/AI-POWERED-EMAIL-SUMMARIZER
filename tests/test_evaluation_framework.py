import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.evaluation.ground_truth_schema import GroundTruthEmail, GroundTruthMeeting
from backend.app.evaluation.benchmark_dataset import BENCHMARK_DATASET
from backend.app.evaluation.metrics_calculator import MetricsCalculator
from backend.app.evaluation.baselines import (
    HeuristicRuleBaseline,
    UnstructuredLLMBaseline,
    ProposedAgentSystem,
    SystemPrediction
)
from backend.app.evaluation.evaluation_engine import EvaluationEngine

client = TestClient(app)

# =========================================================================
# 1. Dataset Integrity & Zero-Fabrication Checks
# =========================================================================

def test_benchmark_dataset_integrity():
    """Verify that the golden benchmark dataset has sufficient diverse academic emails,
    valid schemas, and genuine grounded text spans.
    """
    assert len(BENCHMARK_DATASET) >= 10, "Benchmark dataset must contain at least 10 annotated emails"

    valid_priorities = {"HIGH", "MEDIUM", "LOW"}

    for email in BENCHMARK_DATASET:
        assert email.id.startswith("BENCH-"), f"Invalid ID format: {email.id}"
        assert "@" in email.sender, f"Invalid sender email: {email.sender}"
        assert email.subject.strip(), f"Empty subject in {email.id}"
        assert email.body.strip(), f"Empty body in {email.id}"
        assert email.expected_priority in valid_priorities, f"Invalid priority: {email.expected_priority}"
        assert email.expected_summary.strip(), f"Empty expected summary in {email.id}"

        # Grounded spans verification: Every annotated grounded span MUST actually appear in text
        full_text = f"{email.subject} {email.body}".lower()
        for span in email.grounded_spans:
            assert span.lower() in full_text, (
                f"Grounded span '{span}' was not found in raw text of email {email.id}"
            )

# =========================================================================
# 2. Standalone Metrics Calculator Tests
# =========================================================================

def test_rouge_metric_calculation_identical():
    """ROUGE scores on identical text must yield F1 = 1.0."""
    text = "The Faculty Senate meeting will be held on Friday in Room 101."
    r1 = MetricsCalculator.compute_rouge_1(text, text)
    r2 = MetricsCalculator.compute_rouge_2(text, text)
    rl = MetricsCalculator.compute_rouge_l(text, text)

    assert r1["f1"] == 1.0
    assert r2["f1"] == 1.0
    assert rl["f1"] == 1.0

def test_rouge_metric_calculation_disjoint():
    """ROUGE scores on completely disjoint text must yield F1 = 0.0."""
    text_a = "apples oranges bananas grapes"
    text_b = "computers networks databases algorithms"
    r1 = MetricsCalculator.compute_rouge_1(text_a, text_b)
    r2 = MetricsCalculator.compute_rouge_2(text_a, text_b)
    rl = MetricsCalculator.compute_rouge_l(text_a, text_b)

    assert r1["f1"] == 0.0
    assert r2["f1"] == 0.0
    assert rl["f1"] == 0.0

def test_rouge_partial_overlap():
    """Verify precision, recall, and harmonic mean math on known overlap."""
    pred = "faculty meeting postponed until friday"
    ref = "the faculty meeting is postponed"
    r1 = MetricsCalculator.compute_rouge_1(pred, ref)
    
    # Overlapping tokens: 'faculty', 'meeting', 'postponed' (3 tokens)
    # Pred tokens: 5 ('faculty', 'meeting', 'postponed', 'until', 'friday')
    # Ref tokens: 5 ('the', 'faculty', 'meeting', 'is', 'postponed')
    assert r1["precision"] == 0.6  # 3/5
    assert r1["recall"] == 0.6     # 3/5
    assert r1["f1"] == 0.6

def test_word_jaccard_and_compression():
    """Test token Jaccard similarity and summary compression ratio."""
    src = "one two three four five six seven eight nine ten"
    summary = "one two three"
    jaccard = MetricsCalculator.compute_word_jaccard(src, summary)
    comp = MetricsCalculator.compute_compression_ratio(summary, src)

    assert jaccard == 0.3  # 3 intersection / 10 union
    assert comp == 0.3     # 3 / 10 tokens

def test_classification_metrics_math():
    """Verify multiclass accuracy and Macro F1 calculations."""
    preds = ["Academic", "Examination", "Research", "Administrative"]
    refs = ["Academic", "Examination", "Research", "Administrative"]
    perfect = MetricsCalculator.compute_classification_metrics(preds, refs)
    assert perfect["accuracy"] == 1.0
    assert perfect["macro_f1"] == 1.0

    imperfect_preds = ["Academic", "Research", "Research", "General"]
    imperfect = MetricsCalculator.compute_classification_metrics(imperfect_preds, refs)
    assert imperfect["accuracy"] == 0.5  # 2 of 4 correct

def test_priority_metrics_directional_penalty():
    """Verify asymmetric directional penalty: underestimating HIGH as LOW is heavily penalized."""
    # Case A: Critical underestimation (HIGH -> LOW)
    underestimation = MetricsCalculator.compute_priority_metrics(["LOW"], ["HIGH"])
    # Case B: Overestimation (LOW -> HIGH)
    overestimation = MetricsCalculator.compute_priority_metrics(["HIGH"], ["LOW"])

    assert underestimation["exact_tier_accuracy"] == 0.0
    assert overestimation["exact_tier_accuracy"] == 0.0
    # The penalty for missing a HIGH priority email must be strictly greater than false alarm
    assert underestimation["directional_penalty"] > overestimation["directional_penalty"]
    assert underestimation["high_priority_recall"] == 0.0

def test_deadline_metrics():
    """Test strict exact-match deadline (+- 0 days) evaluation."""
    preds = ["2026-09-25", "2026-09-18", None, "2026-10-01"]
    refs = ["2026-09-25", "2026-09-19", None, "2026-10-01"]
    res = MetricsCalculator.compute_deadline_metrics(preds, refs)
    assert res["exact_match_accuracy"] == 0.75  # 3 out of 4 match exact date or absence

def test_grounding_verification_metrics():
    """Test evidence grounding verification against raw email text."""
    from backend.app.schemas.ai_schema import AIEvidenceOutput
    raw_email = "The mandatory syndicate meeting is scheduled on October 12 in the Senate Hall."

    verified_ev = [
        AIEvidenceOutput(
            field_name="meeting",
            extracted_value="Senate Hall",
            source_text="Senate Hall",
            validation_status="VERIFIED"
        ),
        AIEvidenceOutput(
            field_name="deadline",
            extracted_value="October 12",
            source_text="October 12",
            validation_status="VERIFIED"
        )
    ]
    grounding = MetricsCalculator.compute_grounding_metrics([verified_ev], [raw_email])
    assert grounding["grounding_verification_rate"] == 1.0
    assert grounding["unsupported_assertion_rate"] == 0.0

    # Hallucinated evidence test
    hallucinated_ev = [
        AIEvidenceOutput(
            field_name="action",
            extracted_value="Submit tax forms",
            source_text="tax forms by midnight",  # Not in raw_email
            validation_status="UNVERIFIED"
        )
    ]
    hallucinated_res = MetricsCalculator.compute_grounding_metrics([hallucinated_ev], [raw_email])
    assert hallucinated_res["grounding_verification_rate"] == 0.0
    assert hallucinated_res["unsupported_assertion_rate"] == 1.0

# =========================================================================
# 3. Baseline Systems Execution Tests
# =========================================================================

def test_heuristic_rule_baseline_execution():
    """Verify HeuristicRuleBaseline runs deterministically on benchmark sample."""
    baseline = HeuristicRuleBaseline()
    sample = BENCHMARK_DATASET[0]
    pred = baseline.predict(sample)

    assert isinstance(pred, SystemPrediction)
    assert pred.category in ["Examination", "Academic", "Administrative", "Research", "Placement", "General Notice", "General"]
    assert pred.priority in ["HIGH", "MEDIUM", "LOW"]
    assert isinstance(pred.summary, str) and len(pred.summary) > 0

def test_unstructured_llm_baseline_execution():
    """Verify UnstructuredLLMBaseline runs deterministically on benchmark sample."""
    baseline = UnstructuredLLMBaseline()
    sample = BENCHMARK_DATASET[1]
    pred = baseline.predict(sample)

    assert isinstance(pred, SystemPrediction)
    assert pred.priority in ["HIGH", "MEDIUM", "LOW"]
    assert len(pred.evidence) == 0  # Generic LLM outputs no structured span evidence

def test_proposed_agent_system_execution():
    """Verify ProposedAgentSystem executes the multi-agent orchestrator with full grounding."""
    system = ProposedAgentSystem()
    sample = BENCHMARK_DATASET[0]  # Examination email
    pred = system.predict(sample)

    assert isinstance(pred, SystemPrediction)
    assert pred.priority == "HIGH"
    assert pred.deadline == "2026-09-25"
    assert len(pred.action_items) > 0
    assert len(pred.evidence) > 0  # Multi-agent system produces verified evidence spans

# =========================================================================
# 4. Evaluation Engine Tests & Zero-Fabrication Verification
# =========================================================================

def test_evaluation_engine_benchmark_run():
    """Run full evaluation engine and verify empirical computations and deltas."""
    engine = EvaluationEngine()
    report = engine.run_benchmark()

    assert report.sample_count == len(BENCHMARK_DATASET)
    assert len(report.systems_evaluated) == 3

    # Empirical Results validation
    results = report.empirical_results
    assert "heuristic_baseline" in results
    assert "unstructured_baseline" in results
    assert "proposed_agent_system" in results

    proposed = results["proposed_agent_system"]
    heuristic = results["heuristic_baseline"]

    # Strict assertion: Proposed Multi-Agent System MUST outperform Heuristic on Grounding
    assert proposed["grounding_verification_rate"] > heuristic["grounding_verification_rate"]
    assert proposed["grounding_verification_rate"] >= 0.85
    assert heuristic["grounding_verification_rate"] == 0.0

    # Directional error penalty should be lower (better) or equal in proposed system
    assert proposed["directional_error_penalty"] <= heuristic["directional_error_penalty"]

    # Improvement deltas should be calculated accurately
    deltas = report.improvement_deltas
    assert "delta_vs_heuristic" in deltas
    assert "delta_vs_unstructured" in deltas

def test_experimental_metrics_demarcated_and_unfabricated():
    """Verify that metrics requiring human trials are strictly marked 'REQUIRES_EXPERIMENTAL_DATA'."""
    engine = EvaluationEngine()
    catalog = engine.get_experimental_metrics_catalog()

    assert len(catalog) >= 5, "Must catalog at least 5 experimental metrics"
    
    for metric in catalog:
        assert metric.status == "REQUIRES_EXPERIMENTAL_DATA"
        assert metric.id.startswith("EXP-")
        assert metric.name.strip()
        assert metric.measurement_unit.strip()
        assert metric.target_hypothesis.strip()
        assert metric.data_source_required.strip()
        # Protocol details check
        assert "design" in metric.experimental_protocol
        assert "statistical_test" in metric.experimental_protocol

# =========================================================================
# 5. REST API Endpoint Tests
# =========================================================================

def test_api_evaluation_benchmark_endpoint():
    """Verify GET /api/evaluation/benchmark returns 200 with full evaluation telemetry."""
    response = client.get("/api/evaluation/benchmark")
    assert response.status_code == 200
    data = response.json()

    assert data["sample_count"] == len(BENCHMARK_DATASET)
    assert "empirical_results" in data
    assert "improvement_deltas" in data
    assert "experimental_metrics" in data
    assert "zero_fabrication_attestation" in data
    assert len(data["experimental_metrics"]) >= 5

def test_api_evaluation_catalog_endpoint():
    """Verify GET /api/evaluation/metrics/catalog distinguishes empirical vs experimental."""
    response = client.get("/api/evaluation/metrics/catalog")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "computable_empirical_metrics" in data
    assert "experimental_metrics" in data
    assert len(data["computable_empirical_metrics"]) >= 5

def test_api_evaluation_dataset_endpoint():
    """Verify GET /api/evaluation/dataset returns dataset distribution and metadata."""
    response = client.get("/api/evaluation/dataset")
    assert response.status_code == 200
    data = response.json()

    assert data["sample_count"] == len(BENCHMARK_DATASET)
    assert "summary" in data
    assert "emails" in data
    assert len(data["emails"]) == len(BENCHMARK_DATASET)
