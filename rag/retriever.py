"""
RAG 检索与入库：pgvector 向量表的建表、写入、检索。

init_rag_schema 开 vector 扩展与 ivfflat 索引；insert_documents 批量向量化入库；
search_documents 优先向量余弦检索，异常降级 ILIKE 关键词检索。
"""
from typing import Any

from psycopg.types.json import Jsonb

from rag.embedding import embed_text, get_embedding_dim, to_pgvector
from utils.logger import setup_logger
from utils.postgres_pool import get_connection


logger = setup_logger(__name__)


def init_rag_schema() -> dict[str, Any]:
    """
    初始化RAG所需pgvector表结构，开启vector扩展，
    创建rag_documents向量表与ivfflat向量索引，
    返回初始化状态、向量维度和表名
    """
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
                logger.exception("pgvector 索引创建失败")
            conn.commit()

    return {"status": "ok", "embedding_dim": dim, "table": "rag_documents"}


def insert_documents(documents: list[dict[str, Any]]) -> dict[str, Any]:
    """
    批量写入文档到rag_documents向量表，自动生成文本向量，
    跳过空内容文档，返回成功插入文档数量
    """
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
    """
    向量相似度检索文档；优先执行向量余弦距离搜索，
    异常降级为ILIKE模糊关键词检索，返回top_k匹配文档列表，携带score相似度分数
    """
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
