"""
RAG 服务层：入库、检索、文件上传解析。

initialize_rag 建表、ingest_rag_documents 切分入库、search_rag_documents 检索、
ingest_uploaded_rag_files 处理多文件上传（大小/类型校验 + 解析 + 切分入库）。
"""
from rag.parsers import is_supported, parse_upload
from rag.retriever import init_rag_schema, insert_documents, search_documents
from rag.splitter import split_text
from schemas.rag import (
    RagIngestRequest,
    RagIngestResponse,
    RagSearchRequest,
    RagSearchResponse,
    RagUploadResponse,
)
from utils.logger import setup_logger


logger = setup_logger(__name__)


MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def initialize_rag() -> dict:
    """初始化 RAG 存储表结构。"""
    return init_rag_schema()


def ingest_rag_documents(request: RagIngestRequest) -> RagIngestResponse:
    """切分文档为片段并写入 RAG 知识库。"""
    documents = []
    for document in request.documents:
        raw_document = document.model_dump()
        for index, chunk in enumerate(split_text(raw_document["content"])):
            documents.append(
                {
                    "content": chunk,
                    "source": raw_document.get("source"),
                    "metadata": {
                        **(raw_document.get("metadata") or {}),
                        "chunk_index": index,
                    },
                }
            )

    result = insert_documents(documents)
    return RagIngestResponse(inserted=result["inserted"])


def search_rag_documents(request: RagSearchRequest) -> RagSearchResponse:
    """按查询检索 RAG 知识库中的相关片段。"""
    rows = search_documents(request.query.strip(), request.top_k)
    return RagSearchResponse(query=request.query.strip(), results=rows)


def ingest_uploaded_rag_files(files: list[dict]) -> RagUploadResponse:
    """处理上传文件：校验大小/类型、解析、切分并入库。"""
    results = []
    total_inserted = 0

    for file in files:
        filename = (file.get("filename") or "upload.txt").strip()
        data = file.get("data") or b""
        source = file.get("source") or filename

        if len(data) == 0:
            results.append({"filename": filename, "skipped": True, "error": "empty file"})
            continue
        if len(data) > MAX_UPLOAD_BYTES:
            results.append({"filename": filename, "skipped": True, "error": "file too large"})
            continue
        if not is_supported(filename):
            results.append({"filename": filename, "skipped": True, "error": "unsupported file type"})
            continue

        try:
            text = parse_upload(filename, data).strip()
        except ValueError as exc:
            results.append({"filename": filename, "skipped": True, "error": str(exc)})
            continue
        except Exception:
            logger.exception("parse upload failed: %s", filename)
            results.append({"filename": filename, "skipped": True, "error": "parse failed"})
            continue
        if not text:
            results.append({"filename": filename, "skipped": True, "error": "no text content"})
            continue

        documents = []
        for index, chunk in enumerate(split_text(text)):
            documents.append(
                {
                    "content": chunk,
                    "source": source,
                    "metadata": {
                        "filename": filename,
                        "content_type": file.get("content_type"),
                        "chunk_index": index,
                    },
                }
            )

        insert_result = insert_documents(documents)
        inserted = int(insert_result["inserted"])
        total_inserted += inserted
        results.append({"filename": filename, "inserted": inserted})

    return RagUploadResponse(inserted=total_inserted, files=results)
