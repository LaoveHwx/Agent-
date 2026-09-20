"""
文本切分：用 langchain 的 splitter 组合，保留原"标题整块不腰斩"语义。
"""
import os

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


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


# 按 markdown 标题切的层级配置：标题层级 -> metadata 键名
_HEADERS_TO_SPLIT_ON = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]


def split_text(text: str) -> list[str]:
    """按 markdown 标题切分，超长节再用 RecursiveCharacterTextSplitter 兜底。

    - 有标题的结构化文档：每个小节（如 ## Qn 问答）先整块成 Document，超长再切；
    - 无标题的纯文本：MarkdownHeaderTextSplitter 会把整段当一个 Document，
      交由 RecursiveCharacterTextSplitter 按 chunk_size 切，等价于原段落/字符兜底。
    """
    chunk_size = _int_env("RAG_CHUNK_SIZE", 800)
    chunk_overlap = _int_env("RAG_CHUNK_OVERLAP", 120)
    cleaned = text.strip()
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]

    # 1) 按 markdown 标题切，保证小节整块不被腰斩
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=_HEADERS_TO_SPLIT_ON)
    md_chunks = md_splitter.split_text(cleaned)

    # 2) 超长节再按字符递归切分（分隔符优先级：段落 > 换行 > 空格 > 字符）
    rc_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    final_docs = rc_splitter.split_documents(md_chunks)

    return [doc.page_content for doc in final_docs if doc.page_content and doc.page_content.strip()]
