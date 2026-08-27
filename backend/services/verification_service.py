from typing import Dict, Optional

# Centralized Configurable Scoring Constants
EVIDENCE_WEIGHT = 0.50
AGREEMENT_WEIGHT = 0.30
MODEL_COVERAGE_WEIGHT = 0.20

STRONG_EVIDENCE_THRESHOLD = 0.65
WEAK_EVIDENCE_THRESHOLD = 0.40

# Level Mapping Thresholds
HIGH_THRESHOLD = 0.75
MEDIUM_THRESHOLD = 0.50
LOW_THRESHOLD = 0.01


class VerificationService:
    """
    Production Verification Service for GST Sahayak.
    Calculates a transparent, deterministic verification_score (0.0 to 1.0) and
    verification_level (HIGH, MEDIUM, LOW, UNVERIFIED) using evidence quality,
    model agreement, and provider coverage, strictly applying safety override rules.
    
    NOTE: This is an engineering verification signal and NOT a legal accuracy or correctness probability.
    """

    def __init__(
        self,
        evidence_weight: float = EVIDENCE_WEIGHT,
        agreement_weight: float = AGREEMENT_WEIGHT,
        coverage_weight: float = MODEL_COVERAGE_WEIGHT
    ):
        self.evidence_weight = evidence_weight
        self.agreement_weight = agreement_weight
        self.coverage_weight = coverage_weight

    def compute_verification_signal(
        self,
        evidence_status: str,
        best_score: float,
        overall_status: str,
        successful_count: int,
        requested_count: int
    ) -> dict:
        """
        Calculates transparent verification score and applies safety override caps:
        - Rule 1: evidence_status == 'insufficient' -> UNVERIFIED (score = 0.0, 0 LLM calls)
        - Rule 2: successful_count == 0 -> UNVERIFIED (score = 0.0)
        - Rule 3: overall_status == 'disagreement' -> Capped at MEDIUM/LOW (never HIGH)
        - Rule 4: successful_count == 1 -> Capped at MEDIUM (never HIGH due to lack of multi-model cross-verification)
        - Rule 5: evidence_status == 'weak' -> Capped at MEDIUM/LOW (never HIGH)
        """
        # Rule 1 & Rule 2: Insufficient evidence or 0 successful providers -> UNVERIFIED
        if evidence_status == "insufficient":
            return {
                "verification_score": 0.0,
                "verification_level": "UNVERIFIED",
                "verification_status": "unverified",
                "explanation": "Insufficient supporting GST evidence found in the knowledge base. No model verification was performed.",
                "components": {
                    "evidence_component": 0.0,
                    "agreement_component": 0.0,
                    "model_coverage_component": 0.0
                }
            }
        elif successful_count == 0:
            return {
                "verification_score": 0.0,
                "verification_level": "UNVERIFIED",
                "verification_status": "unverified",
                "explanation": "Supporting GST evidence was retrieved, but all requested LLM providers failed or were unavailable to perform verification.",
                "components": {
                    "evidence_component": round(best_score, 4),
                    "agreement_component": 0.0,
                    "model_coverage_component": 0.0
                }
            }

        # A. Evidence Component (0.0 to 1.0)
        if evidence_status == "strong":
            evidence_comp = round(best_score, 4)
        elif evidence_status == "weak":
            evidence_comp = round(0.6 * best_score, 4)
        else:
            evidence_comp = 0.0

        # B. Agreement Component (0.0 to 1.0)
        if overall_status == "agreement":
            agreement_comp = 1.0
        elif overall_status == "partial_agreement":
            agreement_comp = 0.6
        elif overall_status == "insufficient_models":
            agreement_comp = 0.3
        elif overall_status == "disagreement":
            agreement_comp = 0.0
        else:
            agreement_comp = 0.3

        # C. Model Coverage Component (0.0 to 1.0)
        req_count = max(1, requested_count)
        coverage_comp = round(min(1.0, successful_count / req_count), 4)

        # Raw Weighted Verification Score
        raw_score = (
            (self.evidence_weight * evidence_comp) +
            (self.agreement_weight * agreement_comp) +
            (self.coverage_weight * coverage_comp)
        )
        final_score = round(max(0.0, min(1.0, raw_score)), 4)

        # Evaluate Initial Verification Level
        if final_score >= HIGH_THRESHOLD:
            level = "HIGH"
            status_tag = "strongly_supported"
            explanation = "Strong supporting GST evidence and agreement among available independent models."
        elif final_score >= MEDIUM_THRESHOLD:
            level = "MEDIUM"
            status_tag = "moderately_supported"
            explanation = "Relevant GST evidence was found, but model agreement or independent cross-verification is limited."
        elif final_score >= LOW_THRESHOLD:
            level = "LOW"
            status_tag = "limited_support"
            explanation = "GST evidence is weak or models produced conflicting legal references. Verify directly against cited sources."
        else:
            level = "UNVERIFIED"
            status_tag = "unverified"
            explanation = "Verification score fell below minimum thresholds."

        # Safety Override Rule 3: Disagreement Cap
        if overall_status == "disagreement" and level == "HIGH":
            level = "MEDIUM"
            status_tag = "moderately_supported"
            explanation = "Relevant GST evidence was found, but models produced conflicting legal references. Capped at MEDIUM."

        # Safety Override Rule 4: Single Model Cap (e.g. Standard RAG)
        if successful_count == 1 and level == "HIGH":
            level = "MEDIUM"
            status_tag = "moderately_supported"
            explanation = "Strong supporting GST evidence found, but only one LLM provider was evaluated. Multi-model verification is required for HIGH status."

        # Safety Override Rule 5: Weak Evidence Cap
        if evidence_status == "weak" and level == "HIGH":
            level = "MEDIUM"
            status_tag = "moderately_supported"
            explanation = "Retrieved GST evidence is weak or limited. Capped at MEDIUM status."

        return {
            "verification_score": final_score,
            "verification_level": level,
            "verification_status": status_tag,
            "explanation": explanation,
            "components": {
                "evidence_component": evidence_comp,
                "agreement_component": agreement_comp,
                "model_coverage_component": coverage_comp
            }
        }


# Global singleton instance
verification_service = VerificationService()
