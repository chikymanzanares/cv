# rag/rag_cli/search.py
import argparse
import json
import os
import pickle
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL = "intfloat/multilingual-e5-small"


def load_chunks(chunks_path: Path):
    chunks = []
    with chunks_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def search_faiss(index, chunks, query_vec: np.ndarray, topk: int):
    scores, ids = index.search(query_vec, topk)
    results = []
    for score, idx in zip(scores[0], ids[0]):
        if idx < 0:
            continue
        results.append({"score": float(score), **chunks[idx]})
    return results


def search_bm25(bm25_obj, chunks, query: str, topk: int):
    from rank_bm25 import BM25Okapi
    import re

    word_re = re.compile(r"[A-Za-zÀ-ÿ0-9_+#.-]+")
    tokens = word_re.findall(query.lower())
    scores = bm25_obj.get_scores(tokens)
    top_ids = np.argsort(scores)[::-1][:topk]
    results = []
    for idx in top_ids:
        if scores[idx] > 0:
            results.append({"score": float(scores[idx]), **chunks[idx]})
    return results


def rerank_rrf(faiss_results: list, bm25_results: list, k: int = 60) -> list:
    """
    Reciprocal Rank Fusion: merge two ranked lists by rank position.
    For each doc, RRF_score = 1/(k + rank_faiss) + 1/(k + rank_bm25).
    Docs only in one list get contribution from that list only.
    """
    rrf_scores = {}
    for rank, r in enumerate(faiss_results):
        key = (r["cv_id"], r["chunk_index"])
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
    for rank, r in enumerate(bm25_results):
        key = (r["cv_id"], r["chunk_index"])
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)

    # Build (rrf_score, doc) list; keep full doc from faiss or bm25 (same chunk)
    by_key = {}
    for r in faiss_results:
        key = (r["cv_id"], r["chunk_index"])
        by_key[key] = r
    for r in bm25_results:
        key = (r["cv_id"], r["chunk_index"])
        if key not in by_key:
            by_key[key] = r

    sorted_keys = sorted(rrf_scores.keys(), key=lambda x: -rrf_scores[x])
    return [(rrf_scores[key], by_key[key]) for key in sorted_keys]


def main():
    ap = argparse.ArgumentParser(description="Search the RAG index")
    ap.add_argument("--index_dir", required=True, help="Directory with rag_store indices")
    ap.add_argument("--query", required=True, help="Search query")
    ap.add_argument("--topk", type=int, default=5, help="Number of results")
    ap.add_argument("--mode", choices=["faiss", "bm25", "hybrid", "reranked"], default="hybrid")
    ap.add_argument("--rrf_k", type=int, default=60, help="RRF constant (higher = less weight on rank position)")
    args = ap.parse_args()

    index_dir = Path(args.index_dir)
    faiss_path = index_dir / "faiss.index"
    chunks_path = index_dir / "chunks.jsonl"
    bm25_path = index_dir / "bm25.pkl"

    for p in (faiss_path, chunks_path, bm25_path):
        if not p.exists():
            raise SystemExit(f"Missing index file: {p}. Run 'make -f rag/Makefile index' first.")

    chunks = load_chunks(chunks_path)

    with bm25_path.open("rb") as f:
        bm25_data = pickle.load(f)
    bm25_obj = bm25_data["bm25"]

    faiss_index = faiss.read_index(str(faiss_path))

    model_name = os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL)
    print(f"Loading model: {model_name}")
    st_model = SentenceTransformer(model_name)

    qvec = st_model.encode(
        [f"query: {args.query}"],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")

    # For hybrid/reranked we need a larger candidate pool for RRF
    candidate_k = max(args.topk * 4, 20) if args.mode in ("hybrid", "reranked") else args.topk

    if args.mode in ("faiss", "hybrid", "reranked"):
        faiss_results = search_faiss(faiss_index, chunks, qvec, candidate_k)
    if args.mode in ("bm25", "hybrid", "reranked"):
        bm25_results = search_bm25(bm25_obj, chunks, args.query, candidate_k)

    print(f'\nQuery: "{args.query}"  |  mode={args.mode}  |  topk={args.topk}\n')
    print("=" * 70)

    if args.mode == "faiss":
        print(f"--- FAISS (semantic) ---")
        for r in faiss_results[: args.topk]:
            print(f"  [{r['score']:.4f}] cv_id={r['cv_id']}  chunk={r['chunk_index']}")
            print(f"  {r['text'][:200].replace(chr(10), ' ')}")
            print()
    elif args.mode == "bm25":
        print(f"--- BM25 (keyword) ---")
        for r in bm25_results[: args.topk]:
            print(f"  [{r['score']:.4f}] cv_id={r['cv_id']}  chunk={r['chunk_index']}")
            print(f"  {r['text'][:200].replace(chr(10), ' ')}")
            print()
    elif args.mode in ("hybrid", "reranked"):
        rrf_merged = rerank_rrf(faiss_results, bm25_results, k=args.rrf_k)
        reranked = [doc for _, doc in rrf_merged[: args.topk]]

        if args.mode == "hybrid":
            print(f"--- FAISS (semantic) ---")
            for r in faiss_results[: args.topk]:
                print(f"  [{r['score']:.4f}] cv_id={r['cv_id']}  chunk={r['chunk_index']}")
                print(f"  {r['text'][:200].replace(chr(10), ' ')}")
                print()
            print(f"--- BM25 (keyword) ---")
            for r in bm25_results[: args.topk]:
                print(f"  [{r['score']:.4f}] cv_id={r['cv_id']}  chunk={r['chunk_index']}")
                print(f"  {r['text'][:200].replace(chr(10), ' ')}")
                print()
        print(f"--- Reranked (RRF) ---")
        for i, r in enumerate(reranked, 1):
            rrf_score = rrf_merged[i - 1][0]
            print(f"  [{rrf_score:.4f}] cv_id={r['cv_id']}  chunk={r['chunk_index']}")
            print(f"  {r['text'][:200].replace(chr(10), ' ')}")
            print()

    print("=" * 70)


if __name__ == "__main__":
    main()
