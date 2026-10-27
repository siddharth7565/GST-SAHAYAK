import logging
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from database.models import DocumentChunkModel, DocumentModel
from services.embedding_service import embedding_service
from services.query_expansion import query_expansion_service

logger = logging.getLogger(__name__)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


MAX_TOP_K = 20
DEFAULT_MIN_SIMILARITY = 0.20
DEFAULT_VECTOR_WEIGHT = 0.7
DEFAULT_KEYWORD_WEIGHT = 0.3

# Tunable through backend/.env
DEFAULT_TOP_K = _env_int("DEFAULT_TOP_K", 10)             # chunks sent to the model when the caller gives no top_k
SECTION_BOOST = _env_float("SECTION_BOOST", 0.25)        # bonus when the user names a section
HINT_BOOST_SCALE = _env_float("HINT_BOOST_SCALE", 0.4)   # fraction of that bonus for expansion hints
MAX_PER_SECTION = _env_int("MAX_PER_SECTION", 3)         # soft cap per (act, section) in the top-k
EXPANSION_DEFAULT = os.getenv("QUERY_EXPANSION", "true").lower() == "true"


# ---------------------------------------------------------------- label parsing
def parse_chunk_label(text: str) -> Dict[str, Optional[str]]:
    """Parse the label line the scraper puts first in every chunk, e.g.
    '[CGST Act 2017, Section 22(1), part 1/2 - Persons liable for registration]'."""
    result: Dict[str, Optional[str]] = {
        "act": None, "section": None, "sub": None, "title": None, "citation_label": None, "label": None,
    }
    if not text:
        return result
    first = text.lstrip().split("\n", 1)[0].strip()
    if not (first.startswith("[") and "]" in first):
        return result
    content = first[1:first.rfind("]")].strip()
    result["label"] = content
    m = re.match(r"^(.*?),\s*Section\s+(.*)$", content)
    if not m:
        return result
    result["act"] = m.group(1).strip()
    head, _, title = m.group(2).partition(" - ")
    result["title"] = title.strip() or None
    hm = re.match(r"(\d+[A-Za-z]?)(.*)$", head.strip())
    if not hm:
        return result
    result["section"] = hm.group(1)
    sm = re.match(r"\s*(\([^)]+\))(?:\s*-\s*(\([^)]+\)))?", hm.group(2))
    if sm:
        result["sub"] = sm.group(1) + (f"-{sm.group(2)}" if sm.group(2) else "")
    result["citation_label"] = f"{result['act']}, Section {result['section']}{result['sub'] or ''}"
    return result


# ------------------------------------------------------------ section mentions
_SECTION_MENTION = re.compile(
    r"\b(?:sections?|sec\.?|s\.)\s*(\d{1,3}[A-Za-z]?)((?:\s*\(\s*\w+\s*\))*)", re.IGNORECASE
)


def extract_section_mentions(query: str) -> Dict:
    """Explicit mentions only ('section 16', 'sec 22(1)', 's. 24', 'CGST section 16').
    A bare number (e.g. '15 lakh') is never treated as a section. A bare 'Section 2' is ignored
    because it would boost every definition; 'Section 2(6)' is fine."""
    q = query or ""
    has_c = re.search(r"\bcgst\b", q, re.IGNORECASE) is not None
    has_i = re.search(r"\bigst\b", q, re.IGNORECASE) is not None
    act = "CGST Act 2017" if (has_c and not has_i) else "IGST Act 2017" if (has_i and not has_c) else None
    mentions: List[Tuple[str, Optional[str]]] = []
    for m in _SECTION_MENTION.finditer(q):
        section = m.group(1)
        subs = re.findall(r"\(\s*(\w+)\s*\)", m.group(2) or "")
        sub = subs[0] if subs else None
        if section == "2" and sub is None:
            continue
        mentions.append((section, sub))
    return {"act": act, "mentions": mentions}


def _sub_matches(label_sub: Optional[str], wanted: str) -> bool:
    if not label_sub:
        return False
    nums = [n.lower() for n in re.findall(r"\(\s*(\w+)\s*\)", label_sub)]
    w = wanted.lower()
    if w in nums:
        return True
    if len(nums) == 2 and nums[0].isdigit() and nums[1].isdigit() and w.isdigit():
        return int(nums[0]) <= int(w) <= int(nums[1])
    return False


def _boost_for(label_info: Dict, mentions: Dict, boost: float) -> float:
    if boost <= 0 or not mentions["mentions"] or not label_info.get("section"):
        return 0.0
    if mentions["act"] and label_info.get("act") != mentions["act"]:
        return 0.0
    for section, sub in mentions["mentions"]:
        if label_info["section"].lower() == section.lower():
            if sub is None or _sub_matches(label_info.get("sub"), sub):
                return boost
    return 0.0


_STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "of", "to", "for", "is", "are", "was", "were", "be", "been", "being",
    "with", "as", "by", "at", "from", "that", "this", "it", "on", "do", "does", "did", "can", "i", "my", "me",
    "what", "which", "who", "how", "when", "where", "need", "any", "have", "has", "per", "year",
}


class RetrievalService:
    """
    Hybrid retrieval (dense vectors + PostgreSQL full-text) for GST Sahayak, with:
    - vector search that scores every chunk when the column is a plain float array (no pgvector type),
    - OR-style keyword search, ts_rank_cd normalised to [0, 1),
    - an explicit "Section N" boost, plus softer boosts from query-expansion hints,
    - query expansion (freelancer wording -> statutory wording), merged by best score,
    - a soft per-section cap so one long section cannot fill the whole top-k.
    """

    def __init__(
        self,
        default_top_k: int = DEFAULT_TOP_K,
        max_top_k: int = MAX_TOP_K,
        default_min_similarity: float = DEFAULT_MIN_SIMILARITY,
        vector_weight: float = DEFAULT_VECTOR_WEIGHT,
        keyword_weight: float = DEFAULT_KEYWORD_WEIGHT,
    ):
        self.default_top_k = default_top_k
        self.max_top_k = max_top_k
        self.default_min_similarity = default_min_similarity
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    # ------------------------------------------------------------------ filters
    def _apply_filters(self, query_obj, clean_fy: Optional[str], clean_as_of_date: Optional[str]):
        query_obj = query_obj.filter(DocumentModel.status == "READY")
        if clean_fy:
            query_obj = query_obj.filter(
                or_(DocumentModel.financial_year.is_(None), DocumentModel.financial_year == clean_fy)
            )
        if clean_as_of_date:
            query_obj = query_obj.filter(
                and_(
                    or_(DocumentModel.effective_from.is_(None), DocumentModel.effective_from <= clean_as_of_date),
                    or_(DocumentModel.effective_to.is_(None), DocumentModel.effective_to >= clean_as_of_date),
                )
            )
        return query_obj

    # ---------------------------------------------------------- one query search
    def _candidates(
        self,
        db: Session,
        query: str,
        k: int,
        threshold: float,
        clean_fy: Optional[str],
        clean_as_of_date: Optional[str],
        vw: float,
        kw_w: float,
        boost: float,
    ) -> List[dict]:
        """Score one query string; return all results above the threshold, best first (no cap)."""
        candidate_limit = max(k * 5, 50)
        mentions = extract_section_mentions(query)

        # ---- dense vector search
        query_vector = embedding_service.embed_text(query)
        use_pgvector = hasattr(DocumentChunkModel.embedding, "cosine_distance")
        mode = "pgvector" if use_pgvector else "python-fallback"
        if use_pgvector:
            distance_expr = DocumentChunkModel.embedding.cosine_distance(query_vector)
            vec_q = (
                db.query(DocumentChunkModel, DocumentModel, distance_expr.label("distance"))
                .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
            )
            vec_q = self._apply_filters(vec_q, clean_fy, clean_as_of_date)
            vec_rows = vec_q.order_by(distance_expr.asc()).limit(candidate_limit).all()
        else:
            vec_q = (
                db.query(DocumentChunkModel, DocumentModel)
                .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
            )
            vec_q = self._apply_filters(vec_q, clean_fy, clean_as_of_date)
            vec_rows = []
            for chunk, doc in vec_q.all():  # score EVERY chunk (the corpus is small); never LIMIT unordered rows
                if chunk.embedding:
                    sim = embedding_service.compute_cosine_similarity(query_vector, chunk.embedding)
                    vec_rows.append((chunk, doc, round(1.0 - sim, 4)))
            vec_rows.sort(key=lambda r: r[2])
            vec_rows = vec_rows[:candidate_limit]

        vector_candidates: Dict[str, Tuple] = {}
        for chunk, doc, dist in vec_rows:
            vector_candidates[chunk.chunk_id] = (chunk, doc, round(max(0.0, 1.0 - float(dist)), 4))

        # ---- keyword search (OR of the meaningful words)
        words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 2 and w not in _STOPWORDS]
        words = list(dict.fromkeys(words))
        ts_vector = func.to_tsvector("english", DocumentChunkModel.text)
        if words:
            ts_query = func.to_tsquery("english", " | ".join(words))
        else:
            ts_query = func.plainto_tsquery("english", query)
        kw_rank = func.ts_rank_cd(ts_vector, ts_query, 32)  # 32 => rank / (rank + 1), bounded in [0, 1)
        kw_q = (
            db.query(DocumentChunkModel, DocumentModel, kw_rank.label("rank"))
            .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
        )
        kw_q = self._apply_filters(kw_q, clean_fy, clean_as_of_date)
        kw_q = kw_q.filter(ts_vector.op("@@")(ts_query))
        kw_rows = kw_q.order_by(kw_rank.desc()).limit(candidate_limit).all()
        keyword_candidates: Dict[str, Tuple] = {}
        for chunk, doc, rank_val in kw_rows:
            keyword_candidates[chunk.chunk_id] = (chunk, doc, round(float(rank_val or 0.0), 4))

        # ---- fuse
        results: List[dict] = []
        for cid in set(vector_candidates) | set(keyword_candidates):
            in_vec, in_kw = cid in vector_candidates, cid in keyword_candidates
            if in_vec:
                chunk, doc, v_score = vector_candidates[cid]
            else:
                chunk, doc, _ = keyword_candidates[cid]
                v_score = 0.0
            kw_score = keyword_candidates[cid][2] if in_kw else 0.0
            method = "hybrid" if (in_vec and in_kw) else ("vector_only" if in_vec else "keyword_only")
            base = round(vw * v_score + kw_w * kw_score, 4)

            info = parse_chunk_label(chunk.text)
            hybrid = round(min(1.0, base + _boost_for(info, mentions, boost)), 4)

            if max(v_score, hybrid) >= threshold:
                results.append({
                    "chunk_id": chunk.chunk_id,
                    "document_id": doc.id,
                    "document": doc.filename,
                    "title": doc.title,
                    "document_type": doc.document_type,
                    "source_url": doc.source_url,
                    "issuing_authority": doc.issuing_authority,
                    "publication_date": doc.publication_date,
                    "effective_from": doc.effective_from,
                    "effective_to": doc.effective_to,
                    "financial_year": doc.financial_year,
                    "page": chunk.page,
                    "text": chunk.text,
                    "similarity_score": hybrid,
                    "vector_score": v_score,
                    "keyword_score": kw_score,
                    "hybrid_score": hybrid,
                    "retrieval_method": method,
                    "retrieval_mode": mode,
                    "act": info["act"],
                    "section": info["section"],
                    "sub": info["sub"],
                    "citation_label": info["citation_label"],
                })
        results.sort(key=lambda r: r["hybrid_score"], reverse=True)
        return results

    # ------------------------------------------------------------- diversity cap
    @staticmethod
    def _diversify(results: List[dict], k: int, explicit: Dict) -> List[dict]:
        """Soft cap: at most MAX_PER_SECTION chunks per (act, section) on the first pass, except for
        sections the user named explicitly. Leftover slots are filled by score."""
        out, skipped = [], []
        counts: Dict[Tuple, int] = defaultdict(int)
        for r in results:
            if len(out) >= k:
                break
            key = (r.get("act") or "?", r.get("section") or "?")
            is_explicit = _boost_for(r, explicit, 1.0) > 0
            if is_explicit or counts[key] < MAX_PER_SECTION:
                out.append(r)
                counts[key] += 1
            else:
                skipped.append(r)
        for r in skipped:
            if len(out) >= k:
                break
            out.append(r)
        out.sort(key=lambda r: r["hybrid_score"], reverse=True)
        return out[:k]

    # ------------------------------------------------------------------ public
    def search_hybrid_chunks_with_trace(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
        financial_year: Optional[str] = None,
        as_of_date: Optional[str] = None,
        vector_weight: Optional[float] = None,
        keyword_weight: Optional[float] = None,
        enable_query_expansion: Optional[bool] = None,
    ) -> Tuple[List[dict], Dict]:
        """Same as search_hybrid_chunks but also returns {'queries_used': [...], 'retrieval_mode': ...}."""
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty.")
        clean_query = query.strip()

        k = top_k if top_k is not None else self.default_top_k
        if k < 1 or k > self.max_top_k:
            raise ValueError(f"top_k must be an integer between 1 and {self.max_top_k}.")
        threshold = min_similarity if min_similarity is not None else self.default_min_similarity
        vw = vector_weight if vector_weight is not None else self.vector_weight
        kw_w = keyword_weight if keyword_weight is not None else self.keyword_weight

        clean_as_of_date = None
        if as_of_date and as_of_date.strip():
            clean_as_of_date = as_of_date.strip()
            try:
                datetime.strptime(clean_as_of_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError(
                    f"Invalid as_of_date format '{as_of_date}'. Must be in YYYY-MM-DD format (e.g. 2025-04-01)."
                )
        clean_fy = financial_year.strip() if (financial_year and financial_year.strip()) else None

        use_expansion = EXPANSION_DEFAULT if enable_query_expansion is None else enable_query_expansion
        queries = [clean_query]
        if use_expansion:
            try:
                queries = query_expansion_service.expand_query(clean_query) or [clean_query]
            except Exception as exc:  # never let expansion break search
                logger.warning("[RETRIEVAL] query expansion failed: %s", exc)
                queries = [clean_query]

        merged: Dict[str, dict] = {}
        original_scores: Dict[str, float] = {}
        for i, q in enumerate(queries):
            boost = SECTION_BOOST * (1.0 if i == 0 else HINT_BOOST_SCALE)
            for r in self._candidates(db, q, k, threshold, clean_fy, clean_as_of_date, vw, kw_w, boost):
                if i == 0:
                    original_scores[r["chunk_id"]] = r["hybrid_score"]
                cur = merged.get(r["chunk_id"])
                if cur is None or r["hybrid_score"] > cur["hybrid_score"]:
                    merged[r["chunk_id"]] = r

        # hybrid_score = ranking score (best over the original question and the expansion sub-queries).
        # similarity_score = how well the chunk matches the user's ORIGINAL question (0.0 if it was only found
        # through an expansion sub-query). Sub-queries are written in the Acts' own words, so they match
        # chunks almost perfectly; the evidence guard must not be fooled by that, so it uses similarity_score.
        for cid, r in merged.items():
            r["similarity_score"] = original_scores.get(cid, 0.0)

        ranked = sorted(merged.values(), key=lambda r: r["hybrid_score"], reverse=True)
        final = self._diversify(ranked, k, extract_section_mentions(clean_query))
        mode = final[0]["retrieval_mode"] if final else (
            "pgvector" if hasattr(DocumentChunkModel.embedding, "cosine_distance") else "python-fallback"
        )
        return final, {"queries_used": queries, "retrieval_mode": mode}

    def search_hybrid_chunks(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
        financial_year: Optional[str] = None,
        as_of_date: Optional[str] = None,
        vector_weight: Optional[float] = None,
        keyword_weight: Optional[float] = None,
        enable_query_expansion: Optional[bool] = None,
    ) -> List[dict]:
        results, _ = self.search_hybrid_chunks_with_trace(
            db=db,
            query=query,
            top_k=top_k,
            min_similarity=min_similarity,
            financial_year=financial_year,
            as_of_date=as_of_date,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            enable_query_expansion=enable_query_expansion,
        )
        return results

    def search_similar_chunks(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
        financial_year: Optional[str] = None,
        as_of_date: Optional[str] = None,
    ) -> List[dict]:
        """Backward-compatible vector-only entry point (no expansion)."""
        return self.search_hybrid_chunks(
            db=db,
            query=query,
            top_k=top_k,
            min_similarity=min_similarity,
            financial_year=financial_year,
            as_of_date=as_of_date,
            vector_weight=1.0,
            keyword_weight=0.0,
            enable_query_expansion=False,
        )


# Global singleton RetrievalService instance
retrieval_service = RetrievalService()