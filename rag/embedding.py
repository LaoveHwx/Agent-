import hashlib
import math
import os

import requests
from openai import OpenAI

from utils.env_util import api_key, base_url, embeddings_model_name
from utils.logger import setup_logger


logger = setup_logger(__name__)
_embedding_api_disabled = False
_ollama_embedding_disabled = False


def get_embedding_dim() -> int:
    raw_dim = os.getenv("RAG_EMBEDDING_DIM", "1024")
    try:
        return int(raw_dim)
    except ValueError:
        logger.warning("invalid RAG_EMBEDDING_DIM=%s, fallback to 1024", raw_dim)
        return 1024


def _hash_embedding(text: str, dim: int) -> list[float]:
    values: list[float] = []
    seed = text.encode("utf-8")
    counter = 0

    while len(values) < dim:
        digest = hashlib.sha256(seed + str(counter).encode("utf-8")).digest()
        for byte in digest:
            values.append((byte / 255.0) * 2 - 1)
            if len(values) >= dim:
                break
        counter += 1

    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


def _looks_like_ollama_model(model: str) -> bool:
    return (
        model.endswith(":latest")
        or model.startswith("modelscope.cn/")
        or model in {"nomic-embed-text"}
    )


def _ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


def _embed_with_ollama(text: str, model: str) -> list[float]:
    response = requests.post(
        f"{_ollama_base_url()}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    embedding = data.get("embedding")
    if not embedding:
        raise RuntimeError("Ollama embedding response missing embedding field")
    return embedding


def embed_text(text: str) -> list[float]:
    global _embedding_api_disabled, _ollama_embedding_disabled

    dim = get_embedding_dim()

    if embeddings_model_name and not _ollama_embedding_disabled and _looks_like_ollama_model(embeddings_model_name):
        try:
            return _embed_with_ollama(text, embeddings_model_name)
        except Exception as exc:
            _ollama_embedding_disabled = True
            logger.warning("ollama embedding failed, fallback to openai-compatible embedding: %s", exc)

    if api_key and base_url and embeddings_model_name and not _embedding_api_disabled:
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.embeddings.create(
                model=embeddings_model_name,
                input=text,
            )
            return response.data[0].embedding
        except Exception as exc:
            _embedding_api_disabled = True
            logger.warning("embedding api failed, fallback to local hash embedding: %s", exc)

    return _hash_embedding(text, dim)


def to_pgvector(embedding: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"
