from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


class DocumentTypeEnum(str, Enum):
    CGST_ACT = "CGST_ACT"
    IGST_ACT = "IGST_ACT"
    GST_RULE = "GST_RULE"
    GST_NOTIFICATION = "GST_NOTIFICATION"
    GST_RATE_NOTIFICATION = "GST_RATE_NOTIFICATION"
    GST_CIRCULAR = "GST_CIRCULAR"
    GST_COUNCIL_MATERIAL = "GST_COUNCIL_MATERIAL"
    CASE_LAW = "CASE_LAW"
    OTHER = "OTHER"


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        description="The text prompt or question to send to the AI model.",
        example="Explain GST in simple terms."
    )


class ChatResponse(BaseModel):
    answer: str = Field(
        ...,
        description="The AI-generated response text."
    )


class PageExtract(BaseModel):
    page: int = Field(
        ...,
        description="1-indexed page number of the PDF document.",
        example=1
    )
    text: str = Field(
        ...,
        description="Extracted plain text content from the page."
    )


class PDFExtractionResponse(BaseModel):
    filename: str = Field(
        ...,
        description="Original name of the uploaded PDF file.",
        example="sample_gst_notice.pdf"
    )
    page_count: int = Field(
        ...,
        description="Total number of pages extracted from the PDF.",
        example=2
    )
    pages: List[PageExtract] = Field(
        ...,
        description="List of page extraction objects containing page number and text."
    )


class DocumentChunk(BaseModel):
    chunk_id: str = Field(
        ...,
        description="Unique identifier for the chunk (e.g. sample_gst_notice_p1_c1).",
        example="sample_gst_notice_p1_c1"
    )
    text: str = Field(
        ...,
        description="Cleaned text content of the chunk."
    )
    page: int = Field(
        ...,
        description="1-indexed page number where this chunk originates.",
        example=1
    )
    document: str = Field(
        ...,
        description="Original filename of the document.",
        example="sample_gst_notice.pdf"
    )


class DocumentProcessResponse(BaseModel):
    filename: str = Field(
        ...,
        description="Original name of the processed PDF file.",
        example="sample_gst_notice.pdf"
    )
    page_count: int = Field(
        ...,
        description="Total number of pages in the document.",
        example=2
    )
    chunk_count: int = Field(
        ...,
        description="Total number of chunks generated across all pages.",
        example=4
    )
    chunks: List[DocumentChunk] = Field(
        ...,
        description="List of generated document chunks with metadata."
    )


class EmbeddedDocumentChunk(BaseModel):
    chunk_id: str = Field(
        ...,
        description="Unique identifier for the chunk.",
        example="sample_gst_notice_p1_c1"
    )
    text: str = Field(
        ...,
        description="Cleaned text content of the chunk."
    )
    page: int = Field(
        ...,
        description="1-indexed page number where this chunk originates.",
        example=1
    )
    document: str = Field(
        ...,
        description="Original filename of the document.",
        example="sample_gst_notice.pdf"
    )
    embedding: List[float] = Field(
        ...,
        description="Numerical embedding vector generated for the chunk text."
    )


class DocumentEmbeddingResponse(BaseModel):
    filename: str = Field(
        ...,
        description="Original name of the processed PDF file.",
        example="sample_gst_notice_long.pdf"
    )
    page_count: int = Field(
        ...,
        description="Total number of pages in the document.",
        example=2
    )
    chunk_count: int = Field(
        ...,
        description="Total number of chunks generated across all pages.",
        example=5
    )
    embedding_dimension: int = Field(
        ...,
        description="Dimensionality of each generated embedding vector.",
        example=384
    )
    chunks: List[EmbeddedDocumentChunk] = Field(
        ...,
        description="List of document chunks attached with their numerical embedding vectors."
    )


class EmbeddingTestRequest(BaseModel):
    texts: List[str] = Field(
        ...,
        description="List of text strings to generate embeddings for.",
        example=[
            "Input tax credit can be claimed subject to the conditions prescribed under GST law.",
            "The weather today is pleasant."
        ]
    )


class EmbeddingTestResponse(BaseModel):
    model: str = Field(
        ...,
        description="Name of the embedding model used.",
        example="sentence-transformers/all-MiniLM-L6-v2"
    )
    dimension: int = Field(
        ...,
        description="Dimensionality of each embedding vector.",
        example=384
    )
    count: int = Field(
        ...,
        description="Number of embedding vectors generated.",
        example=2
    )
    embeddings: List[List[float]] = Field(
        ...,
        description="List of numerical embedding vectors."
    )


class SimilarityTestRequest(BaseModel):
    text_a: str = Field(
        ...,
        description="First text prompt (GST domain).",
        example="Input tax credit can be claimed subject to the conditions prescribed under GST law."
    )
    text_b: str = Field(
        ...,
        description="Second text prompt (Related GST domain).",
        example="A registered person may claim input tax credit when the applicable conditions are satisfied."
    )
    text_c: str = Field(
        ...,
        description="Third text prompt (Unrelated general domain).",
        example="The weather today is pleasant."
    )


class SimilarityTestResponse(BaseModel):
    model: str = Field(
        ...,
        description="Name of the embedding model used.",
        example="sentence-transformers/all-MiniLM-L6-v2"
    )
    similarity_a_b: float = Field(
        ...,
        description="Cosine similarity score between Text A and Text B (related).",
        example=0.82
    )
    similarity_a_c: float = Field(
        ...,
        description="Cosine similarity score between Text A and Text C (unrelated).",
        example=0.12
    )
    interpretation: str = Field(
        ...,
        description="Human-readable summary of the similarity evaluation results."
    )


class StoredDocumentSummary(BaseModel):
    id: int = Field(
        ...,
        description="Primary key ID of the stored document record.",
        example=1
    )
    filename: str = Field(
        ...,
        description="Original name of the stored document.",
        example="cgst_act_section_16.pdf"
    )
    sha256_hash: str = Field(
        ...,
        description="Cryptographic SHA-256 content hash of the document bytes.",
        example="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    title: Optional[str] = Field(
        default=None,
        description="Official title of the GST legal document.",
        example="Central Goods and Services Tax Act, 2017 - Section 16"
    )
    document_type: str = Field(
        default="OTHER",
        description="Category/Type of the GST document.",
        example="CGST_ACT"
    )
    source_url: Optional[str] = Field(
        default=None,
        description="Official provenance source URL.",
        example="https://cbic-gst.gov.in/pdf/cgst-act-2017.pdf"
    )
    issuing_authority: Optional[str] = Field(
        default=None,
        description="Official issuing government authority.",
        example="CBIC / Ministry of Finance"
    )
    publication_date: Optional[str] = Field(
        default=None,
        description="Date of official publication.",
        example="2017-04-12"
    )
    effective_from: Optional[str] = Field(
        default=None,
        description="Effective start date.",
        example="2017-07-01"
    )
    effective_to: Optional[str] = Field(
        default=None,
        description="Effective end date (null if currently active)."
    )
    financial_year: Optional[str] = Field(
        default=None,
        description="Associated financial year.",
        example="2017-18"
    )
    document_version: Optional[str] = Field(
        default="1.0",
        description="Document version identifier.",
        example="1.0"
    )
    description: Optional[str] = Field(
        default=None,
        description="Brief summary or description of document contents."
    )
    is_authoritative: bool = Field(
        default=False,
        description="Flag indicating if the document originates from an official government source.",
        example=True
    )
    status: str = Field(
        default="READY",
        description="Processing status (PENDING, PROCESSING, READY, FAILED).",
        example="READY"
    )
    chunk_count: int = Field(
        ...,
        description="Number of stored chunks associated with the document.",
        example=5
    )
    created_at: str = Field(
        ...,
        description="ISO 8601 creation timestamp."
    )


class StoredChunkPreview(BaseModel):
    chunk_id: str = Field(
        ...,
        description="Unique identifier for the chunk.",
        example="cgst_act_section_16_p1_c1"
    )
    page: int = Field(
        ...,
        description="1-indexed page number of the chunk.",
        example=1
    )
    text_preview: str = Field(
        ...,
        description="Truncated preview of the chunk text."
    )


class StoredDocumentDetail(BaseModel):
    id: int = Field(
        ...,
        description="Primary key ID of the stored document.",
        example=1
    )
    filename: str = Field(
        ...,
        description="Original name of the stored document.",
        example="cgst_act_section_16.pdf"
    )
    sha256_hash: str = Field(
        ...,
        description="Cryptographic SHA-256 content hash of the document bytes.",
        example="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    title: Optional[str] = Field(default=None)
    document_type: str = Field(default="OTHER")
    source_url: Optional[str] = Field(default=None)
    issuing_authority: Optional[str] = Field(default=None)
    publication_date: Optional[str] = Field(default=None)
    effective_from: Optional[str] = Field(default=None)
    effective_to: Optional[str] = Field(default=None)
    financial_year: Optional[str] = Field(default=None)
    document_version: Optional[str] = Field(default="1.0")
    description: Optional[str] = Field(default=None)
    is_authoritative: bool = Field(default=False)
    status: str = Field(default="READY")
    created_at: str = Field(..., description="ISO 8601 creation timestamp.")
    chunk_count: int = Field(..., description="Number of stored chunks.")
    chunks: List[StoredChunkPreview] = Field(
        ...,
        description="List of stored chunk metadata previews (no raw vectors exposed)."
    )


class RetrievalRequest(BaseModel):
    query: str = Field(
        ...,
        description="Natural language user query for hybrid semantic & keyword search.",
        example="Section 16 conditions for claiming input tax credit"
    )
    top_k: Optional[int] = Field(
        default=5,
        description="Maximum number of relevant document chunks to return (1 to 20).",
        example=5
    )
    min_similarity: Optional[float] = Field(
        default=None,
        description="Optional minimum similarity threshold score (e.g. 0.20).",
        example=0.20
    )
    financial_year: Optional[str] = Field(
        default=None,
        description="Optional financial year filter (e.g. 2025-26).",
        example="2025-26"
    )
    as_of_date: Optional[str] = Field(
        default=None,
        description="Optional as-of applicability date filter (YYYY-MM-DD format).",
        example="2025-04-01"
    )
    vector_weight: Optional[float] = Field(
        default=0.7,
        description="Weight assigned to dense vector semantic search score (0.0 to 1.0).",
        example=0.7
    )
    keyword_weight: Optional[float] = Field(
        default=0.3,
        description="Weight assigned to PostgreSQL full-text keyword search score (0.0 to 1.0).",
        example=0.3
    )


class RetrievedChunk(BaseModel):
    chunk_id: str = Field(
        ...,
        description="Unique identifier for the chunk.",
        example="sample_gst_notice_long_p1_c1"
    )
    document_id: int = Field(
        ...,
        description="Primary key ID of the source document.",
        example=1
    )
    document: str = Field(
        ...,
        description="Original filename of the source document.",
        example="sample_gst_notice_long.pdf"
    )
    title: Optional[str] = Field(
        default=None,
        description="Official title of the document.",
        example="Central Goods and Services Tax Act, 2017 - Section 16"
    )
    document_type: Optional[str] = Field(
        default="OTHER",
        description="Category/Type of the document.",
        example="CGST_ACT"
    )
    source_url: Optional[str] = Field(
        default=None,
        description="Official provenance source URL.",
        example="https://cbic-gst.gov.in/pdf/cgst-act-2017.pdf"
    )
    issuing_authority: Optional[str] = Field(
        default=None,
        description="Official issuing government authority.",
        example="CBIC / Ministry of Finance"
    )
    publication_date: Optional[str] = Field(
        default=None,
        description="Date of official publication.",
        example="2017-04-12"
    )
    effective_from: Optional[str] = Field(
        default=None,
        description="Effective start date (YYYY-MM-DD).",
        example="2017-07-01"
    )
    effective_to: Optional[str] = Field(
        default=None,
        description="Effective end date (null if active)."
    )
    financial_year: Optional[str] = Field(
        default=None,
        description="Associated financial year.",
        example="2017-18"
    )
    page: int = Field(
        ...,
        description="1-indexed page number of the chunk.",
        example=1
    )
    text: str = Field(
        ...,
        description="Original cleaned text content of the retrieved chunk."
    )
    similarity_score: float = Field(
        ...,
        description="Calculated similarity / hybrid ranking score (higher means more relevant).",
        example=0.82
    )
    vector_score: Optional[float] = Field(
        default=None,
        description="Raw vector cosine similarity score [0.0 to 1.0].",
        example=0.8174
    )
    keyword_score: Optional[float] = Field(
        default=None,
        description="Normalized keyword full-text search score [0.0 to 1.0].",
        example=0.6500
    )
    hybrid_score: Optional[float] = Field(
        default=None,
        description="Weighted combined hybrid score.",
        example=0.7672
    )
    retrieval_method: Optional[str] = Field(
        default="hybrid",
        description="Method that retrieved this chunk ('hybrid', 'vector_only', 'keyword_only').",
        example="hybrid"
    )
    retrieval_mode: Optional[str] = Field(
        default=None,
        description="Retrieval mode used ('pgvector' or 'python-fallback').",
        example="python-fallback"
    )
    act: Optional[str] = Field(
        default=None,
        description="Parsed Act name from chunk label (e.g., 'CGST Act 2017').",
        example="CGST Act 2017"
    )
    section: Optional[str] = Field(
        default=None,
        description="Parsed section number from chunk label (e.g., '16' or '17A').",
        example="16"
    )
    sub: Optional[str] = Field(
        default=None,
        description="Parsed subsection from chunk label (e.g., '(1)' or '(1)-(3)').",
        example="(1)"
    )
    citation_label: Optional[str] = Field(
        default=None,
        description="Formatted citation label combining act, section, and subsection.",
        example="CGST Act 2017, Section 16(1)"
    )


class RetrievalResponse(BaseModel):
    query: str = Field(
        ...,
        description="The original user query text.",
        example="What are the conditions for claiming input tax credit?"
    )
    top_k: int = Field(
        ...,
        description="Target maximum top_k specified in request.",
        example=5
    )
    count: int = Field(
        ...,
        description="Actual number of relevant chunks returned after similarity threshold filtering.",
        example=3
    )
    retrieval_mode: Optional[str] = Field(
        default=None,
        description="Retrieval mode used ('pgvector' or 'python-fallback').",
        example="python-fallback"
    )
    results: List[RetrievedChunk] = Field(
        ...,
        description="List of retrieved relevant document chunks with source metadata and similarity scores."
    )


class RAGRequest(BaseModel):
    query: str = Field(
        ...,
        description="User's GST law question.",
        example="What are the conditions for claiming input tax credit?"
    )
    top_k: Optional[int] = Field(
        default=5,
        description="Maximum number of relevant document chunks to retrieve (1 to 20).",
        example=5
    )
    min_similarity: Optional[float] = Field(
        default=None,
        description="Optional minimum cosine similarity threshold score.",
        example=0.20
    )
    financial_year: Optional[str] = Field(
        default=None,
        description="Optional financial year applicability filter (e.g. 2025-26).",
        example="2025-26"
    )
    as_of_date: Optional[str] = Field(
        default=None,
        description="Optional as-of date applicability filter (YYYY-MM-DD format).",
        example="2025-04-01"
    )
    vector_weight: Optional[float] = Field(
        default=0.7,
        description="Weight assigned to dense vector semantic search score.",
        example=0.7
    )
    keyword_weight: Optional[float] = Field(
        default=0.3,
        description="Weight assigned to PostgreSQL full-text keyword search score.",
        example=0.3
    )


class VerificationComponentDetails(BaseModel):
    evidence_component: float = Field(..., example=0.8122)
    agreement_component: float = Field(..., example=1.0)
    model_coverage_component: float = Field(..., example=1.0)


class VerificationSignal(BaseModel):
    verification_score: float = Field(
        ...,
        description="Deterministic verification score [0.0 to 1.0]. NOT a legal correctness probability.",
        example=0.8225
    )
    verification_level: str = Field(
        ...,
        description="User-facing verification level: 'HIGH', 'MEDIUM', 'LOW', or 'UNVERIFIED'.",
        example="HIGH"
    )
    verification_status: str = Field(
        ...,
        description="Canonical verification status tag ('strongly_supported', 'moderately_supported', 'limited_support', 'unverified').",
        example="strongly_supported"
    )
    explanation: str = Field(
        ...,
        description="Human-readable explanation of the verification score calculation and safety caps.",
        example="Strong supporting GST evidence and agreement among available independent models."
    )
    components: VerificationComponentDetails = Field(...)


class RAGResponse(BaseModel):
    query: str = Field(
        ...,
        description="Original user query.",
        example="What are the conditions for claiming input tax credit?"
    )
    answer: str = Field(
        ...,
        description="Grounded AI-generated answer strictly based on retrieved evidence."
    )
    retrieved_count: int = Field(
        ...,
        description="Number of retrieved chunks used as evidence.",
        example=3
    )
    evidence_status: str = Field(
        ...,
        description="Deterministically evaluated evidence status: 'strong', 'weak', or 'insufficient'.",
        example="strong"
    )
    best_score: float = Field(
        ...,
        description="Highest hybrid relevance score among retrieved evidence chunks.",
        example=0.8122
    )
    verification: Optional[VerificationSignal] = Field(
        default=None,
        description="Deterministic verification score and level signal."
    )
    retrieved_chunks: List[RetrievedChunk] = Field(
        ...,
        description="List of retrieved evidence chunks with source metadata and similarity scores."
    )


class MultiModelRequest(BaseModel):
    query: str = Field(
        ...,
        description="User's GST law question for multi-model verification.",
        example="What are the conditions for claiming input tax credit under Section 16?"
    )
    top_k: Optional[int] = Field(
        default=5,
        description="Maximum number of evidence chunks to retrieve (1 to 20).",
        example=5
    )
    financial_year: Optional[str] = Field(
        default=None,
        description="Optional financial year filter.",
        example="2025-26"
    )
    as_of_date: Optional[str] = Field(
        default=None,
        description="Optional as-of date applicability filter.",
        example="2025-04-01"
    )
    providers: Optional[List[str]] = Field(
        default=["gemini", "mistral", "grok", "ollama"],
        description="List of LLM providers to execute concurrently using identical evidence.",
        example=["gemini", "mistral", "grok", "ollama"]
    )
    vector_weight: Optional[float] = Field(default=0.7)
    keyword_weight: Optional[float] = Field(default=0.3)


class ModelAnswerResult(BaseModel):
    provider: str = Field(..., description="Provider name (gemini, mistral, grok, ollama).", example="gemini")
    model: str = Field(..., description="Model identifier used.", example="gemini-3.6-flash")
    success: bool = Field(..., description="True if generation succeeded.", example=True)
    answer: Optional[str] = Field(default=None, description="Generated answer text if successful.")
    error: Optional[str] = Field(default=None, description="Error message if generation failed or unconfigured.")
    response_time: Optional[float] = Field(default=None, description="Execution time in seconds.", example=1.85)


class ComparisonResult(BaseModel):
    overall_status: str = Field(
        ...,
        description="Deterministic status: 'agreement', 'partial_agreement', 'disagreement', or 'insufficient_models'.",
        example="agreement"
    )
    successful_provider_count: int = Field(..., example=2)
    failed_provider_count: int = Field(..., example=1)
    pairwise_similarity: Dict[str, float] = Field(
        default_factory=dict,
        description="Pairwise Jaccard token similarity scores between successful model answers.",
        example={"gemini_vs_openai": 0.68}
    )
    shared_legal_references: List[str] = Field(
        default_factory=list,
        description="Legal references (sections, rules, notifications) cited by all successful models.",
        example=["Section 16"]
    )
    conflicting_references: List[str] = Field(
        default_factory=list,
        description="Legal references cited by some models but omitted by others.",
        example=[]
    )


class MultiModelResponse(BaseModel):
    query: str = Field(..., description="Original user query.")
    evidence_status: str = Field(..., description="Evaluated evidence status ('strong', 'weak', 'insufficient').")
    best_score: float = Field(..., description="Highest hybrid relevance score among retrieved evidence chunks.")
    retrieved_count: int = Field(..., description="Number of retrieved chunks used as shared evidence.")
    model_results: List[ModelAnswerResult] = Field(..., description="List of provider answer results.")
    comparison: ComparisonResult = Field(..., description="Deterministic answer comparison results.")
    verification: Optional[VerificationSignal] = Field(
        default=None,
        description="Deterministic verification score and level signal."
    )
    retrieved_chunks: List[RetrievedChunk] = Field(..., description="Shared evidence chunks passed to models.")


class DeepSeekLocalRequest(BaseModel):
    query: str = Field(
        ...,
        description="User question to send directly to local DeepSeek-R1 7B model via Ollama.",
        example="What is input tax credit under GST?"
    )


class DeepSeekLocalResponse(BaseModel):
    provider: str = Field(default="deepseek-local", example="deepseek-local")
    model: str = Field(default="deepseek-r1:7b", example="deepseek-r1:7b")
    answer: str = Field(..., description="Generated answer text from local DeepSeek-R1 7B.")
    status: str = Field(default="success", example="success")
