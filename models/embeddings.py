from langchain_ollama import OllamaEmbeddings

from utils.env_util import embeddings_model_name


def _embedding_model_name() -> str:
    if not embeddings_model_name:
        raise RuntimeError("EMBEDDINGS_MODEL_NAME is not configured")
    return embeddings_model_name


embeddings = OllamaEmbeddings(model=_embedding_model_name())
