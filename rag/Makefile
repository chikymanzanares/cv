# rag/Makefile

# Paths relativas al working_dir del contenedor (/cv)
PDF_DIR ?= cv_generation/data/cvs
OUT_DIR ?= rag_store

# Docker compose
COMPOSE ?= docker compose
RAG_SERVICE ?= rag_index

.PHONY: help build index search ls clean rebuild

help:
	@echo ""
	@echo "Targets:"
	@echo "  make build            Build RAG docker image (MiniLM + FAISS + BM25)"
	@echo "  make index            Build FAISS + BM25 indices from PDFs"
	@echo "  make search Q='...'   Search indices with query"
	@echo "  make ls               List rag_store contents"
	@echo "  make clean            Remove rag_store artifacts"
	@echo "  make rebuild          Force reindex"
	@echo ""

# 🔧 Rebuild container after changing requirements-rag.txt
build:
	$(COMPOSE) build $(RAG_SERVICE)

# 🧠 Build indices (persistent on disk)
index:
	$(COMPOSE) run --rm $(RAG_SERVICE) \
	sh -lc "python -m rag.rag_cli.build_index --pdf_dir $(PDF_DIR) --out_dir $(OUT_DIR)"

# 🔁 Force rebuild even if manifest matches
rebuild:
	$(COMPOSE) run --rm $(RAG_SERVICE) \
	sh -lc "python -m rag.rag_cli.build_index --pdf_dir $(PDF_DIR) --out_dir $(OUT_DIR) --force"

# 🔍 CLI search (FAISS + BM25)
search:
	@if [ -z "$(Q)" ]; then echo "Missing Q. Usage: make search Q='Who knows Python?'"; exit 1; fi
	$(COMPOSE) run --rm $(RAG_SERVICE) \
	sh -lc "python -m rag.rag_cli.search --index_dir $(OUT_DIR) --query \"$(Q)\""

# 📁 List persisted indices
ls:
	@echo "Listing $(OUT_DIR):"
	@ls -lah $(OUT_DIR) || true

# 🧹 Remove persisted artifacts
clean:
	@echo "Removing rag artifacts in $(OUT_DIR)..."
	@rm -f $(OUT_DIR)/faiss.index $(OUT_DIR)/chunks.jsonl $(OUT_DIR)/bm25.pkl $(OUT_DIR)/manifest.json