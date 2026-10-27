import concurrent.futures
import re
import time
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from services.citations import extract_citations
from services.llm_providers import get_llm_provider
from services.rag_service import rag_service
from services.retrieval_service import retrieval_service
from services.verification_service import verification_service

STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "of", "to", "for", "is", "are", "was", "were",
    "be", "been", "being", "with", "as", "by", "at", "from", "that", "this", "it", "on",
}

_CITATION_TAG = re.compile(r"\[\s*S\s*\d+(?:\s*[,;]\s*S?\s*\d+)*\s*\]", re.IGNORECASE)


class MultiModelVerificationService:
    """
    Multi-model verification: retrieve ONCE, send the SAME citation-anchored prompt to several providers in
    parallel, then compare the answers (text overlap + which sources each model cited).
    """

    def __init__(self):
        self.retrieval_service = retrieval_service
        self.rag_service = rag_service
        self.verification_service = verification_service

    # ------------------------------------------------------------------ helpers
    def extract_legal_references(self, text: str) -> List[str]:
        """Sections, rules, notifications and circulars named in free text (kept for the UI/legacy use)."""
        if not text:
            return []
        patterns = [
            r"\bSection\s+\d+[A-Za-z]?(?:\(\w+\))*",
            r"\bRule\s+\d+[A-Za-z]?(?:\(\w+\))*",
            r"\bNotification\s+(?:No\.?\s*)?\d+/\d+(?:-[A-Za-z]+)?",
            r"\bCircular\s+(?:No\.?\s*)?\d+/\d+(?:/\d+-[A-Za-z]+)?",
            r"\bCGST\s+Act\b",
            r"\bIGST\s+Act\b",
        ]
        found = set()
        for p in patterns:
            for m in re.findall(p, text, flags=re.IGNORECASE):
                found.add(m.strip())
        return sorted(found)

    def compute_jaccard_similarity(self, text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0

        def tokens(t: str) -> set:
            t = _CITATION_TAG.sub(" ", t)
            cleaned = re.sub(r"[^\w\s]", " ", t.lower())
            return {w for w in cleaned.split() if w not in STOPWORDS and len(w) > 1}

        a, b = tokens(text1), tokens(text2)
        if not a or not b:
            return 0.0
        return round(len(a & b) / len(a | b), 4)

    @staticmethod
    def _set_jaccard(a: set, b: set) -> float:
        if not a and not b:
            return 0.0
        return round(len(a & b) / len(a | b), 4)

    # --------------------------------------------------------------- comparison
    def compare_answers(self, model_results: List[dict]) -> dict:
        """
        Agreement from (a) Jaccard overlap of the answer text and (b) overlap of the sources each model cited.
        Sources cited by only some models are reported as 'conflicting_references' for information; they no
        longer block 'agreement' on their own.
        """
        successful = [m for m in model_results if m.get("success") and m.get("answer")]
        failed_count = len(model_results) - len(successful)
        if len(successful) < 2:
            return {
                "overall_status": "insufficient_models",
                "successful_provider_count": len(successful),
                "failed_provider_count": failed_count,
                "pairwise_similarity": {},
                "pairwise_citation_overlap": {},
                "shared_legal_references": [],
                "conflicting_references": [],
            }

        cited: Dict[str, set] = {m["provider"]: set(m.get("cited_sections") or []) for m in successful}
        pairwise_text: Dict[str, float] = {}
        pairwise_cite: Dict[str, float] = {}
        combined_values = []
        any_citations = any(cited.values())
        for i in range(len(successful)):
            for j in range(i + 1, len(successful)):
                a, b = successful[i], successful[j]
                key = f"{a['provider']}_vs_{b['provider']}"
                text_sim = self.compute_jaccard_similarity(a["answer"], b["answer"])
                cite_sim = self._set_jaccard(cited[a["provider"]], cited[b["provider"]])
                pairwise_text[key] = text_sim
                pairwise_cite[key] = cite_sim
                combined_values.append(0.5 * text_sim + 0.5 * cite_sim if any_citations else text_sim)

        avg = sum(combined_values) / len(combined_values) if combined_values else 0.0
        sets = list(cited.values())
        shared = set.intersection(*sets) if sets else set()
        union = set.union(*sets) if sets else set()
        conflicting = union - shared

        if avg >= 0.55:
            status = "agreement"
        elif avg >= 0.30:
            status = "partial_agreement"
        else:
            status = "disagreement"
        return {
            "overall_status": status,
            "successful_provider_count": len(successful),
            "failed_provider_count": failed_count,
            "pairwise_similarity": pairwise_text,
            "pairwise_citation_overlap": pairwise_cite,
            "shared_legal_references": sorted(shared),
            "conflicting_references": sorted(conflicting),
        }

    # -------------------------------------------------------------------- main
    def verify_question(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = None,
        financial_year: Optional[str] = None,
        as_of_date: Optional[str] = None,
        providers: Optional[List[str]] = None,
        vector_weight: Optional[float] = None,
        keyword_weight: Optional[float] = None,
    ) -> dict:
        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")
        clean_query = query.strip()

        requested = providers or ["gemini", "mistral", "grok", "ollama"]
        targets = list(dict.fromkeys([p.strip().lower() for p in requested if p and p.strip()]))
        if "anthropic" in targets and "claude" not in targets:
            targets[targets.index("anthropic")] = "claude"
        if "deepseek-r1" in targets and "deepseek" not in targets:
            targets[targets.index("deepseek-r1")] = "deepseek"

        # 1. retrieve once for all models
        retrieved_chunks = self.retrieval_service.search_hybrid_chunks(
            db=db,
            query=clean_query,
            top_k=top_k,
            financial_year=financial_year,
            as_of_date=as_of_date,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
        )
        evidence_status, best_score = self.rag_service.evaluate_evidence_quality(retrieved_chunks)

        # 2. refuse without any LLM call if the evidence is insufficient
        if evidence_status == "insufficient":
            signal = self.verification_service.compute_verification_signal(
                evidence_status="insufficient",
                best_score=0.0,
                overall_status="insufficient_models",
                successful_count=0,
                requested_count=0,
            )
            return {
                "query": clean_query,
                "evidence_status": "insufficient",
                "best_score": best_score,
                "retrieved_count": 0,
                "model_results": [],
                "comparison": {
                    "overall_status": "insufficient_models",
                    "successful_provider_count": 0,
                    "failed_provider_count": 0,
                    "pairwise_similarity": {},
                    "pairwise_citation_overlap": {},
                    "shared_legal_references": [],
                    "conflicting_references": [],
                },
                "verification": signal,
                "retrieved_chunks": [],
                "debug_retrieved": [
                    {"chunk_id": c.get("chunk_id"), "citation_label": c.get("citation_label"),
                     "score": c.get("similarity_score")}
                    for c in retrieved_chunks[:5]
                ],
            }

        # 3. identical prompt for every provider
        shared_prompt, sources = self.rag_service.build_grounded_prompt(
            retrieved_chunks, clean_query, evidence_status
        )

        def run_provider(name: str) -> dict:
            start = time.time()
            model_name = name
            try:
                provider = get_llm_provider(name)
                model_name = getattr(provider, "_model_name", name)
                if not provider.is_configured():
                    return {
                        "provider": name, "model": model_name, "success": False, "answer": None,
                        "error": f"{name.upper()} API key is not configured.",
                        "response_time": round(time.time() - start, 2),
                    }
                answer = provider.generate_response(shared_prompt)
                elapsed = round(time.time() - start, 2)
                cit = extract_citations(answer, sources)
                return {
                    "provider": name, "model": model_name, "success": True, "answer": answer, "error": None,
                    "response_time": elapsed,
                    "citations": cit["citations"],
                    "invalid_citations": cit["invalid_citations"],
                    "uncited_answer": cit["uncited_answer"],
                    "cited_sections": cit["cited_sections"],
                }
            except Exception as exc:
                return {
                    "provider": name, "model": model_name, "success": False, "answer": None,
                    "error": str(exc), "response_time": round(time.time() - start, 2),
                }

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(run_provider, p): p for p in targets}
            for fut in concurrent.futures.as_completed(futures):
                results.append(fut.result())
        ordered = [next(r for r in results if r["provider"] == p) for p in targets if any(r["provider"] == p for r in results)]

        comparison = self.compare_answers(ordered)
        signal = self.verification_service.compute_verification_signal(
            evidence_status=evidence_status,
            best_score=best_score,
            overall_status=comparison["overall_status"],
            successful_count=comparison["successful_provider_count"],
            requested_count=len(targets),
        )
        return {
            "query": clean_query,
            "evidence_status": evidence_status,
            "best_score": best_score,
            "retrieved_count": len(retrieved_chunks),
            "model_results": ordered,
            "comparison": comparison,
            "verification": signal,
            "retrieved_chunks": retrieved_chunks,
        }


multi_model_verification_service = MultiModelVerificationService()
