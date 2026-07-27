from rag.retriever import init_rag_schema, insert_documents, search_documents
from rag.splitter import split_text
from schemas.rag import RagIngestRequest, RagIngestResponse, RagSearchRequest, RagSearchResponse


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
