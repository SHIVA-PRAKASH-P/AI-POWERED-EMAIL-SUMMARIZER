"""Evaluation Framework for AI Email Summarizer Agent.

Provides standalone metric calculation, curated golden benchmark datasets,
baseline implementations, and empirical vs experimental evaluation telemetry.
"""

from backend.app.evaluation.ground_truth_schema import GroundTruthEmail
from backend.app.evaluation.benchmark_dataset import BENCHMARK_DATASET
from backend.app.evaluation.metrics_calculator import MetricsCalculator
from backend.app.evaluation.baselines import (
    HeuristicRuleBaseline,
    UnstructuredLLMBaseline,
    ProposedAgentSystem
)
from backend.app.evaluation.evaluation_engine import EvaluationEngine

__all__ = [
    "GroundTruthEmail",
    "BENCHMARK_DATASET",
    "MetricsCalculator",
    "HeuristicRuleBaseline",
    "UnstructuredLLMBaseline",
    "ProposedAgentSystem",
    "EvaluationEngine"
]
