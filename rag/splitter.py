"""
文本切分：按 markdown 标题分块，超长节再按段落/字符兜底。

split_text 优先按 #/##/### 切分保证小节整块不被腰斩，单节超 chunk_size 时退化为
段落聚合或字符滑窗；chunk_size / overlap 由环境变量配置。
"""
import os
import re


def _int_env(key: str, default: int) -> int:
    """读环境变量为正整数，缺失或非法时回退默认值。"""
    raw_value = os.getenv(key)
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


def _slide(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """纯字符滑窗（带 overlap），仅作无法按结构切分时的兜底。"""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks


def _split_large_section(section: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """单节超过 chunk_size 时：先按段落聚合，段落仍超长再按字符滑窗兜底。"""
    paragraphs = re.split(r"\n\s*\n", section)
    chunks: list[str] = []
    buffer = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        candidate = f"{buffer}\n\n{para}" if buffer else para
        if len(candidate) <= chunk_size:
            buffer = candidate
            continue
        if buffer:
            chunks.append(buffer)
            buffer = ""
        if len(para) <= chunk_size:
            buffer = para
        else:
            chunks.extend(_slide(para, chunk_size, chunk_overlap))
    if buffer:
        chunks.append(buffer)
    return chunks


def split_text(text: str) -> list[str]:
    """按 markdown 标题（# / ## / ### …）切分，保证每个小节（如 ## Qn 问答）整块不被腰斩；
    单节超过 chunk_size 时再按段落/字符兜底切。chunk_size / overlap 由环境变量配置。

    - Q&A 这类结构化文档：每个问答独立成块，检索最精准；
    - 无标题的纯文本：退化为按段落/字符切分（仍比纯字符滑窗更尊重段落边界）。
    """
    chunk_size = _int_env("RAG_CHUNK_SIZE", 800)
    chunk_overlap = _int_env("RAG_CHUNK_OVERLAP", 120)
    cleaned = text.strip()
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]

    # 按行首的 markdown 标题切分（标题留在块首），标题前的引言自成一块
    sections = [s.strip() for s in re.split(r"(?m)(?=^#{1,}\s)", cleaned) if s.strip()]

    chunks: list[str] = []
    for section in sections:
        if len(section) <= chunk_size:
            chunks.append(section)
        else:
            chunks.extend(_split_large_section(section, chunk_size, chunk_overlap))
    return chunks
