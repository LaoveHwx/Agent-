from rag.retriever import init_rag_schema, insert_documents, search_documents
from rag.splitter import split_text
from schemas.rag import (
    RagIngestRequest,
    RagIngestResponse,
    RagSearchRequest,
    RagSearchResponse,
    RagUploadResponse,
)


SUPPORTED_UPLOAD_SUFFIXES = {".txt", ".md", ".csv", ".json", ".log"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024


def initialize_rag() -> dict:
    return init_rag_schema()


def ingest_rag_documents(request: RagIngestRequest) -> RagIngestResponse:
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
    rows = search_documents(request.query.strip(), request.top_k)
    return RagSearchResponse(query=request.query.strip(), results=rows)


def _file_suffix(filename: str) -> str:
    dot_index = filename.rfind(".")
    return filename[dot_index:].lower() if dot_index >= 0 else ""


def _decode_upload(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def ingest_uploaded_rag_files(files: list[dict]) -> RagUploadResponse:
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
        if _file_suffix(filename) not in SUPPORTED_UPLOAD_SUFFIXES:
            results.append({"filename": filename, "skipped": True, "error": "unsupported file type"})
            continue

        text = _decode_upload(data).strip()
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
