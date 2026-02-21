# rag/rag_cli/build_index.py
import argparse
import hashlib
import json
import os
import pickle
import re
from pathlib import Path
from typing import Any, Dict, List

import fitz  # PyMuPDF
import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9_+#.-]+")
DEFAULT_MODEL = "intfloat/multilingual-e5-small"


def tokenize(text: str) -> List[str]:
    return WORD_RE.findall(text.lower())


def extract_text_from_pdf(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    parts: List[str] = []
    for page in doc:
        parts.append(page.get_text("text"))
    doc.close()
    return "\n".join(parts).strip()


def chunk_text(text: str, chunk_chars: int = 1800, overlap_chars: int = 250) -> List[str]:
    """Simple chunker by characters (robust + no tokenizer dependency)."""
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_chars, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start = max(0, end - overlap_chars)
    return chunks


def file_fingerprint(paths: List[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        st = p.stat()
        h.update(str(p).encode("utf-8"))
        h.update(str(int(st.st_mtime)).encode("utf-8"))
        h.update(str(st.st_size).encode("utf-8"))
    return h.hexdigest()


def ensure_out_dir(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf_dir", required=True, help="Directory with CV PDFs")
    ap.add_argument("--out_dir", required=True, help="Directory to persist indices")
    ap.add_argument("--chunk_chars", type=int, default=500)
    ap.add_argument("--overlap_chars", type=int, default=50)
    ap.add_argument("--batch_size", type=int, default=64)
    ap.add_argument("--force", action="store_true", help="Rebuild even if unchanged")
    args = ap.parse_args()

    pdf_dir = Path(args.pdf_dir)
    out_dir = Path(args.out_dir)

    model_name = os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL)

    ensure_out_dir(out_dir)

    # CVs live in subdirs: cv_generation/data/cvs/cv_001/cv.pdf, cv_002/cv.pdf, ...
    pdf_paths = sorted(pdf_dir.glob("*/cv.pdf"))
    if not pdf_paths:
        pdf_paths = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_paths:
        raise SystemExit(f"No PDFs found in {pdf_dir.resolve()}")

    manifest_path = out_dir / "manifest.json"
    current_fp = file_fingerprint(pdf_paths)

    if manifest_path.exists() and not args.force:
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if old.get("fingerprint") == current_fp:
            print("No changes detected. Skipping rebuild (use --force to rebuild).")
            return

    print(f"Found {len(pdf_paths)} PDFs. Extracting text + chunking...")

    records: List[Dict[str, Any]] = []
    all_texts: List[str] = []
    all_tokens: List[List[str]] = []

    chunk_id = 0
    for pdf_path in tqdm(pdf_paths, desc="PDFs"):
        cv_id = pdf_path.parent.name if pdf_path.parent != pdf_dir else pdf_path.stem
        text = extract_text_from_pdf(pdf_path)
        chunks = chunk_text(text, chunk_chars=args.chunk_chars, overlap_chars=args.overlap_chars)

        for i, ch in enumerate(chunks):
            rec = {
                "chunk_id": chunk_id,
                "cv_id": cv_id,
                "pdf_path": str(pdf_path),
                "chunk_index": i,
                "text": ch,
            }
            records.append(rec)
            all_texts.append(ch)
            all_tokens.append(tokenize(ch))
            chunk_id += 1

    if not records:
        raise SystemExit("No chunks produced. Check PDF text extraction.")

    print(f"Total chunks: {len(records)}")

    # BM25
    print("Building BM25 index...")
    bm25 = BM25Okapi(all_tokens)

    # FAISS with local SentenceTransformer (no API needed)
    print(f"Loading embedding model: {model_name} ...")
    embedder = SentenceTransformer(model_name)

    print("Embedding chunks + building FAISS index...")
    vectors: List[np.ndarray] = []
    for i in tqdm(range(0, len(all_texts), args.batch_size), desc="Embedding"):
        batch = all_texts[i : i + args.batch_size]
        passages = [f"passage: {t}" for t in batch]
        vec = embedder.encode(passages, show_progress_bar=False, convert_to_numpy=True)
        vectors.append(vec.astype("float32"))

    X = np.vstack(vectors).astype("float32")
    faiss.normalize_L2(X)

    dim = X.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(X)

    faiss_path = out_dir / "faiss.index"
    chunks_path = out_dir / "chunks.jsonl"
    bm25_path = out_dir / "bm25.pkl"

    print(f"Saving FAISS index: {faiss_path}")
    faiss.write_index(index, str(faiss_path))

    print(f"Saving chunks metadata: {chunks_path}")
    with chunks_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Saving BM25 object: {bm25_path}")
    with bm25_path.open("wb") as f:
        pickle.dump({"bm25": bm25, "chunk_count": len(records)}, f)

    manifest = {
        "fingerprint": current_fp,
        "pdf_count": len(pdf_paths),
        "chunk_count": len(records),
        "embedding_model": model_name,
        "dim": int(dim),
        "chunk_chars": args.chunk_chars,
        "overlap_chars": args.overlap_chars,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved manifest: {manifest_path}")
    print("✅ Done.")


if __name__ == "__main__":
    main()
