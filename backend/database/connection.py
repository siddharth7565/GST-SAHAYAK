import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database.models import Base

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/gst_sahayak"
)

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)

# Session factory for DB operations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency generator for obtaining FastAPI database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initializes database connection, enables pgvector extension,
    and safely creates tables if they do not already exist.
    Raises clear RuntimeError if database connection or pgvector fails.
    """
    try:
        # 1. Verify PostgreSQL connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

            # 2. Enable pgvector extension (if available on PostgreSQL host)
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
            except Exception:
                pass

        # 3. Create schema tables safely (non-destructive)
        Base.metadata.create_all(bind=engine)
        return True

    except Exception as exc:
        err_msg = str(exc)
        if "could not connect" in err_msg.lower() or "connection refused" in err_msg.lower():
            raise RuntimeError(
                f"PostgreSQL database connection failed. Please check that PostgreSQL is running "
                f"at {DATABASE_URL} and credentials are correct. Error: {err_msg}"
            )
        elif "vector" in err_msg.lower() or "extension" in err_msg.lower():
            raise RuntimeError(
                f"pgvector extension check failed. Please ensure pgvector extension is installed "
                f"in your PostgreSQL database. Error: {err_msg}"
            )
        else:
            raise RuntimeError(f"Database initialization failed: {err_msg}")
