from typing import List, Optional, Dict, Tuple
from datetime import datetime
import re
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, text
from database.models import DocumentModel, DocumentChunkModel, Vector
from services.embedding_service import embedding_service

DEFAULT_TOP_K = 5
MAX_TOP_K = 20
DEFAULT_MIN_SIMILARITY = 0.20
DEFAULT_VECTOR_WEIGHT = 0.7
DEFAULT_KEYWORD_WEIGHT = 0.3
DEFAULT_SECTION_BOOST = 0.15  # Bonus for section-mention matches
DEFAULT_MAX_PER_SECTION = 3  # Max chunks from same (act, section) in results

# Detect retrieval mode at module load
import logging
logger = logging.getLogger(__name__)

try:
    from pgvector.sqlalchemy import Vector as PgVector
    _RETRIEVAL_MODE = "pgvector"
    logger.info(f"[RETRIEVAL] Using pgvector native cosine_distance for vector search")
except Exception:
    _RETRIEVAL_MODE = "python-fallback"
    logger.info(f"[RETRIEVAL] Using Python-side cosine similarity fallback (SafeVector type)")


def parse_chunk_label(text: str) -> Dict[str, Optional[str]]:
    """
    Parse chunk label line like "[CGST Act 2017, Section 22(1) - Persons liable for registration]"
    Returns dict with act, section, sub, title, citation_label.
    """
    result = {
        "act": None,
        "section": None,
        "sub": None,
        "title": None,
        "citation_label": None
    }

    # Extract label line (first line if it starts with '[')
    lines = text.split('\n')
    label_line = None
    for line in lines:
        line = line.strip()
        if line.startswith('[') and ']' in line:
            label_line = line
            break

    if not label_line:
        return result

    # Remove brackets
    content = label_line.strip('[]')

    # Pattern: "Act Name, Section X(Y) - Title"
    # Examples:
    # "CGST Act 2017, Section 22(1) - Persons liable for registration"
    # "IGST Act 2017, Section 2(11) - Definitions"
    # "CGST Act 2017, Section 16(4), part 1/2 - Eligibility and conditions for taking input tax credit"

    # Extract act (everything before "Section")
    if "Section" in content:
        parts = content.split("Section", 1)
        result["act"] = parts[0].strip().rstrip(', ')
        section_part = parts[1].strip()
    else:
        return result

    # Extract section number and subsection
    # Pattern: "22(1)" or "22(1)-(3)" or "17A(1)" or "16(4), part 1/2"
    section_match = re.match(r'(\d+[A-Za-z]?(?:\([^)]+\)(?:-\([^)]+\))*)?)', section_part)
    if section_match:
        full_section = section_match.group(1)
        # Extract base section (e.g., "22" from "22(1)" or "17A" from "17A(1)")
        base_section_match = re.match(r'(\d+[A-Za-z]?)', full_section)
        if base_section_match:
            result["section"] = base_section_match.group(1)
        # Extract subsection (e.g., "(1)" or "(1)-(3)")
        sub_match = re.search(r'\(([^)]+)\)(?:-\(([^)]+)\))?', full_section)
        if sub_match:
            if sub_match.group(2):
                result["sub"] = f"({sub_match.group(1)})-({sub_match.group(2)})"
            else:
                result["sub"] = f"({sub_match.group(1)})"

    # Extract title (after " - ")
    if " - " in section_part:
        title_part = section_part.split(" - ", 1)[1]
        # Remove any "part X/Y" suffix for cleaner title
        title_part = re.sub(r',\s*part\s+\d+/\d+\s*$', '', title_part, flags=re.IGNORECASE)
        result["title"] = title_part.strip()

    # Build citation label
    if result["act"] and result["section"]:
        citation = f"{result['act']}, Section {result['section']}"
        if result["sub"]:
            citation += result["sub"]
        result["citation_label"] = citation

    return result


def extract_section_mentions(query: str) -> Dict[str, Optional[str]]:
    """
    Extract section mentions from query (e.g., "section 16", "sec 16", "s. 16", "section 16(2)").
    Returns dict with section number and optional act.
    """
    result = {
        "section": None,
        "sub": None,
        "act": None
    }

    query_lower = query.lower()

    # Detect act mention (CGST/IGST)
    if "cgst" in query_lower or "central" in query_lower:
        result["act"] = "CGST Act 2017"
    elif "igst" in query_lower or "integrated" in query_lower:
        result["act"] = "IGST Act 2017"

    # Detect section number with various prefixes
    # Patterns: "section 16", "sec 16", "s. 16", "section 16(2)", "section 16(1)-(3)"
    # Simplified: just extract section number and optionally subsection
    section_match = re.search(r'(?:section|sec|s\.)\s*(\d+[A-Za-z]?)(?:\s*\(([^)]+)\))?', query_lower)
    if not section_match:
        section_match = re.search(r'(\d+[A-Za-z]?)(?:\s*\(([^)]+)\))?\s*(?:section|clause|provision)?', query_lower)

    if section_match:
        result["section"] = section_match.group(1)
        if section_match.group(2):
            # Check for range like (1)-(3)
            sub_parts = section_match.group(2).split('-')
            if len(sub_parts) > 1:
                result["sub"] = f"({sub_parts[0]})-({sub_parts[1]})"
            else:
                result["sub"] = f"({section_match.group(2)})"

    return result


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

        # Extract section mentions for boost
        section_mentions = extract_section_mentions(clean_query)

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
            # Score ALL chunks passing filters (corpus is < 1000 rows), then sort and limit
            all_chunks = vec_query_obj.all()

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
        # Build OR-style tsquery for better natural-language matching
        # Parse query into terms and build OR query: term1 | term2 | term3
        ts_vector = func.to_tsvector("english", DocumentChunkModel.text)

        # Split query into words, filter basic stopwords, join with | for OR semantics
        # This is a simple approach; for production, consider using Python-side stopword removal
        words = re.findall(r'\b\w+\b', clean_query.lower())
        # Basic English stopwords to filter
        basic_stopwords = {'a', 'an', 'the', 'and', 'or', 'in', 'of', 'to', 'for', 'is', 'are', 'was', 'were',
                          'be', 'been', 'being', 'with', 'as', 'by', 'at', 'from', 'that', 'this', 'it', 'on'}
        filtered_words = [w for w in words if w not in basic_stopwords and len(w) > 2]
        if filtered_words:
            or_query_str = ' | '.join(filtered_words)
            ts_query = func.to_tsquery("english", or_query_str)
        else:
            # Fallback to plainto_tsquery if no meaningful terms
            ts_query = func.plainto_tsquery("english", clean_query)

        # Use ts_rank_cd with normalization flag 32 (rank/(rank+1)) to prevent score inflation
        kw_rank_expr = func.ts_rank_cd(ts_vector, ts_query, 32)

        kw_query_obj = (
            db.query(DocumentChunkModel, DocumentModel, kw_rank_expr.label("rank"))
            .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
        )
        kw_query_obj = self._apply_filters(kw_query_obj, clean_fy, clean_as_of_date)

        # Filter by full-text match only (removed ILIKE fallback)
        kw_query_obj = kw_query_obj.filter(ts_vector.op("@@")(ts_query))
        kw_rows = kw_query_obj.order_by(kw_rank_expr.desc()).limit(candidate_limit).all()

        keyword_candidates: Dict[str, Tuple[DocumentChunkModel, DocumentModel, float]] = {}
        for chunk, doc, rank_val in kw_rows:
            raw_rank = float(rank_val) if rank_val is not None else 0.0
            keyword_candidates[chunk.chunk_id] = (chunk, doc, raw_rank)

        # ----------------------------------------------------
        # SCORE NORMALIZATION (No min-max; ts_rank_cd with normalization 32 already produces bounded scores)
        # ----------------------------------------------------
        norm_keyword_scores: Dict[str, float] = {}
        for cid, (chunk, doc, raw_r) in keyword_candidates.items():
            # ts_rank_cd with normalization 32 produces values in [0, 1), use directly
            norm_keyword_scores[cid] = round(raw_r, 4)

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

            # Parse chunk label for metadata (needed for section boost)
            label_info = parse_chunk_label(chunk.text)

            # Apply section-mention boost if applicable
            if section_mentions["section"]:
                boost_applied = False
                # Check section match
                if label_info["section"] == section_mentions["section"]:
                    # Check subsection match if specified
                    if section_mentions["sub"]:
                        if label_info["sub"] == section_mentions["sub"]:
                            hybrid_score = round(min(1.0, hybrid_score + DEFAULT_SECTION_BOOST), 4)
                            boost_applied = True
                    else:
                        # Section match without specific subsection
                        hybrid_score = round(min(1.0, hybrid_score + DEFAULT_SECTION_BOOST), 4)
                        boost_applied = True

                # Check act match if specified
                if not boost_applied and section_mentions["act"] and label_info["act"] == section_mentions["act"]:
                    hybrid_score = round(min(1.0, hybrid_score + DEFAULT_SECTION_BOOST * 0.5), 4)

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
                    "retrieval_method": method,
                    # Add parsed label fields
                    "act": label_info["act"],
                    "section": label_info["section"],
                    "sub": label_info["sub"],
                    "citation_label": label_info["citation_label"]
                })

        # Sort deduplicated results by hybrid_score descending
        hybrid_results.sort(key=lambda x: x["hybrid_score"], reverse=True)

        # Apply diversity cap: limit chunks from same (act, section)
        section_counts = defaultdict(int)
        final_results = []
        for result in hybrid_results:
            act = result.get("act") or "unknown"
            section = result.get("section") or "unknown"
            key = (act, section)

            current_count = section_counts[key]
            if current_count < DEFAULT_MAX_PER_SECTION:
                final_results.append(result)
                section_counts[key] = current_count + 1
            # If we've hit the cap for this section, skip but keep looking for other sections

        # If we couldn't fill top_k due to diversity cap, relax it
        if len(final_results) < k and len(hybrid_results) > len(final_results):
            # Add remaining results from capped sections until we reach k
            for result in hybrid_results:
                if len(final_results) >= k:
                    break
                if result not in final_results:
                    final_results.append(result)

        # Add retrieval mode metadata
        for result in final_results:
            result["retrieval_mode"] = _RETRIEVAL_MODE

        return final_results[:k]

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
