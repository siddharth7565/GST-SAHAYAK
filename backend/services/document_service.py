import io
import re
from pypdf import PdfReader
from pypdf.errors import PdfReadError, PyPdfError
from services.embedding_service import embedding_service

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150


class DocumentService:
    """Service layer for PDF text extraction, text cleaning, page-aware chunking, and chunk embedding."""

    def __init__(self, default_chunk_size: int = DEFAULT_CHUNK_SIZE, default_chunk_overlap: int = DEFAULT_CHUNK_OVERLAP):
        self.default_chunk_size = default_chunk_size
        self.default_chunk_overlap = default_chunk_overlap

    def clean_text(self, text: str) -> str:
        """
        Cleans extracted PDF text without modifying legal terms, numbers, or wording.
        - Normalizes newlines and carriage returns.
        - Replaces non-breaking spaces and multiple horizontal spaces with a single space.
        - Limits consecutive newlines to at most 2 (preserving paragraph structure).
        """
        if not text:
            return ""

        # Normalize carriage returns
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n")

        # Replace non-breaking space and multiple horizontal spaces/tabs with single space
        cleaned = re.sub(r"[ \t\xa0]+", " ", cleaned)

        # Normalize 3+ newlines to 2 newlines (paragraph boundary)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        # Clean leading/trailing space per line
        lines = [line.strip() for line in cleaned.split("\n")]
        cleaned = "\n".join(lines)

        return cleaned.strip()

    def chunk_page_text(
        self,
        text: str,
        page_number: int,
        filename: str,
        chunk_size: int = None,
        chunk_overlap: int = None
    ) -> list:
        """
        Splits page text into deterministic chunks with specified size and overlap.
        Preserves page number, original filename, assigns unique chunk IDs, and
        aligns both start and end boundaries to word/whitespace boundaries.
        """
        cleaned = self.clean_text(text)
        if not cleaned:
            return []

        c_size = chunk_size or self.default_chunk_size
        c_overlap = chunk_overlap or self.default_chunk_overlap

        # Ensure overlap is less than chunk size
        if c_overlap >= c_size:
            c_overlap = max(0, c_size - 50)

        # Clean filename stem for chunk_id (e.g., sample_gst_notice.pdf -> sample_gst_notice)
        stem = re.sub(r"[^a-zA-Z0-9_]", "_", filename.rsplit(".", 1)[0])

        total_length = len(cleaned)

        # If page text fits into a single chunk
        if total_length <= c_size:
            return [{
                "chunk_id": f"{stem}_p{page_number}_c1",
                "text": cleaned,
                "page": page_number,
                "document": filename
            }]

        chunks = []
        step = max(1, c_size - c_overlap)
        start = 0
        chunk_idx = 1

        while start < total_length:
            end = min(total_length, start + c_size)
            chunk_str = cleaned[start:end]

            # Adjust end boundary to nearest space or newline if not at end of text
            if end < total_length:
                last_space = chunk_str.rfind(" ")
                last_newline = chunk_str.rfind("\n")
                break_point = max(last_space, last_newline)
                if break_point > int(c_size * 0.7):
                    end = start + break_point
                    chunk_str = cleaned[start:end]

            chunk_str = chunk_str.strip()
            if chunk_str:
                chunk_id = f"{stem}_p{page_number}_c{chunk_idx}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": chunk_str,
                    "page": page_number,
                    "document": filename
                })
                chunk_idx += 1

            # Determine next start boundary aligned to nearest word boundary near target_start
            target_start = start + step
            if target_start >= total_length:
                break

            search_min = max(start + 1, target_start - 40)
            search_max = min(total_length, target_start + 40)

            space_pos = -1
            for pos in range(target_start, search_min - 1, -1):
                if cleaned[pos] in (" ", "\n"):
                    space_pos = pos
                    break

            if space_pos == -1:
                for pos in range(target_start + 1, search_max):
                    if cleaned[pos] in (" ", "\n"):
                        space_pos = pos
                        break

            if space_pos != -1:
                next_start = space_pos + 1
            else:
                next_start = target_start

            if next_start <= start:
                next_start = start + 1

            start = next_start

        return chunks

    def extract_pdf_text(self, file_bytes: bytes, filename: str) -> dict:
        """Extracts text page-by-page from raw PDF bytes."""
        if not file_bytes or len(file_bytes) == 0:
            raise ValueError("Uploaded file is empty.")

        try:
            pdf_stream = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_stream)

            if reader.is_encrypted:
                try:
                    decrypted = reader.decrypt("")
                    if not decrypted:
                        raise ValueError("PDF is encrypted and password-protected.")
                except Exception:
                    raise ValueError("Encrypted PDF files are not supported.")

            page_count = len(reader.pages)
            if page_count == 0:
                raise ValueError("PDF contains 0 pages.")

            extracted_pages = []
            for idx, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                extracted_pages.append({
                    "page": idx,
                    "text": page_text.strip()
                })

            return {
                "filename": filename,
                "page_count": page_count,
                "pages": extracted_pages
            }

        except (PdfReadError, PyPdfError) as exc:
            raise ValueError(f"Failed to read PDF file: Corrupted or invalid PDF format ({str(exc)}).")
        except ValueError as exc:
            raise exc
        except Exception as exc:
            raise ValueError(f"An error occurred while processing the PDF: {str(exc)}")

    def process_pdf_document(
        self,
        file_bytes: bytes,
        filename: str,
        chunk_size: int = None,
        chunk_overlap: int = None
    ) -> dict:
        """
        Executes full extraction -> cleaning -> chunking pipeline on a PDF file.
        """
        extraction = self.extract_pdf_text(file_bytes, filename)
        all_chunks = []

        for page_data in extraction["pages"]:
            cleaned_text = self.clean_text(page_data["text"])
            page_chunks = self.chunk_page_text(
                text=cleaned_text,
                page_number=page_data["page"],
                filename=filename,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            all_chunks.extend(page_chunks)

        return {
            "filename": filename,
            "page_count": extraction["page_count"],
            "chunk_count": len(all_chunks),
            "chunks": all_chunks
        }

    def process_and_embed_pdf_document(
        self,
        file_bytes: bytes,
        filename: str,
        chunk_size: int = None,
        chunk_overlap: int = None
    ) -> dict:
        """
        Executes extraction -> cleaning -> chunking -> batch embedding pipeline.
        Attaches numerical embedding vectors to every chunk object while preserving all metadata.
        """
        processing_result = self.process_pdf_document(
            file_bytes=file_bytes,
            filename=filename,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        chunks = processing_result["chunks"]
        if not chunks:
            raise ValueError("Document produced zero chunks to embed.")

        chunk_texts = [c["text"] for c in chunks]

        # Batch embed all chunk texts in a single call
        embeddings = embedding_service.embed_texts(chunk_texts)

        # Strict alignment verification
        if len(embeddings) != len(chunks):
            raise RuntimeError(
                f"Embedding count mismatch: generated {len(embeddings)} embeddings for {len(chunks)} chunks."
            )

        embedded_chunks = []
        for chunk_dict, emb in zip(chunks, embeddings):
            embedded_chunks.append({
                "chunk_id": chunk_dict["chunk_id"],
                "text": chunk_dict["text"],
                "page": chunk_dict["page"],
                "document": chunk_dict["document"],
                "embedding": emb
            })

        return {
            "filename": filename,
            "page_count": processing_result["page_count"],
            "chunk_count": len(embedded_chunks),
            "embedding_dimension": embedding_service.get_dimension(),
            "chunks": embedded_chunks
        }


# Global DocumentService instance
document_service = DocumentService()
