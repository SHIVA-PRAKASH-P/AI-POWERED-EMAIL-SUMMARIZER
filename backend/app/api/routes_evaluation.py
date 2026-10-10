import logging
from typing import Optional
from fastapi import APIRouter, Query

from backend.app.evaluation.evaluation_engine import EvaluationEngine, EvaluationReport
from backend.app.config import settings

logger = logging.getLogger("backend.api.evaluation")

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation & Benchmarking"])

# In-memory cache for benchmark execution results
_cached_report: Optional[EvaluationReport] = None

@router.get("/benchmark", response_model=EvaluationReport)
def get_evaluation_benchmark(
    refresh: bool = Query(
        default=False,
        description="Set to true to re-run full evaluation pipeline across all baselines"
    )
):
    """Retrieve comprehensive evaluation report comparing the Proposed Multi-Agent System
    against Heuristic and Unstructured LLM Baselines.
    
    In strict compliance with the Zero-Fabrication Policy:
    - All empirical metric numbers are calculated dynamically from the golden benchmark dataset.
    - Human-subject / longitudinal metrics are marked with status 'REQUIRES_EXPERIMENTAL_DATA'.
    """
    global _cached_report
    if _cached_report is None or refresh:
        logger.info("Executing comprehensive benchmark evaluation across all baselines...")
        engine = EvaluationEngine()
        _cached_report = engine.run_benchmark()
        logger.info("Benchmark evaluation completed successfully.")
    
    return _cached_report

@router.get("/metrics/catalog")
def get_metrics_catalog():
    """Retrieve the formal taxonomy of evaluation metrics, distinguishing between
    computable empirical metrics and metrics requiring experimental field data.
    """
    engine = EvaluationEngine()
    return {
        "status": "success",
        "stage": "STAGE 18 — EVALUATION FRAMEWORK",
        "computable_empirical_metrics": [
            {
                "name": "ROUGE-1, ROUGE-2, ROUGE-L F1",
                "category": "Summarization Quality",
                "description": "N-gram and Longest Common Subsequence overlap with human reference summaries."
            },
            {
                "name": "Category Accuracy & Macro F1",
                "category": "Categorization",
                "description": "Multiclass precision, recall, and harmonic mean across academic domains."
            },
            {
                "name": "Priority Tier Accuracy & Directional Penalty",
                "category": "Priority Alignment",
                "description": "Exact tier matching and asymmetric penalty weighting against urgent deadline misses."
            },
            {
                "name": "Deadline Exact Match Accuracy",
                "category": "Information Extraction",
                "description": "Strict day-exact (+- 0 days) temporal resolution and normalization."
            },
            {
                "name": "Meeting Slot Accuracy",
                "category": "Information Extraction",
                "description": "Joint tuple match on date, time, and venue components."
            },
            {
                "name": "Grounding Verification Rate",
                "category": "Evidence & Anti-Hallucination",
                "description": "Fraction of extracted assertions verified by verbatim text spans in the raw email."
            }
        ],
        "experimental_metrics": engine.get_experimental_metrics_catalog()
    }

@router.get("/dataset")
def get_benchmark_dataset():
    """Retrieve the golden benchmark dataset summary and metadata."""
    engine = EvaluationEngine()
    return {
        "summary": engine.get_dataset_summary(),
        "sample_count": len(engine.dataset),
        "emails": [
            {
                "id": e.id,
                "sender": e.sender,
                "subject": e.subject,
                "domain": e.domain,
                "difficulty": e.difficulty,
                "expected_category": e.expected_category,
                "expected_priority": e.expected_priority,
                "expected_deadline": e.expected_deadline,
                "has_meeting": e.expected_meeting is not None,
                "action_item_count": len(e.expected_actions),
                "grounded_span_count": len(e.grounded_spans)
            }
            for e in engine.dataset
        ]
    }
