from rag.retriever import search_documents


def run_rag_agent(question: str, top_k: int = 5) -> dict:
    try:
        results = search_documents(question, top_k)
        return {"rag_context": results, "errors": []}
    except Exception as exc:
        return {
            "rag_context": [],
            "errors": [f"RAG检索失败: {exc}"],
        }
