# rag/rag_cli/search.py
import argparse
import json
import os
import pickle
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


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


def main():
    ap = argparse.ArgumentParser(description="Search the RAG index")
    ap.add_argument("--index_dir", required=True, help="Directory with rag_store indices")
    ap.add_argument("--query", required=True, help="Search query")
    ap.add_argument("--topk", type=int, default=5, help="Number of results")
    ap.add_argument("--mode", choices=["faiss", "bm25", "hybrid"], default="hybrid")
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
        [args.query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")

    print(f'\nQuery: "{args.query}"  |  mode={args.mode}  |  topk={args.topk}\n')
    print("=" * 70)

    if args.mode in ("faiss", "hybrid"):
        faiss_results = search_faiss(faiss_index, chunks, qvec, args.topk)
        print(f"--- FAISS (semantic) ---")
        for r in faiss_results:
            print(f"  [{r['score']:.4f}] cv_id={r['cv_id']}  chunk={r['chunk_index']}")
            print(f"  {r['text'][:200].replace(chr(10), ' ')}")
            print()

    if args.mode in ("bm25", "hybrid"):
        bm25_results = search_bm25(bm25_obj, chunks, args.query, args.topk)
        print(f"--- BM25 (keyword) ---")
        for r in bm25_results:
            print(f"  [{r['score']:.4f}] cv_id={r['cv_id']}  chunk={r['chunk_index']}")
            print(f"  {r['text'][:200].replace(chr(10), ' ')}")
            print()

    print("=" * 70)


if __name__ == "__main__":
    main()
