from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.types import TypeDecorator, ARRAY, Float
try:
    from pgvector.sqlalchemy import Vector as PgVector
    # Check if pgvector extension is supported on the target DB host
    from database.connection import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).fetchone()
        if res:
            Vector = PgVector
        else:
            class SafeVector(TypeDecorator):
                impl = ARRAY(Float)
                def __init__(self, dim=384):
                    super().__init__()
                    self.dim = dim
            Vector = SafeVector
except Exception:
    class SafeVector(TypeDecorator):
        impl = ARRAY(Float)
        def __init__(self, dim=384):
            super().__init__()
            self.dim = dim
    Vector = SafeVector

Base = declarative_base()


class DocumentModel(Base):
    """
    SQLAlchemy model representing an ingested GST document with full legal metadata,
    source provenance, SHA-256 hash for duplicate detection, and processing status.
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    sha256_hash = Column(String(64), unique=True, nullable=False, index=True)

    # Legal & Provenance Metadata
    title = Column(String(500), nullable=True)
    document_type = Column(String(50), nullable=False, default="OTHER")
    source_url = Column(Text, nullable=True)
    issuing_authority = Column(String(255), nullable=True)

    # Time & Versioning Metadata
    publication_date = Column(String(50), nullable=True)
    effective_from = Column(String(50), nullable=True)
    effective_to = Column(String(50), nullable=True)
    financial_year = Column(String(20), nullable=True)
    document_version = Column(String(50), nullable=True, default="1.0")

    # Legal Status & Authority Flags
    description = Column(Text, nullable=True)
    is_authoritative = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="READY")  # PENDING, PROCESSING, READY, FAILED

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # One-to-many relationship with chunks
    chunks = relationship("DocumentChunkModel", back_populates="document", cascade="all, delete-orphan")


class DocumentChunkModel(Base):
    """
    SQLAlchemy model representing a document chunk attached with a 384-dimensional embedding vector.
    """
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(String(255), nullable=False, index=True)
    text = Column(Text, nullable=False)
    page = Column(Integer, nullable=False)
    embedding = Column(Vector(384), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship back to parent document
    document = relationship("DocumentModel", back_populates="chunks")
