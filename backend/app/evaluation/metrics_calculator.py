import re
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import Counter

class MetricsCalculator:
    """Pure-Python, dependency-free metrics calculator for Natural Language Processing,
    Structured Information Extraction, Priority Alignment, and Grounding Verification.
    """

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Normalize and tokenize text into words, stripping punctuation."""
        if not text:
            return []
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return [w for w in cleaned.split() if w]

    @staticmethod
    def _get_ngrams(tokens: List[str], n: int) -> Counter:
        """Extract n-gram multiset counter from token sequence."""
        if len(tokens) < n or n < 1:
            return Counter()
        return Counter(tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1))

    # =========================================================================
    # 1. Summarization Metrics (ROUGE-1, ROUGE-2, ROUGE-L, Compression)
    # =========================================================================

    @classmethod
    def compute_rouge_n(cls, pred_text: str, ref_text: str, n: int = 1) -> Dict[str, float]:
        """Compute ROUGE-N (unigram / bigram overlap) Precision, Recall, and F1."""
        pred_tokens = cls._tokenize(pred_text)
        ref_tokens = cls._tokenize(ref_text)

        if not pred_tokens or not ref_tokens:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

        pred_ngrams = cls._get_ngrams(pred_tokens, n)
        ref_ngrams = cls._get_ngrams(ref_tokens, n)

        overlap_count = sum((pred_ngrams & ref_ngrams).values())
        total_pred = sum(pred_ngrams.values())
        total_ref = sum(ref_ngrams.values())

        if total_pred == 0 or total_ref == 0:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

        precision = overlap_count / total_pred
        recall = overlap_count / total_ref

        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4)
        }

    @classmethod
    def compute_rouge_1(cls, pred_text: str, ref_text: str) -> Dict[str, float]:
        """ROUGE-1 (Unigram) Overlap."""
        return cls.compute_rouge_n(pred_text, ref_text, n=1)

    @classmethod
    def compute_rouge_2(cls, pred_text: str, ref_text: str) -> Dict[str, float]:
        """ROUGE-2 (Bigram) Overlap."""
        return cls.compute_rouge_n(pred_text, ref_text, n=2)

    @classmethod
    def compute_rouge_l(cls, pred_text: str, ref_text: str) -> Dict[str, float]:
        """Compute ROUGE-L based on Longest Common Subsequence (LCS)."""
        pred_tokens = cls._tokenize(pred_text)
        ref_tokens = cls._tokenize(ref_text)

        m = len(ref_tokens)
        n = len(pred_tokens)

        if m == 0 or n == 0:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

        # Dynamic Programming table for LCS length
        # Space-optimized 2-row DP
        prev = [0] * (n + 1)
        curr = [0] * (n + 1)

        for i in range(1, m + 1):
            ref_word = ref_tokens[i - 1]
            for j in range(1, n + 1):
                if ref_word == pred_tokens[j - 1]:
                    curr[j] = prev[j - 1] + 1
                else:
                    curr[j] = max(prev[j], curr[j - 1])
            prev = list(curr)

        lcs_length = prev[n]

        recall = lcs_length / m if m > 0 else 0.0
        precision = lcs_length / n if n > 0 else 0.0

        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4)
        }

    @classmethod
    def compute_word_jaccard(cls, text_a: str, text_b: str) -> float:
        """Compute Word-level Jaccard similarity index."""
        set_a = set(cls._tokenize(text_a))
        set_b = set(cls._tokenize(text_b))
        if not set_a and not set_b:
            return 1.0
        if not set_a or not set_b:
            return 0.0
        return round(len(set_a & set_b) / len(set_a | set_b), 4)

    @classmethod
    def compute_compression_ratio(cls, summary: str, source: str) -> float:
        """Calculate token-based compression ratio: len(summary) / len(source)."""
        sum_tokens = len(cls._tokenize(summary))
        src_tokens = len(cls._tokenize(source))
        if src_tokens == 0:
            return 0.0
        return round(sum_tokens / src_tokens, 4)

    # =========================================================================
    # 2. Classification Metrics (Accuracy, Macro-F1, Micro-F1)
    # =========================================================================

    @classmethod
    def compute_classification_metrics(
        cls,
        predictions: List[str],
        references: List[str]
    ) -> Dict[str, float]:
        """Compute multiclass Classification Accuracy, Macro-Precision, Macro-Recall, and Macro-F1."""
        if not references or len(predictions) != len(references):
            return {"accuracy": 0.0, "macro_precision": 0.0, "macro_recall": 0.0, "macro_f1": 0.0}

        total = len(references)
        correct = sum(1 for p, r in zip(predictions, references) if p.strip().lower() == r.strip().lower())
        accuracy = correct / total

        # Compute per-class statistics
        classes = sorted(list(set([r.strip().lower() for r in references] + [p.strip().lower() for p in predictions])))
        f1_list = []
        p_list = []
        r_list = []

        for c in classes:
            tp = sum(1 for p, r in zip(predictions, references) if p.strip().lower() == c and r.strip().lower() == c)
            fp = sum(1 for p, r in zip(predictions, references) if p.strip().lower() == c and r.strip().lower() != c)
            fn = sum(1 for p, r in zip(predictions, references) if p.strip().lower() != c and r.strip().lower() == c)

            prec = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if fn == 0 and tp == 0 else 0.0)
            rec = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if fp == 0 and tp == 0 else 0.0)
            f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

            p_list.append(prec)
            r_list.append(rec)
            f1_list.append(f1)

        macro_p = sum(p_list) / len(classes) if classes else 0.0
        macro_r = sum(r_list) / len(classes) if classes else 0.0
        macro_f1 = sum(f1_list) / len(classes) if classes else 0.0

        return {
            "accuracy": round(accuracy, 4),
            "macro_precision": round(macro_p, 4),
            "macro_recall": round(macro_r, 4),
            "macro_f1": round(macro_f1, 4)
        }

    # =========================================================================
    # 3. Priority Alignment Metrics (Ordinal Distance, Directional Penalty)
    # =========================================================================

    PRIORITY_LEVELS = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}

    @classmethod
    def compute_priority_metrics(
        cls,
        predictions: List[str],
        references: List[str]
    ) -> Dict[str, float]:
        """Compute faculty-specific Priority Alignment metrics:
        - exact_tier_accuracy: fraction of identical priority predictions
        - average_priority_distance: mean ordinal difference (|pred - ref|)
        - directional_error_penalty: weighted asymmetric penalty (HIGH->LOW is penalized 2.0x, HIGH->MED 1.0x)
        - high_priority_recall: recall specifically for critical HIGH tier items
        """
        if not references or len(predictions) != len(references):
            return {
                "exact_tier_accuracy": 0.0,
                "average_priority_distance": 0.0,
                "directional_penalty": 0.0,
                "high_priority_recall": 0.0
            }

        n = len(references)
        exact_matches = 0
        total_distance = 0.0
        total_penalty = 0.0

        high_tp = 0
        high_fn = 0

        for p_str, r_str in zip(predictions, references):
            p = p_str.strip().upper()
            r = r_str.strip().upper()

            p_val = cls.PRIORITY_LEVELS.get(p, 1)
            r_val = cls.PRIORITY_LEVELS.get(r, 1)

            diff = abs(p_val - r_val)
            total_distance += diff

            if p == r:
                exact_matches += 1

            # High priority recall check
            if r == "HIGH":
                if p == "HIGH":
                    high_tp += 1
                else:
                    high_fn += 1

            # Directional Penalty Calculation:
            # Underestimating urgency is catastrophic for faculty (missing exam/audit deadlines)
            if r == "HIGH" and p == "LOW":
                total_penalty += 2.0  # Critical miss
            elif r == "HIGH" and p == "MEDIUM":
                total_penalty += 1.0  # Moderate miss
            elif r == "MEDIUM" and p == "LOW":
                total_penalty += 0.8  # Minor miss
            elif p_val > r_val:
                # Over-caution (marking LOW as HIGH) is less damaging
                total_penalty += 0.3 * (p_val - r_val)

        exact_acc = exact_matches / n
        avg_dist = total_distance / n
        avg_penalty = total_penalty / n
        high_recall = high_tp / (high_tp + high_fn) if (high_tp + high_fn) > 0 else 1.0

        return {
            "exact_tier_accuracy": round(exact_acc, 4),
            "average_priority_distance": round(avg_dist, 4),
            "directional_penalty": round(avg_penalty, 4),
            "high_priority_recall": round(high_recall, 4)
        }

    # =========================================================================
    # 4. Information Extraction Metrics (Deadlines, Meetings, Actions)
    # =========================================================================

    @classmethod
    def compute_deadline_metrics(
        cls,
        predictions: List[Optional[str]],
        references: List[Optional[str]]
    ) -> Dict[str, float]:
        """Compute strict exact-match accuracy (+- 0 days) and presence F1 for deadlines."""
        if not references or len(predictions) != len(references):
            return {"exact_match_accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}

        n = len(references)
        exact_matches = 0
        tp = 0
        fp = 0
        fn = 0

        for p, r in zip(predictions, references):
            p_norm = p.strip()[:10] if p else None
            r_norm = r.strip()[:10] if r else None

            if p_norm == r_norm:
                exact_matches += 1

            if p_norm and r_norm:
                if p_norm == r_norm:
                    tp += 1
                else:
                    # Predicted a deadline, but wrong date
                    fp += 1
                    fn += 1
            elif p_norm and not r_norm:
                fp += 1
            elif not p_norm and r_norm:
                fn += 1

        acc = exact_matches / n
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        return {
            "exact_match_accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4)
        }

    @classmethod
    def compute_meeting_metrics(
        cls,
        predicted_meetings: List[Any],
        reference_meetings: List[Any]
    ) -> Dict[str, float]:
        """Compute meeting detection accuracy, date accuracy, time accuracy, and location accuracy."""
        n = len(reference_meetings)
        if n == 0 or len(predicted_meetings) != n:
            return {"detection_accuracy": 0.0, "slot_match_accuracy": 0.0}

        detection_correct = 0
        slot_correct = 0

        for p_meet, r_meet in zip(predicted_meetings, reference_meetings):
            has_p = p_meet is not None and getattr(p_meet, "title", None) is not None
            has_r = r_meet is not None

            if has_p == has_r:
                detection_correct += 1

            if has_p and has_r:
                p_date = (getattr(p_meet, "date", "") or "").strip()[:10]
                r_date = (getattr(r_meet, "date", "") or "").strip()[:10]
                # Check date match
                date_match = (p_date == r_date) if (p_date and r_date) else True
                if date_match:
                    slot_correct += 1
            elif not has_p and not has_r:
                slot_correct += 1

        return {
            "detection_accuracy": round(detection_correct / n, 4),
            "slot_match_accuracy": round(slot_correct / n, 4)
        }

    @classmethod
    def compute_action_metrics(
        cls,
        predicted_action_lists: List[List[str]],
        reference_action_lists: List[List[str]]
    ) -> Dict[str, float]:
        """Compute action item extraction precision, recall, and token Jaccard overlap."""
        n = len(reference_action_lists)
        if n == 0 or len(predicted_action_lists) != n:
            return {"action_presence_accuracy": 0.0, "average_jaccard": 0.0}

        presence_correct = 0
        jaccard_scores = []

        for p_list, r_list in zip(predicted_action_lists, reference_action_lists):
            has_p = len(p_list) > 0
            has_r = len(r_list) > 0

            if has_p == has_r:
                presence_correct += 1

            p_joined = " ".join(p_list)
            r_joined = " ".join(r_list)
            jaccard_scores.append(cls.compute_word_jaccard(p_joined, r_joined))

        avg_jaccard = sum(jaccard_scores) / n if n > 0 else 0.0

        return {
            "action_presence_accuracy": round(presence_correct / n, 4),
            "average_jaccard": round(avg_jaccard, 4)
        }

    # =========================================================================
    # 5. Evidence Grounding Metrics (Verification Rate, Unsupported Assertion)
    # =========================================================================

    @classmethod
    def compute_grounding_metrics(
        cls,
        evidence_lists: List[List[Any]],
        raw_email_texts: List[str]
    ) -> Dict[str, float]:
        """Compute Grounding Verification Rate: percentage of extracted claims verified
        against original source text, and Unsupported Assertion Rate.
        """
        total_evidences = 0
        verified_evidences = 0

        for ev_list, raw_text in zip(evidence_lists, raw_email_texts):
            raw_clean = raw_text.lower()
            for ev in ev_list:
                total_evidences += 1
                source_span = getattr(ev, "source_text", "") or ""
                val_status = getattr(ev, "validation_status", "") or ""
                # A verified evidence must have non-empty source text present in raw text
                if (val_status == "VERIFIED" or val_status == "CONFIRMED") and source_span.strip():
                    if source_span.strip().lower() in raw_clean:
                        verified_evidences += 1
                elif source_span.strip() and source_span.strip().lower() in raw_clean:
                    verified_evidences += 1

        if total_evidences == 0:
            return {
                "grounding_verification_rate": 0.0,
                "unsupported_assertion_rate": 1.0,
                "total_claims_evaluated": 0
            }

        verification_rate = verified_evidences / total_evidences
        unsupported_rate = 1.0 - verification_rate

        return {
            "grounding_verification_rate": round(verification_rate, 4),
            "unsupported_assertion_rate": round(unsupported_rate, 4),
            "total_claims_evaluated": total_evidences
        }
