"""
RAG 路由：知识库初始化、入库、上传、检索 HTTP 入口。

/init 建表、/documents 批量入库、/upload 多文件上传解析、/search 向量检索；
文件先读取为 bytes 再交 rag_service 处理。
"""
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from schemas.rag import RagIngestRequest, RagIngestResponse, RagSearchRequest, RagSearchResponse, RagUploadResponse
from services.rag_service import ingest_rag_documents, ingest_uploaded_rag_files, initialize_rag, search_rag_documents


rag_router = APIRouter(prefix="/rag")


@rag_router.get("")
async def rag():
    """RAG 模块探活，返回存活状态。"""
    return {"status": "ok", "module": "rag"}


@rag_router.post("/init")
async def init_rag():
    """初始化 RAG 知识库表结构与索引。"""
    try:
        return initialize_rag()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@rag_router.post("/documents", response_model=RagIngestResponse)
async def ingest_documents(request: RagIngestRequest):
    """批量将文档入库到 RAG 知识库。"""
    try:
        return ingest_rag_documents(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@rag_router.post("/upload", response_model=RagUploadResponse)
async def upload_documents(
    files: list[UploadFile] = File(...),
    source: str | None = Form(default=None),
):
    """上传多文件解析后入 RAG 知识库，支持标注来源。"""
    try:
        uploaded_files = []
        for file in files:
            uploaded_files.append(
                {
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "data": await file.read(),
                    "source": source,
                }
            )
        return ingest_uploaded_rag_files(uploaded_files)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@rag_router.post("/search", response_model=RagSearchResponse)
async def search(request: RagSearchRequest):
    """向量检索 RAG 知识库，返回相关文档片段。"""
    try:
        return search_rag_documents(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
