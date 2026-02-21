# rag/rag_cli/search.py — CLI for RAG search. Uses shared logic from rag.retrieval.
import argparse
import os
import sys
from pathlib import Path

from rag.retrieval import DEFAULT_EMBEDDING_MODEL, run_search


def main() -> None:
    ap = argparse.ArgumentParser(description="Search the RAG index")
    ap.add_argument("--index_dir", required=True, help="Directory with rag_store indices")
    ap.add_argument("--query", required=True, help="Search query")
    ap.add_argument("--topk", type=int, default=5, help="Number of results")
    ap.add_argument("--mode", choices=["faiss", "bm25", "hybrid", "reranked"], default="hybrid")
    ap.add_argument("--rrf_k", type=int, default=60, help="RRF constant (higher = less weight on rank position)")
    args = ap.parse_args()

    index_dir = Path(args.index_dir)
    try:
        print(f"Loading model: {os.getenv('EMBEDDING_MODEL', DEFAULT_EMBEDDING_MODEL)}")
        out = run_search(
            index_dir=index_dir,
            query=args.query,
            topk=args.topk,
            mode=args.mode,
            rrf_k=args.rrf_k,
        )
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    mode = out["mode"]
    query = out["query"]
    results = out["results"]
    print(f'\nQuery: "{query}"  |  mode={mode}  |  topk={args.topk}\n')
    print("=" * 70)

    if mode == "faiss":
        print("--- FAISS (semantic) ---")
        for r in results:
            print(f"  [{r['score']:.4f}] cv_id={r['cv_id']}  chunk={r['chunk_index']}")
            print(f"  {r['text'][:200].replace(chr(10), ' ')}")
            print()
    elif mode == "bm25":
        print("--- BM25 (keyword) ---")
        for r in results:
            print(f"  [{r['score']:.4f}] cv_id={r['cv_id']}  chunk={r['chunk_index']}")
            print(f"  {r['text'][:200].replace(chr(10), ' ')}")
            print()
    elif mode in ("hybrid", "reranked"):
        faiss_results = out.get("faiss_results") or []
        bm25_results = out.get("bm25_results") or []
        rrf_merged = out.get("reranked") or []
        if mode == "hybrid":
            print("--- FAISS (semantic) ---")
            for r in faiss_results[: args.topk]:
                print(f"  [{r['score']:.4f}] cv_id={r['cv_id']}  chunk={r['chunk_index']}")
                print(f"  {r['text'][:200].replace(chr(10), ' ')}")
                print()
            print("--- BM25 (keyword) ---")
            for r in bm25_results[: args.topk]:
                print(f"  [{r['score']:.4f}] cv_id={r['cv_id']}  chunk={r['chunk_index']}")
                print(f"  {r['text'][:200].replace(chr(10), ' ')}")
                print()
        print("--- Reranked (RRF) ---")
        for i, r in enumerate(results, 1):
            rrf_score = rrf_merged[i - 1][0] if i <= len(rrf_merged) else 0.0
            print(f"  [{rrf_score:.4f}] cv_id={r['cv_id']}  chunk={r['chunk_index']}")
            print(f"  {r['text'][:200].replace(chr(10), ' ')}")
            print()

    print("=" * 70)


if __name__ == "__main__":
    main()
