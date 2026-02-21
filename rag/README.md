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

The defaults are aligned with the model's hard limit of **128 tokens**
(~500–600 characters for multilingual text). This ensures every chunk is
fully represented in its FAISS vector — nothing is silently truncated.

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
paraphrase-multilingual-MiniLM-L12-v2
```

- Downloaded from HuggingFace on first run (~471 MB)
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
  "chunk_count": 59,
  "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
  "dim": 384,
  "chunk_chars": 1800,
  "overlap_chars": 250
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
| `hybrid` | `--mode hybrid` (default) | Runs both FAISS and BM25, prints both result sets |
| `faiss` | `--mode faiss` | Semantic search only |
| `bm25` | `--mode bm25` | Keyword search only |

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
  [0.7821] cv_id=cv_008  chunk=0
  Marcos Delgado  DevOps Engineer  ...CI/CD pipelines with Jenkins and GitLab...

  [0.7103] cv_id=cv_015  chunk=0
  Ana Costa  Platform Engineer  ...automated deployments using Jenkins, Ansible...

--- BM25 (keyword) ---
  [4.2100] cv_id=cv_008  chunk=0
  Marcos Delgado  DevOps Engineer  ...CI/CD pipelines with Jenkins and GitLab...
```

### Configuration

The embedding model is read from the environment:

```
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2  # default
```

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
