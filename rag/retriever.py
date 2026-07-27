from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from rag.embedding import embed_text, get_embedding_dim, to_pgvector
from utils.env_util import connection_string, connectioned_string, ps_dsn
from utils.logger import setup_logger


logger = setup_logger(__name__)


def _dsn() -> str:
    dsn = ps_dsn or connection_string or connectioned_string
    if not dsn:
        raise RuntimeError("PostgreSQL DSN is not configured. Please set PS_DSN in .env")
    return dsn


def get_connection():
    return psycopg.connect(_dsn(), row_factory=dict_row)


def init_rag_schema() -> dict[str, Any]:
    dim = get_embedding_dim()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS rag_documents (
                    id BIGSERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT,
                    metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    embedding vector({dim}) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            try:
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_rag_documents_embedding
                    ON rag_documents USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                    """
                )
            except Exception:
                logger.exception("pgvector index creation failed")
            conn.commit()

    return {"status": "ok", "embedding_dim": dim, "table": "rag_documents"}


def insert_documents(documents: list[dict[str, Any]]) -> dict[str, Any]:
    if not documents:
        return {"inserted": 0}

    init_rag_schema()
    inserted = 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            for document in documents:
                content = document["content"].strip()
                if not content:
                    continue

                embedding = to_pgvector(embed_text(content))
                cur.execute(
                    """
                    INSERT INTO rag_documents (content, source, metadata, embedding)
                    VALUES (%s, %s, %s, %s::vector)
                    """,
                    (
                        content,
                        document.get("source"),
                        Jsonb(document.get("metadata") or {}),
                        embedding,
                    ),
                )
                inserted += 1
            conn.commit()

    return {"inserted": inserted}


def search_documents(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    init_rag_schema()
    query_embedding = to_pgvector(embed_text(query))

    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("SET LOCAL enable_indexscan = off")
                cur.execute("SET LOCAL enable_bitmapscan = off")
                cur.execute(
                    """
                    SELECT
                        id,
                        content,
                        source,
                        metadata,
                        1 - (embedding <=> %s::vector) AS score,
                        embedding <=> %s::vector AS distance
                    FROM rag_documents
                    ORDER BY distance
                    LIMIT %s
                    """,
                    (query_embedding, query_embedding, top_k),
                )
                return list(cur.fetchall())
            except Exception:
                logger.exception("vector search failed, fallback to keyword search")
                conn.rollback()
                cur.execute(
                    """
                    SELECT id, content, source, metadata, 0.0 AS score
                    FROM rag_documents
                    WHERE content ILIKE %s
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (f"%{query}%", top_k),
                )
                return list(cur.fetchall())
