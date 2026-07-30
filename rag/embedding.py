"""
嵌入工具：维度读取 + 文本向量化 + pgvector 格式化。

get_embedding_dim 读环境变量并兜底 1024；embed_text 调 Ollama 嵌入；
to_pgvector 把浮点向量格式化为 pgvector 方括号字符串。
"""
import os

from models.embeddings import embeddings
from utils.logger import setup_logger


logger = setup_logger(__name__)


def get_embedding_dim() -> int:
    """
    读取环境变量RAG_EMBEDDING_DIM获取向量模型维度，
    解析异常告警并回退1024，返回向量维度整数
    """
    raw_dim = os.getenv("RAG_EMBEDDING_DIM", "1024")
    try:
        return int(raw_dim)
    except ValueError:
        logger.warning("invalid RAG_EMBEDDING_DIM=%s, fallback to 1024", raw_dim)
        return 1024


def embed_text(text: str) -> list[float]:
    """调嵌入模型把文本转向量。"""
    return embeddings.embed_query(text)


def to_pgvector(embedding: list[float]) -> str:
    """
    将float类型向量列表格式化为pgvector要求的格式：方括号字符串，
    保留8位小数，返回格式化后的向量字符串
    """
    return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"
