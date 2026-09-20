"""
上传文件解析：把二进制文件抽成纯文本，供 RAG 切分入库。
"""
from __future__ import annotations

import os
import tempfile

from utils.logger import setup_logger


logger = setup_logger(__name__)


# 纯文本类后缀：直接按编码解码，保留 # 标记供 MarkdownHeaderTextSplitter 切分
_TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".csv", ".json", ".log"}

# 需要走 langchain loader 的二进制/结构化后缀
_LOADER_SUFFIXES = {".pdf", ".docx", ".doc"}


def _decode_text(data: bytes) -> str:
    """按常见编码依次尝试解码，兜底用 utf-8 容错。"""
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _load_with_loader(filename: str, data: bytes) -> str:
    """落临时文件，按后缀选 langchain loader 解析，拼接 page_content 返回纯文本。

    临时文件保留原后缀：部分 loader（如 PyPDFLoader）靠后缀识别格式。
    loader 在函数内延迟 import，避免模块加载即强依赖 unstructured/pypdf。
    """
    suffix = file_suffix(filename) or ".txt"
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = os.path.join(tmp_dir, f"upload{suffix}")
        with open(tmp_path, "wb") as f:
            f.write(data)

        if suffix == ".pdf":
            from langchain_community.document_loaders import PyPDFLoader

            loader = PyPDFLoader(tmp_path)
        else:  # .docx / .doc
            from langchain_community.document_loaders import UnstructuredWordDocumentLoader

            loader = UnstructuredWordDocumentLoader(tmp_path)

        docs = loader.load()
        return "\n".join(doc.page_content for doc in docs if doc.page_content)


SUPPORTED_SUFFIXES = _TEXT_SUFFIXES | _LOADER_SUFFIXES


def file_suffix(filename: str) -> str:
    """取文件名后缀（含点并小写），无后缀返回空串。"""
    dot_index = filename.rfind(".")
    return filename[dot_index:].lower() if dot_index >= 0 else ""


def is_supported(filename: str) -> bool:
    """判断文件名后缀是否在支持解析的集合内。"""
    return file_suffix(filename) in SUPPORTED_SUFFIXES


def parse_upload(filename: str, data: bytes) -> str:
    """根据文件名后缀选择解析器，把 bytes 抽成纯文本。"""
    suffix = file_suffix(filename)
    if suffix not in _LOADER_SUFFIXES:
        # 纯文本类（含 md，保留 # 标记）直接解码
        return _decode_text(data)

    try:
        return _load_with_loader(filename, data)
    except Exception:
        logger.exception("loader parse failed, filename=%s", filename)
        if suffix == ".doc":
            # 老 .doc 二进制格式 unstructured 同样搞不定，给明确提示
            raise ValueError("legacy .doc 格式暂不支持，请另存为 .docx 后重试") from None
        raise
