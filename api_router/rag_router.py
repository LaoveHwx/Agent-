from fastapi import APIRouter, HTTPException

from schemas.rag import RagIngestRequest, RagIngestResponse, RagSearchRequest, RagSearchResponse
from services.rag_service import ingest_rag_documents, initialize_rag, search_rag_documents


rag_router = APIRouter(prefix="/rag")


@rag_router.get("")
async def rag():
    return {"status": "ok", "module": "rag"}


@rag_router.post("/init")
async def init_rag():
    try:
        return initialize_rag()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@rag_router.post("/documents", response_model=RagIngestResponse)
async def ingest_documents(request: RagIngestRequest):
    try:
        return ingest_rag_documents(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@rag_router.post("/search", response_model=RagSearchResponse)
async def search(request: RagSearchRequest):
    try:
        return search_rag_documents(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
