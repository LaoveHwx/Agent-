import os

from models.embeddings import embeddings
from utils.logger import setup_logger


logger = setup_logger(__name__)


def get_embedding_dim() -> int:
    raw_dim = os.getenv("RAG_EMBEDDING_DIM", "1024")
    try:
        return int(raw_dim)
    except ValueError:
        logger.warning("invalid RAG_EMBEDDING_DIM=%s, fallback to 1024", raw_dim)
        return 1024


def embed_text(text: str) -> list[float]:
    return embeddings.embed_query(text)


def to_pgvector(embedding: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"
