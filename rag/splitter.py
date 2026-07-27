import os


def _int_env(key: str, default: int) -> int:
    raw_value = os.getenv(key)
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


def split_text(text: str) -> list[str]:
    chunk_size = _int_env("RAG_CHUNK_SIZE", 800)
    chunk_overlap = _int_env("RAG_CHUNK_OVERLAP", 120)
    cleaned_text = text.strip()

    if len(cleaned_text) <= chunk_size:
        return [cleaned_text] if cleaned_text else []

    chunks: list[str] = []
    start = 0
    while start < len(cleaned_text):
        end = min(start + chunk_size, len(cleaned_text))
        chunk = cleaned_text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned_text):
            break
        start = max(end - chunk_overlap, start + 1)

    return chunks
