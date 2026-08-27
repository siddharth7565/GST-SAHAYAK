from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

from schemas import (
    ChatRequest, ChatResponse,
    PDFExtractionResponse, DocumentProcessResponse,
    EmbeddedDocumentChunk, DocumentEmbeddingResponse,
    EmbeddingTestRequest, EmbeddingTestResponse,
    SimilarityTestRequest, SimilarityTestResponse,
    StoredDocumentSummary, StoredChunkPreview, StoredDocumentDetail,
    RetrievalRequest, RetrievedChunk, RetrievalResponse,
    RAGRequest, RAGResponse, DocumentTypeEnum,
    MultiModelRequest, MultiModelResponse,
    DeepSeekLocalRequest, DeepSeekLocalResponse
)
from services.llm_service import llm_service
from services.llm_providers import get_llm_provider
from services.document_service import document_service
from services.embedding_service import embedding_service
from services.retrieval_service import retrieval_service
from services.rag_service import rag_service
from services.document_ingestion_service import document_ingestion_service
from services.multi_model_verification_service import multi_model_verification_service
from services.ollama_manager import ensure_ollama_running
from database.connection import get_db, init_db
from database.models import DocumentModel, DocumentChunkModel

app = FastAPI(title="GST Sahayak API")

# Enable CORS so the React frontend can communicate with the FastAPI backend during local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Attempt database initialization and pgvector extension verification on startup, and log Ollama configuration."""
    try:
        init_db()
        print("[DATABASE] PostgreSQL connection and pgvector extension verified successfully.")
    except Exception as exc:
        print(f"[DATABASE WARNING] {str(exc)}")

    try:
        provider = get_llm_provider("ollama")
        if provider.is_configured():
            print("[OLLAMA API] Remote Ollama Cloud API configured successfully via OLLAMA_API_KEY.")
        else:
            ensure_ollama_running()
    except Exception as exc:
        print(f"[OLLAMA STARTUP WARNING] {str(exc)}")


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "GST Sahayak backend is running"
    }


@app.get("/api/test")
def test_endpoint():
    return {
        "message": "Frontend and backend communication successful"
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """Endpoint to process chat messages via Gemini LLM Service."""
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User message cannot be empty."
        )

    try:
        answer = llm_service.generate_response(request.message)
        return ChatResponse(answer=answer)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(exc)}"
        )


@app.post("/api/documents/extract", response_model=PDFExtractionResponse)
async def extract_pdf_document(file: UploadFile = File(...)):
    """
    Endpoint to receive a multipart PDF upload and extract text page-by-page.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF files are supported."
        )

    try:
        file_bytes = await file.read()
        extraction_result = document_service.extract_pdf_text(file_bytes, file.filename)
        return PDFExtractionResponse(**extraction_result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(exc)}"
        )


@app.post("/api/documents/process", response_model=DocumentProcessResponse)
async def process_pdf_document(file: UploadFile = File(...)):
    """
    Endpoint to receive a multipart PDF upload and execute extraction -> cleaning -> chunking.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF files are supported."
        )

    try:
        file_bytes = await file.read()
        processing_result = document_service.process_pdf_document(file_bytes, file.filename)
        return DocumentProcessResponse(**processing_result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(exc)}"
        )


@app.post("/api/embeddings/test", response_model=EmbeddingTestResponse)
def generate_embeddings_test(request: EmbeddingTestRequest):
    """
    Development endpoint to test embedding vector generation using SentenceTransformers.
    """
    if not request.texts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="List of texts to embed cannot be empty."
        )

    try:
        vectors = embedding_service.embed_texts(request.texts)
        dimension = embedding_service.get_dimension()
        return EmbeddingTestResponse(
            model=embedding_service.MODEL_NAME,
            dimension=dimension,
            count=len(vectors),
            embeddings=vectors
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate embeddings: {str(exc)}"
        )


@app.post("/api/embeddings/similarity", response_model=SimilarityTestResponse)
def evaluate_similarity_test(request: SimilarityTestRequest):
    """
    Development endpoint to test cosine similarity between related and unrelated texts.
    """
    try:
        sim_a_b = embedding_service.evaluate_similarity(request.text_a, request.text_b)
        sim_a_c = embedding_service.evaluate_similarity(request.text_a, request.text_c)

        if sim_a_b > sim_a_c:
            interpretation = (
                f"PASS: Related GST texts (A & B) have higher similarity ({sim_a_b:.4f}) "
                f"than unrelated text (A & C) ({sim_a_c:.4f})."
            )
        else:
            interpretation = (
                f"EVALUATION: Related similarity ({sim_a_b:.4f}) is lower or equal to "
                f"unrelated similarity ({sim_a_c:.4f})."
            )

        return SimilarityTestResponse(
            model=embedding_service.MODEL_NAME,
            similarity_a_b=sim_a_b,
            similarity_a_c=sim_a_c,
            interpretation=interpretation
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate similarity: {str(exc)}"
        )


@app.post("/api/embeddings/document", response_model=DocumentEmbeddingResponse)
async def process_and_embed_pdf_document(file: UploadFile = File(...)):
    """
    Development endpoint to receive a multipart PDF upload and execute
    extraction -> cleaning -> chunking -> batch embedding generation pipeline.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF files are supported."
        )

    try:
        file_bytes = await file.read()
        embedding_result = document_service.process_and_embed_pdf_document(file_bytes, file.filename)
        return DocumentEmbeddingResponse(**embedding_result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process and embed document: {str(exc)}"
        )


@app.post("/api/documents/store", response_model=StoredDocumentSummary)
async def store_pdf_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Legacy endpoint for basic PDF upload & ingestion.
    Delegates to document_ingestion_service with SHA-256 duplicate protection.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF files are supported."
        )

    try:
        file_bytes = await file.read()
        summary = document_ingestion_service.ingest_document(
            db=db,
            file_bytes=file_bytes,
            filename=file.filename,
            metadata={"title": file.filename, "document_type": "OTHER", "is_authoritative": False}
        )
        return StoredDocumentSummary(**summary)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store document in database: {str(exc)}"
        )


@app.post("/api/knowledge/documents", response_model=StoredDocumentSummary)
async def ingest_knowledge_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    document_type: Optional[str] = Form("OTHER"),
    source_url: Optional[str] = Form(None),
    issuing_authority: Optional[str] = Form(None),
    publication_date: Optional[str] = Form(None),
    effective_from: Optional[str] = Form(None),
    effective_to: Optional[str] = Form(None),
    financial_year: Optional[str] = Form(None),
    document_version: Optional[str] = Form("1.0"),
    description: Optional[str] = Form(None),
    is_authoritative: Optional[bool] = Form(False),
    db: Session = Depends(get_db)
):
    """
    Production GST Knowledge Base document ingestion endpoint.
    Accepts PDF upload and comprehensive legal metadata (title, type, source URL, issuing authority, dates, FY).
    Calculates SHA-256 hash for duplicate content protection.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF files are supported."
        )

    # Validate document_type enum value
    valid_types = [t.value for t in DocumentTypeEnum]
    dt_upper = (document_type or "OTHER").upper()
    if dt_upper not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document_type '{document_type}'. Supported types: {', '.join(valid_types)}"
        )

    metadata = {
        "title": title,
        "document_type": dt_upper,
        "source_url": source_url,
        "issuing_authority": issuing_authority,
        "publication_date": publication_date,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "financial_year": financial_year,
        "document_version": document_version,
        "description": description,
        "is_authoritative": is_authoritative
    }

    try:
        file_bytes = await file.read()
        summary = document_ingestion_service.ingest_document(
            db=db,
            file_bytes=file_bytes,
            filename=file.filename,
            metadata=metadata
        )
        return StoredDocumentSummary(**summary)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest knowledge document: {str(exc)}"
        )


@app.delete("/api/knowledge/documents/{document_id}")
def delete_knowledge_document(document_id: int, db: Session = Depends(get_db)):
    """
    Deletes a document and its associated chunks from PostgreSQL by document ID.
    """
    try:
        deleted = document_ingestion_service.delete_document(db, document_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found."
            )
        return {"message": f"Document with ID {document_id} deleted successfully."}
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(exc)}"
        )


@app.get("/api/documents", response_model=List[StoredDocumentSummary])
def list_stored_documents(db: Session = Depends(get_db)):
    """
    Inspection endpoint returning list of stored GST documents in PostgreSQL with full legal metadata.
    Excludes raw embedding vectors.
    """
    try:
        documents = db.query(DocumentModel).order_by(DocumentModel.id.desc()).all()
        summaries = []
        for doc in documents:
            summaries.append(
                StoredDocumentSummary(
                    id=doc.id,
                    filename=doc.filename,
                    sha256_hash=doc.sha256_hash,
                    title=doc.title,
                    document_type=doc.document_type,
                    source_url=doc.source_url,
                    issuing_authority=doc.issuing_authority,
                    publication_date=doc.publication_date,
                    effective_from=doc.effective_from,
                    effective_to=doc.effective_to,
                    financial_year=doc.financial_year,
                    document_version=doc.document_version,
                    description=doc.description,
                    is_authoritative=doc.is_authoritative,
                    status=doc.status,
                    chunk_count=len(doc.chunks),
                    created_at=doc.created_at.isoformat()
                )
            )
        return summaries
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve stored documents: {str(exc)}"
        )


@app.get("/api/documents/{document_id}", response_model=StoredDocumentDetail)
def get_stored_document_detail(document_id: int, db: Session = Depends(get_db)):
    """
    Inspection endpoint returning detailed legal metadata and chunk previews for a specific document.
    Excludes raw embedding vectors.
    """
    try:
        doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found."
            )

        chunk_previews = []
        for c in doc.chunks:
            preview = c.text[:120] + "..." if len(c.text) > 120 else c.text
            chunk_previews.append(
                StoredChunkPreview(
                    chunk_id=c.chunk_id,
                    page=c.page,
                    text_preview=preview
                )
            )

        return StoredDocumentDetail(
            id=doc.id,
            filename=doc.filename,
            sha256_hash=doc.sha256_hash,
            title=doc.title,
            document_type=doc.document_type,
            source_url=doc.source_url,
            issuing_authority=doc.issuing_authority,
            publication_date=doc.publication_date,
            effective_from=doc.effective_from,
            effective_to=doc.effective_to,
            financial_year=doc.financial_year,
            document_version=doc.document_version,
            description=doc.description,
            is_authoritative=doc.is_authoritative,
            status=doc.status,
            created_at=doc.created_at.isoformat(),
            chunk_count=len(doc.chunks),
            chunks=chunk_previews
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document details: {str(exc)}"
        )


@app.post("/api/retrieval/search", response_model=RetrievalResponse)
def retrieval_search_endpoint(
    request: RetrievalRequest,
    db: Session = Depends(get_db)
):
    """
    Production hybrid retrieval endpoint for GST Sahayak.
    Combines pgvector dense semantic search and PostgreSQL full-text keyword search
    with SQL temporal applicability filtering.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty."
        )

    if request.top_k is not None and (request.top_k < 1 or request.top_k > retrieval_service.max_top_k):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"top_k must be an integer between 1 and {retrieval_service.max_top_k}."
        )

    try:
        results_data = retrieval_service.search_hybrid_chunks(
            db=db,
            query=request.query,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
            financial_year=request.financial_year,
            as_of_date=request.as_of_date,
            vector_weight=request.vector_weight,
            keyword_weight=request.keyword_weight
        )

        retrieved_chunks = [RetrievedChunk(**item) for item in results_data]
        top_k_val = request.top_k if request.top_k is not None else retrieval_service.default_top_k

        return RetrievalResponse(
            query=request.query.strip(),
            top_k=top_k_val,
            count=len(retrieved_chunks),
            results=retrieved_chunks
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval search failed: {str(exc)}"
        )


@app.post("/api/rag/answer", response_model=RAGResponse)
def rag_answer_endpoint(
    request: RAGRequest,
    db: Session = Depends(get_db)
):
    """
    Production Hybrid RAG answer generation endpoint for GST Sahayak.
    Retrieves relevant document chunks, deterministically evaluates evidence quality (strong, weak, insufficient),
    generates a grounded answer via Gemini LLMService, and returns deterministic verification signal.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User query cannot be empty."
        )

    if request.top_k is not None and (request.top_k < 1 or request.top_k > retrieval_service.max_top_k):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"top_k must be an integer between 1 and {retrieval_service.max_top_k}."
        )

    try:
        rag_output = rag_service.answer_question(
            db=db,
            query=request.query,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
            financial_year=request.financial_year,
            as_of_date=request.as_of_date,
            vector_weight=request.vector_weight,
            keyword_weight=request.keyword_weight
        )

        retrieved_chunks = [RetrievedChunk(**item) for item in rag_output["retrieved_chunks"]]

        return RAGResponse(
            query=rag_output["query"],
            answer=rag_output["answer"],
            retrieved_count=rag_output["retrieved_count"],
            evidence_status=rag_output["evidence_status"],
            best_score=rag_output["best_score"],
            verification=rag_output.get("verification"),
            retrieved_chunks=retrieved_chunks
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG answer generation failed: {str(exc)}"
        )


@app.post("/api/rag/verify", response_model=MultiModelResponse)
def rag_multi_model_verify_endpoint(
    request: MultiModelRequest,
    db: Session = Depends(get_db)
):
    """
    Production Multi-Model Answer Verification endpoint for GST Sahayak.
    Performs hybrid retrieval ONCE to obtain identical shared GST evidence.
    Concurrently executes requested LLM providers (Gemini, OpenAI, Claude) using identical evidence and prompts.
    Deterministically compares model answers and computes overall verification signal with safety caps.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty."
        )

    try:
        verify_output = multi_model_verification_service.verify_question(
            db=db,
            query=request.query,
            top_k=request.top_k,
            financial_year=request.financial_year,
            as_of_date=request.as_of_date,
            providers=request.providers,
            vector_weight=request.vector_weight,
            keyword_weight=request.keyword_weight
        )

        retrieved_chunks = [RetrievedChunk(**item) for item in verify_output["retrieved_chunks"]]

        return MultiModelResponse(
            query=verify_output["query"],
            evidence_status=verify_output["evidence_status"],
            best_score=verify_output["best_score"],
            retrieved_count=verify_output["retrieved_count"],
            model_results=verify_output["model_results"],
            comparison=verify_output["comparison"],
            verification=verify_output.get("verification"),
            retrieved_chunks=retrieved_chunks
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-model verification failed: {str(exc)}"
        )


@app.post("/api/llm/deepseek-local", response_model=DeepSeekLocalResponse)
def deepseek_local_endpoint(request: DeepSeekLocalRequest):
    """
    Dedicated endpoint to send questions directly to local DeepSeek-R1 7B via Ollama (http://localhost:11434).
    Does NOT use the official DeepSeek API key or paid balance.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty."
        )

    try:
        provider = get_llm_provider("deepseek-local")
        ans_text = provider.generate_response(request.query)
        return DeepSeekLocalResponse(
            provider="deepseek-local",
            model=getattr(provider, "_model_name", "deepseek-r1:7b"),
            answer=ans_text,
            status="success"
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Local DeepSeek generation failed: {str(exc)}"
        )
