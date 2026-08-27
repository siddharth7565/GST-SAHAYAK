import hashlib
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from database.models import DocumentModel, DocumentChunkModel
from services.document_service import document_service


class DocumentIngestionService:
    """
    Production Document Ingestion Service for GST Sahayak.
    Handles SHA-256 content hash duplicate detection, legal document metadata validation,
    PDF processing via DocumentService, batch embedding generation, and atomic DB persistence.
    """

    def __init__(self):
        self.document_service = document_service

    @staticmethod
    def calculate_sha256(file_bytes: bytes) -> str:
        """Calculates SHA-256 cryptographic hash from file bytes."""
        hasher = hashlib.sha256()
        hasher.update(file_bytes)
        return hasher.hexdigest()

    def ingest_document(
        self,
        db: Session,
        file_bytes: bytes,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes full document ingestion pipeline:
        1. Calculate SHA-256 hash & check duplicate content in DB.
        2. Execute PDF extraction -> text cleaning -> chunking -> batch vector embedding.
        3. Create DocumentModel with legal & provenance metadata.
        4. Create child DocumentChunkModel records with 384d pgvector vectors.
        5. Atomically commit transaction & return summary.
        """
        if not file_bytes or len(file_bytes) == 0:
            raise ValueError("Uploaded file is empty.")

        meta = metadata or {}
        sha256_hash = self.calculate_sha256(file_bytes)

        # 1. Duplicate detection check via SHA-256 hash
        existing_doc = db.query(DocumentModel).filter(DocumentModel.sha256_hash == sha256_hash).first()
        if existing_doc:
            raise ValueError(
                f"Duplicate document detected: A document with identical content (SHA-256: {sha256_hash[:12]}...) "
                f"already exists under filename '{existing_doc.filename}' (ID: {existing_doc.id})."
            )

        # 2. Extract, clean, chunk, and batch embed PDF
        embedding_result = self.document_service.process_and_embed_pdf_document(file_bytes, filename)

        try:
            # 3. Create parent DocumentModel with legal metadata
            doc_record = DocumentModel(
                filename=filename,
                sha256_hash=sha256_hash,
                title=meta.get("title") or filename,
                document_type=meta.get("document_type") or "OTHER",
                source_url=meta.get("source_url"),
                issuing_authority=meta.get("issuing_authority"),
                publication_date=meta.get("publication_date"),
                effective_from=meta.get("effective_from"),
                effective_to=meta.get("effective_to"),
                financial_year=meta.get("financial_year"),
                document_version=meta.get("document_version") or "1.0",
                description=meta.get("description"),
                is_authoritative=bool(meta.get("is_authoritative", False)),
                status="READY"
            )

            db.add(doc_record)
            db.flush()  # Generate doc_record.id

            # 4. Create child DocumentChunkModel records
            for chunk in embedding_result["chunks"]:
                chunk_record = DocumentChunkModel(
                    document_id=doc_record.id,
                    chunk_id=chunk["chunk_id"],
                    text=chunk["text"],
                    page=chunk["page"],
                    embedding=chunk["embedding"]
                )
                db.add(chunk_record)

            db.commit()
            db.refresh(doc_record)

            return {
                "id": doc_record.id,
                "filename": doc_record.filename,
                "sha256_hash": doc_record.sha256_hash,
                "title": doc_record.title,
                "document_type": doc_record.document_type,
                "source_url": doc_record.source_url,
                "issuing_authority": doc_record.issuing_authority,
                "publication_date": doc_record.publication_date,
                "effective_from": doc_record.effective_from,
                "effective_to": doc_record.effective_to,
                "financial_year": doc_record.financial_year,
                "document_version": doc_record.document_version,
                "description": doc_record.description,
                "is_authoritative": doc_record.is_authoritative,
                "status": doc_record.status,
                "page_count": embedding_result["page_count"],
                "chunk_count": len(doc_record.chunks),
                "created_at": doc_record.created_at.isoformat()
            }

        except Exception as exc:
            db.rollback()
            raise RuntimeError(f"Database transaction failed during document ingestion: {str(exc)}")

    def delete_document(self, db: Session, document_id: int) -> bool:
        """
        Deletes a document and its associated chunks from PostgreSQL by document ID.
        Returns True if deleted, False if not found.
        """
        doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
        if not doc:
            return False

        try:
            db.delete(doc)
            db.commit()
            return True
        except Exception as exc:
            db.rollback()
            raise RuntimeError(f"Failed to delete document with ID {document_id}: {str(exc)}")


# Global singleton DocumentIngestionService instance
document_ingestion_service = DocumentIngestionService()
