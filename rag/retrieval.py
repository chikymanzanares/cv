# rag/retrieval.py — Shared retrieval logic for CLI and API.
# Used by rag.rag_cli.search and (later) FastAPI endpoints.
import json
import os
import pickle
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
BM25_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9_+#.-]+")


def load_chunks(chunks_path: Path) -> List[Dict[str, Any]]:
    chunks = []
    with chunks_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def load_index(index_dir: Path) -> Dict[str, Any]:
    """Load FAISS index, chunks metadata, and BM25 object from index_dir."""
    faiss_path = index_dir / "faiss.index"
    chunks_path = index_dir / "chunks.jsonl"
    bm25_path = index_dir / "bm25.pkl"
    for p in (faiss_path, chunks_path, bm25_path):
        if not p.exists():
            raise FileNotFoundError(f"Missing index file: {p}. Run 'make -f rag/Makefile index' first.")
    chunks = load_chunks(chunks_path)
    with bm25_path.open("rb") as f:
        bm25_data = pickle.load(f)
    faiss_index = faiss.read_index(str(faiss_path))
    return {
        "faiss_index": faiss_index,
        "chunks": chunks,
        "bm25": bm25_data["bm25"],
    }


def search_faiss(
    index: faiss.Index,
    chunks: List[Dict[str, Any]],
    query_vec: np.ndarray,
    topk: int,
) -> List[Dict[str, Any]]:
    scores, ids = index.search(query_vec, topk)
    results = []
    for score, idx in zip(scores[0], ids[0]):
        if idx < 0:
            continue
        results.append({"score": float(score), **chunks[idx]})
    return results


def search_bm25(
    bm25_obj: Any,
    chunks: List[Dict[str, Any]],
    query: str,
    topk: int,
) -> List[Dict[str, Any]]:
    tokens = BM25_WORD_RE.findall(query.lower())
    scores = bm25_obj.get_scores(tokens)
    top_ids = np.argsort(scores)[::-1][:topk]
    results = []
    for idx in top_ids:
        if scores[idx] > 0:
            results.append({"score": float(scores[idx]), **chunks[idx]})
    return results


def rerank_rrf(
    faiss_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    k: int = 60,
) -> List[Tuple[float, Dict[str, Any]]]:
    """
    Reciprocal Rank Fusion: merge two ranked lists by rank position.
    Returns list of (rrf_score, doc) sorted by score descending.
    """
    rrf_scores: Dict[Tuple[str, int], float] = {}
    for rank, r in enumerate(faiss_results):
        key = (r["cv_id"], r["chunk_index"])
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
    for rank, r in enumerate(bm25_results):
        key = (r["cv_id"], r["chunk_index"])
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)

    by_key: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for r in faiss_results:
        key = (r["cv_id"], r["chunk_index"])
        by_key[key] = r
    for r in bm25_results:
        key = (r["cv_id"], r["chunk_index"])
        if key not in by_key:
            by_key[key] = r

    sorted_keys = sorted(rrf_scores.keys(), key=lambda x: -rrf_scores[x])
    return [(rrf_scores[key], by_key[key]) for key in sorted_keys]


def run_search(
    index_dir: Path,
    query: str,
    topk: int = 5,
    mode: str = "hybrid",
    rrf_k: int = 60,
    embedding_model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run search over the RAG index. Single entry point for both CLI and API.

    Returns a dict with:
      - "results": main result list (reranked if mode in hybrid/reranked, else faiss or bm25)
      - "faiss_results": list or None (set when mode in hybrid/reranked)
      - "bm25_results": list or None (set when mode in hybrid/reranked)
      - "reranked": list of (score, doc) or None (set when mode in hybrid/reranked)
    """
    index_dir = Path(index_dir)
    data = load_index(index_dir)
    faiss_index = data["faiss_index"]
    chunks = data["chunks"]
    bm25_obj = data["bm25"]

    model_name = embedding_model or os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    st_model = SentenceTransformer(model_name)
    qvec = st_model.encode(
        [f"query: {query}"],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")

    candidate_k = max(topk * 4, 20) if mode in ("hybrid", "reranked") else topk
    faiss_results: Optional[List[Dict[str, Any]]] = None
    bm25_results: Optional[List[Dict[str, Any]]] = None
    rrf_merged: Optional[List[Tuple[float, Dict[str, Any]]]] = None

    if mode in ("faiss", "hybrid", "reranked"):
        faiss_results = search_faiss(faiss_index, chunks, qvec, candidate_k)
    if mode in ("bm25", "hybrid", "reranked"):
        bm25_results = search_bm25(bm25_obj, chunks, query, candidate_k)

    if mode in ("hybrid", "reranked") and faiss_results is not None and bm25_results is not None:
        rrf_merged = rerank_rrf(faiss_results, bm25_results, k=rrf_k)
        main_results = [doc for _, doc in rrf_merged[:topk]]
    elif mode == "faiss" and faiss_results is not None:
        main_results = faiss_results[:topk]
    elif mode == "bm25" and bm25_results is not None:
        main_results = bm25_results[:topk]
    else:
        main_results = []

    return {
        "query": query,
        "mode": mode,
        "topk": topk,
        "results": main_results,
        "faiss_results": faiss_results,
        "bm25_results": bm25_results,
        "reranked": rrf_merged,
    }
