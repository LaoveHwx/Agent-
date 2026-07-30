"""
嵌入模型单例：Ollama bge 向量化。

按环境变量 EMBEDDINGS_MODEL_NAME 实例化 OllamaEmbeddings，
供 RAG 切分入库与检索共用；模型未配置时直接抛错暴露问题。
"""
from langchain_ollama import OllamaEmbeddings

from utils.env_util import embeddings_model_name


def _embedding_model_name() -> str:
    if not embeddings_model_name:
        raise RuntimeError("EMBEDDINGS_MODEL_NAME is not configured")
    return embeddings_model_name


embeddings = OllamaEmbeddings(model=_embedding_model_name())
