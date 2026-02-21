from __future__ import annotations

from typing import Any

from rag.retrieval import run_search_with_model


class RagChatService:
    """
    Wraps the RAG retrieval pipeline for use inside the API.

    Holds pre-loaded index data (FAISS + BM25 + chunks) and the embedding model
    as instance state so they are loaded once at startup and reused across requests.
    """

    def __init__(self, *, index_data: dict[str, Any], model: Any):
        self._index_data = index_data
        self._model = model

    def search(
        self,
        query: str,
        *,
        topk: int = 5,
        mode: str = "hybrid",
        rrf_k: int = 60,
    ) -> dict[str, Any]:
        """
        Run hybrid RAG search (FAISS + BM25 + RRF reranking by default).
        Returns the same dict as run_search_with_model.
        """
        return run_search_with_model(
            index_data=self._index_data,
            model=self._model,
            query=query,
            topk=topk,
            mode=mode,
            rrf_k=rrf_k,
        )
