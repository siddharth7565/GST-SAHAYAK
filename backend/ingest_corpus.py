"""Load corpus.json (made by scrape_gst.py) into the GST Sahayak Postgres database.

Run from the backend folder, venv active, AFTER the backend has been started once
(so the `documents` and `document_chunks` tables exist) and Postgres is running:

    python ingest_corpus.py

Re-running is safe: each Act's previous rows are deleted and re-inserted.
It writes straight to the tables with SQL (the section chunks do not go through the
PDF endpoint), and embeds with the same model the backend uses.
"""
import hashlib
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/gst_sahayak")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # must match backend/services/embedding_service.py

DOCS = {
    "cgst": {
        "filename": "cgst_act_2017_selected_sections.json",
        "title": "Central Goods and Services Tax Act, 2017 (selected sections)",
        "url": "https://www.advocatekhoj.com/library/bareacts/centralgstact/",
    },
    "igst": {
        "filename": "igst_act_2017_selected_sections.json",
        "title": "Integrated Goods and Services Tax Act, 2017 (selected sections)",
        "url": "https://www.advocatekhoj.com/library/bareacts/integratedgst2017/",
    },
}


def section_as_page(section: str) -> int:
    """document_chunks.page is a required integer; store the section number there ('17A' -> 17)."""
    m = re.match(r"\d+", section)
    return int(m.group()) if m else 0


def main():
    corpus = json.loads(Path("corpus.json").read_text(encoding="utf-8"))
    print(f"{len(corpus)} chunks loaded from corpus.json")

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)
    vectors = model.encode([c["text"] for c in corpus], batch_size=32, normalize_embeddings=True,
                           show_progress_bar=True)
    assert vectors.shape[1] == 384, f"unexpected embedding size {vectors.shape}"

    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        for t in ("documents", "document_chunks"):
            ok = conn.execute(text("SELECT to_regclass(:t)"), {"t": t}).scalar()
            if ok is None:
                raise SystemExit(f"Table '{t}' does not exist. Start the backend once so it creates the tables.")

        col_type = conn.execute(
            text(
                "SELECT udt_name FROM information_schema.columns "
                "WHERE table_name = 'document_chunks' AND column_name = 'embedding'"
            )
        ).scalar()
        use_vector = col_type == "vector"
        cast_type = "vector" if use_vector else "double precision[]"
        open_b, close_b = ("[", "]") if use_vector else ("{", "}")
        print(f"embedding column type in database: {col_type} (inserting as {cast_type})")

        for key, meta in DOCS.items():
            idx = [i for i, c in enumerate(corpus) if c["act_key"] == key]
            if not idx:
                continue
            conn.execute(text("DELETE FROM documents WHERE filename = :f"), {"f": meta["filename"]})
            digest = hashlib.sha256("\n".join(corpus[i]["text"] for i in idx).encode("utf-8")).hexdigest()
            doc_id = conn.execute(
                text(
                    """
                    INSERT INTO documents
                      (filename, sha256_hash, title, document_type, source_url, issuing_authority,
                       publication_date, effective_from, effective_to, financial_year, document_version,
                       description, is_authoritative, status, created_at)
                    VALUES
                      (:filename, :sha, :title, 'ACT', :url, :authority,
                       NULL, '2017-07-01', NULL, NULL, '1.0',
                       :descr, FALSE, 'READY', now())
                    RETURNING id
                    """
                ),
                {
                    "filename": meta["filename"],
                    "sha": digest,
                    "title": meta["title"],
                    "url": meta["url"],
                    "authority": "Parliament of India (text from AdvocateKhoj bare act pages)",
                    "descr": "Selected freelancer-relevant sections, one chunk per sub-section. "
                             "Copied from AdvocateKhoj; not yet verified against the CBIC consolidated text.",
                },
            ).scalar()

            for i in idx:
                c = corpus[i]
                vec = open_b + ",".join(f"{x:.6f}" for x in vectors[i]) + close_b
                conn.execute(
                    text(
                        f"""
                        INSERT INTO document_chunks (document_id, chunk_id, text, page, embedding, created_at)
                        VALUES (:d, :cid, :t, :p, CAST(:e AS {cast_type}), now())
                        """
                    ),
                    {"d": doc_id, "cid": c["chunk_id"], "t": c["text"], "p": section_as_page(c["section"]), "e": vec},
                )
            print(f"inserted document {doc_id} ({key}) with {len(idx)} chunks")

        rows = conn.execute(
            text(
                "SELECT d.id, d.filename, d.status, COUNT(c.id) FROM documents d "
                "LEFT JOIN document_chunks c ON c.document_id = d.id GROUP BY d.id ORDER BY d.id"
            )
        ).all()
    print("documents in database now:")
    for r in rows:
        print("  ", tuple(r))


if __name__ == "__main__":
    main()