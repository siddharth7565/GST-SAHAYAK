from typing import List, Optional, Dict, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, text
from database.models import DocumentModel, DocumentChunkModel
from services.embedding_service import embedding_service

DEFAULT_TOP_K = 5
MAX_TOP_K = 20
DEFAULT_MIN_SIMILARITY = 0.20
DEFAULT_VECTOR_WEIGHT = 0.7
DEFAULT_KEYWORD_WEIGHT = 0.3


class RetrievalService:
    """
    Production Hybrid Retrieval Service layer for GST Sahayak.
    Combines dense semantic vector search (pgvector cosine similarity)
    and sparse keyword search (PostgreSQL full-text TSVECTOR / TSQUERY ranking)
    with score normalization, weighted fusion, candidate deduplication, and
    SQL-level temporal/status filtering.
    """

    def __init__(
        self,
        default_top_k: int = DEFAULT_TOP_K,
        max_top_k: int = MAX_TOP_K,
        default_min_similarity: float = DEFAULT_MIN_SIMILARITY,
        vector_weight: float = DEFAULT_VECTOR_WEIGHT,
        keyword_weight: float = DEFAULT_KEYWORD_WEIGHT
    ):
        self.default_top_k = default_top_k
        self.max_top_k = max_top_k
        self.default_min_similarity = default_min_similarity
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    def _apply_filters(self, query_obj, clean_fy: Optional[str], clean_as_of_date: Optional[str]):
        """Helper to apply SQL status and temporal applicability filters consistently."""
        query_obj = query_obj.filter(DocumentModel.status == "READY")

        if clean_fy:
            query_obj = query_obj.filter(
                or_(
                    DocumentModel.financial_year.is_(None),
                    DocumentModel.financial_year == clean_fy
                )
            )

        if clean_as_of_date:
            query_obj = query_obj.filter(
                and_(
                    or_(
                        DocumentModel.effective_from.is_(None),
                        DocumentModel.effective_from <= clean_as_of_date
                    ),
                    or_(
                        DocumentModel.effective_to.is_(None),
                        DocumentModel.effective_to >= clean_as_of_date
                    )
                )
            )

        return query_obj

    def search_hybrid_chunks(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
        financial_year: Optional[str] = None,
        as_of_date: Optional[str] = None,
        vector_weight: Optional[float] = None,
        keyword_weight: Optional[float] = None
    ) -> List[dict]:
        """
        Executes hybrid search combining pgvector dense semantic search
        and PostgreSQL full-text keyword search:
        1. Validates query and temporal parameters.
        2. Retrieves candidate set 1 via pgvector cosine distance + temporal filters.
        3. Retrieves candidate set 2 via PostgreSQL to_tsvector / ts_rank_cd + temporal filters.
        4. Normalizes keyword rank scores using Min-Max scaling.
        5. Deduplicates candidates by chunk_id and computes combined hybrid score:
           S_hybrid = (vector_weight * v_score) + (keyword_weight * kw_norm_score)
        6. Returns top K ranked results with score breakdown and retrieval_method metadata.
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty.")

        clean_query = query.strip()

        k = top_k if top_k is not None else self.default_top_k
        if k < 1 or k > self.max_top_k:
            raise ValueError(f"top_k must be an integer between 1 and {self.max_top_k}.")

        threshold = min_similarity if min_similarity is not None else self.default_min_similarity
        vw = vector_weight if vector_weight is not None else self.vector_weight
        kw_w = keyword_weight if keyword_weight is not None else self.keyword_weight

        # Validate as_of_date format if provided
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

        candidate_limit = k * 3

        # ----------------------------------------------------
        # SEARCH METHOD 1: Dense Vector Similarity Search
        # ----------------------------------------------------
        query_vector = embedding_service.embed_text(clean_query)
        if hasattr(DocumentChunkModel.embedding, "cosine_distance"):
            distance_expr = DocumentChunkModel.embedding.cosine_distance(query_vector)
            vec_query_obj = (
                db.query(DocumentChunkModel, DocumentModel, distance_expr.label("distance"))
                .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
            )
            vec_query_obj = self._apply_filters(vec_query_obj, clean_fy, clean_as_of_date)
            vec_rows = vec_query_obj.order_by(distance_expr.asc()).limit(candidate_limit).all()
        else:
            vec_query_obj = (
                db.query(DocumentChunkModel, DocumentModel)
                .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
            )
            vec_query_obj = self._apply_filters(vec_query_obj, clean_fy, clean_as_of_date)
            all_chunks = vec_query_obj.limit(candidate_limit * 2).all()
            
            vec_rows = []
            for chunk, doc in all_chunks:
                if chunk.embedding:
                    sim = embedding_service.compute_cosine_similarity(query_vector, chunk.embedding)
                    dist = round(1.0 - sim, 4)
                    vec_rows.append((chunk, doc, dist))
            vec_rows.sort(key=lambda r: r[2])
            vec_rows = vec_rows[:candidate_limit]

        vector_candidates: Dict[str, Tuple[DocumentChunkModel, DocumentModel, float]] = {}
        for chunk, doc, dist in vec_rows:
            v_score = round(max(0.0, 1.0 - float(dist)), 4)
            vector_candidates[chunk.chunk_id] = (chunk, doc, v_score)

        # ----------------------------------------------------
        # SEARCH METHOD 2: PostgreSQL Full-Text Keyword Search
        # ----------------------------------------------------
        # Build text search query and rank using ts_rank_cd
        ts_vector = func.to_tsvector("english", DocumentChunkModel.text)
        ts_query = func.websearch_to_tsquery("english", clean_query)
        kw_rank_expr = func.ts_rank_cd(ts_vector, ts_query)

        kw_query_obj = (
            db.query(DocumentChunkModel, DocumentModel, kw_rank_expr.label("rank"))
            .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
        )
        kw_query_obj = self._apply_filters(kw_query_obj, clean_fy, clean_as_of_date)

        # Apply phrase/keyword filter or ILIKE substring fallback if full-text query matches
        kw_query_obj = kw_query_obj.filter(
            or_(
                ts_vector.op("@@")(ts_query),
                DocumentChunkModel.text.ilike(f"%{clean_query}%")
            )
        )
        kw_rows = kw_query_obj.order_by(kw_rank_expr.desc()).limit(candidate_limit).all()

        keyword_candidates: Dict[str, Tuple[DocumentChunkModel, DocumentModel, float]] = {}
        for chunk, doc, rank_val in kw_rows:
            raw_rank = float(rank_val) if rank_val is not None else 0.1
            # If matched via ILIKE fallback, assign baseline rank
            if raw_rank == 0.0 and clean_query.lower() in chunk.text.lower():
                raw_rank = 0.1
            keyword_candidates[chunk.chunk_id] = (chunk, doc, raw_rank)

        # ----------------------------------------------------
        # SCORE NORMALIZATION (Min-Max scaling for Keyword Ranks)
        # ----------------------------------------------------
        norm_keyword_scores: Dict[str, float] = {}
        if keyword_candidates:
            raw_ranks = [item[2] for item in keyword_candidates.values()]
            min_r = min(raw_ranks)
            max_r = max(raw_ranks)
            r_range = max_r - min_r

            for cid, (chunk, doc, raw_r) in keyword_candidates.items():
                if r_range > 0.0001:
                    norm_score = round(0.2 + 0.8 * ((raw_r - min_r) / r_range), 4)
                else:
                    norm_score = 0.8
                norm_keyword_scores[cid] = norm_score

        # ----------------------------------------------------
        # DEDUPLICATION & WEIGHTED HYBRID FUSION
        # ----------------------------------------------------
        all_chunk_ids = set(vector_candidates.keys()).union(set(keyword_candidates.keys()))

        hybrid_results = []
        for cid in all_chunk_ids:
            in_vec = cid in vector_candidates
            in_kw = cid in keyword_candidates

            if in_vec:
                chunk, doc, v_score = vector_candidates[cid]
            else:
                chunk, doc, _ = keyword_candidates[cid]
                v_score = 0.0

            kw_score = norm_keyword_scores.get(cid, 0.0)

            # Determine retrieval method tag
            if in_vec and in_kw:
                method = "hybrid"
            elif in_vec:
                method = "vector_only"
            else:
                method = "keyword_only"

            # Compute combined hybrid score
            hybrid_score = round((vw * v_score) + (kw_w * kw_score), 4)

            # Filter out results below minimum threshold
            # (Allow high keyword matches or high vector matches to pass)
            effective_similarity = max(v_score, hybrid_score)
            if effective_similarity >= threshold:
                hybrid_results.append({
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
                    "similarity_score": hybrid_score,  # Returned as primary relevance score
                    "vector_score": v_score,
                    "keyword_score": kw_score,
                    "hybrid_score": hybrid_score,
                    "retrieval_method": method
                })

        # Sort deduplicated results by hybrid_score descending
        hybrid_results.sort(key=lambda x: x["hybrid_score"], reverse=True)

        return hybrid_results[:k]

    def search_similar_chunks(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
        financial_year: Optional[str] = None,
        as_of_date: Optional[str] = None
    ) -> List[dict]:
        """
        Backward-compatible vector retrieval entry point.
        Delegates to search_hybrid_chunks for unified search experience.
        """
        return self.search_hybrid_chunks(
            db=db,
            query=query,
            top_k=top_k,
            min_similarity=min_similarity,
            financial_year=financial_year,
            as_of_date=as_of_date,
            vector_weight=1.0,
            keyword_weight=0.0
        )


# Global singleton RetrievalService instance
retrieval_service = RetrievalService()
