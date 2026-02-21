# RAG Pipeline

Offline indexing and search for synthetic CV documents.

Uses a **hybrid retrieval** strategy combining:
- **FAISS** — dense vector search (semantic similarity)
- **BM25** — sparse keyword search (exact term matching)

Both indices are built from the same text chunks extracted from the CV PDFs.

---

## Architecture

```
cv_generation/data/cvs/
  cv_001/cv.pdf
  cv_002/cv.pdf
  ...
        │
        ▼
  build_index.py
        │
        ├── Extract text (PyMuPDF)
        ├── Chunk text (char-level, configurable size + overlap)
        ├── Build BM25 index  ──────────────► rag_store/bm25.pkl
        └── Embed + build FAISS index ──────► rag_store/faiss.index
                                              rag_store/chunks.jsonl
                                              rag_store/manifest.json
```

---

## Quickstart

```bash
# Build Docker image (once, or after changing requirements-rag.txt)
make -f rag/Makefile build

# Build indices from PDFs
make -f rag/Makefile index

# Search
make -f rag/Makefile search Q="Who has experience with Jenkins?"

# Force reindex (even if PDFs haven't changed)
make -f rag/Makefile rebuild
```

---

## Indexing (`build_index.py`)

### 1. PDF text extraction

Each CV lives in its own subdirectory:

```
cv_generation/data/cvs/cv_001/cv.pdf
cv_generation/data/cvs/cv_002/cv.pdf
...
```

Text is extracted page by page using **PyMuPDF** (`fitz`) and joined into a single string per CV.

### 2. Chunking

The full text of each CV is split into overlapping character-level chunks:

```
chunk_chars   = 500  (default, configurable via --chunk_chars)
overlap_chars = 50   (default, configurable via --overlap_chars)
```

The defaults keep each chunk well within the token limit of the embedding model
[`intfloat/multilingual-e5-small`](https://huggingface.co/intfloat/multilingual-e5-small) (**512 tokens** max).
At ~5.5 chars/token for multilingual text, 500 chars ≈ 90 tokens, so every chunk is fully
represented in its FAISS vector with no truncation.

Example — a 2300-character CV produces ~5 chunks:

```
chunk 0:  chars    0 → 500
chunk 1:  chars  450 → 950    ← 50-char overlap with chunk 0
chunk 2:  chars  900 → 1400
chunk 3:  chars 1350 → 1850
chunk 4:  chars 1800 → 2300
```

The 50-char overlap ensures a sentence cut at a boundary also appears at
the start of the next chunk, so no context is lost during search.

### 3. BM25 index

All chunk texts are tokenized with a simple regex (`[A-Za-zÀ-ÿ0-9_+#.-]+`) and
fed into `BM25Okapi`. The resulting object is serialized with `pickle`:

```
rag_store/bm25.pkl
```

### 4. FAISS index

Chunks are embedded in batches using a local **SentenceTransformer** model:

```
intfloat/multilingual-e5-small
```

Model card: [Hugging Face — intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small).
Inputs must be prefixed with `query: ` (for the search query) or `passage: ` (for document chunks); the pipeline applies these automatically.

- Downloaded from HuggingFace on first run (~117 MB)
- Cached in Docker volume `hf_cache` — subsequent runs load from disk
- Produces 384-dimensional float32 vectors
- Vectors are L2-normalized → inner product equals cosine similarity
- Stored as `IndexFlatIP` (exact search, no approximation)

```
rag_store/faiss.index    ← binary matrix  (N chunks × 384 dims)
rag_store/chunks.jsonl   ← one JSON line per chunk (text + metadata)
```

`chunks.jsonl` is the bridge between FAISS row indices and actual CV text:

```jsonl
{"chunk_id": 0, "cv_id": "cv_001", "chunk_index": 0, "text": "Emily Williamson\nJunior Product Manager..."}
{"chunk_id": 1, "cv_id": "cv_001", "chunk_index": 1, "text": "...Competencias\nProduct Management..."}
{"chunk_id": 2, "cv_id": "cv_002", "chunk_index": 0, "text": "Lena Müller\nSenior UX Designer..."}
```

### 5. Manifest

A `manifest.json` is written after every successful index build:

```json
{
  "fingerprint": "7df5b7e...",
  "pdf_count": 30,
  "chunk_count": 169,
  "embedding_model": "intfloat/multilingual-e5-small",
  "dim": 384,
  "chunk_chars": 500,
  "overlap_chars": 50
}
```

The fingerprint is a SHA-256 hash of all PDF paths + modification times + sizes.
On the next `make index`, if the fingerprint matches, indexing is skipped entirely.
Use `make rebuild` or `--force` to override.

---

## Search (`search.py`)

### Modes

| Mode | Flag | What it does |
|------|------|-------------|
| `hybrid` | `--mode hybrid` (default) | Runs FAISS + BM25, then **reranks** with RRF; prints all three (FAISS, BM25, Reranked) |
| `reranked` | `--mode reranked` | Same as hybrid but prints only the RRF reranked list |
| `faiss` | `--mode faiss` | Semantic search only |
| `bm25` | `--mode bm25` | Keyword search only |

### Reranking (RRF)

When `mode` is `hybrid` or `reranked`, the two ranked lists (FAISS and BM25) are merged using **Reciprocal Rank Fusion (RRF)**:

- Each ranker returns a larger candidate set (default: `max(topk×4, 20)`).
- For each document, RRF score = `1/(k + rank_faiss) + 1/(k + rank_bm25)` (documents absent from one list contribute only the term from the list where they appear).
- Results are sorted by this score; the top `topk` form the final reranked list.

This favours chunks that appear **high in both** FAISS and BM25 (e.g. exact keyword match + good semantic fit). The constant `k` is configurable via `--rrf_k` (default 60).

### How a query is processed

**FAISS path (semantic):**

```
query string
    │
    ▼
SentenceTransformer.encode(query, normalize_embeddings=True)
    │
    ▼ float32 vector [384 dims]
    │
    ▼
faiss.index.search(qvec, topk)
    │
    ▼ [(score, chunk_id), ...]
    │
    ▼
chunks.jsonl[chunk_id]  →  cv_id + text
```

**BM25 path (keyword):**

```
query string
    │
    ▼
tokenize("who has jenkins experience")  →  ["who", "has", "jenkins", "experience"]
    │
    ▼
bm25.get_scores(tokens)  →  score per chunk
    │
    ▼
sort descending, take topk where score > 0
    │
    ▼
chunks.jsonl[chunk_id]  →  cv_id + text
```

### Example output

```
Query: "Jenkins"  |  mode=hybrid  |  topk=5

--- FAISS (semantic) ---
  [0.8407] cv_id=cv_029  chunk=4  ...Kubernetes Jenkins Ansible...
  [0.8376] cv_id=cv_029  chunk=5  ...Jenkins-based CI/CD pipeline...

--- BM25 (keyword) ---
  [3.4059] cv_id=cv_029  chunk=1  ...CI/CD pipelines using Jenkins, Ansible...

--- Reranked (RRF) ---
  [0.0328] cv_id=cv_029  chunk=1  ...CI/CD pipelines using Jenkins, Ansible...
  [0.0326] cv_id=cv_029  chunk=4  ...Kubernetes Jenkins Ansible...
  ...
```

### Configuration

- **Embedding model** (env): `EMBEDDING_MODEL=intfloat/multilingual-e5-small`  
  See [Hugging Face — intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small).
- **RRF constant** (CLI): `--rrf_k 60` — higher values reduce the impact of rank position when fusing FAISS and BM25.

---

## Output files reference

| File | Format | Purpose |
|------|--------|---------|
| `rag_store/faiss.index` | FAISS binary | Dense vector index (loaded into RAM at search time) |
| `rag_store/chunks.jsonl` | JSON Lines | Text + metadata for every chunk |
| `rag_store/bm25.pkl` | Python pickle | Serialized BM25Okapi object |
| `rag_store/manifest.json` | JSON | Build config + fingerprint for change detection |

---

## Makefile targets

```
make build           Build RAG docker image
make index           Build FAISS + BM25 indices from PDFs
make rebuild         Force reindex (ignores manifest fingerprint)
make search Q='...'  Run a hybrid search query
make ls              List rag_store contents
make clean           Remove all rag_store artefacts
```
