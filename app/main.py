from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

from app.infrastructure.web.routers.threads import router as threads_router
from app.infrastructure.web.routers.runs import router as runs_router
from app.infrastructure.web.routers.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Load the RAG index and embedding model once at startup.
    Both are stored in app.state so background tasks can reuse them
    without reloading on every request.
    """
    from sentence_transformers import SentenceTransformer
    from rag.retrieval import load_index
    from app.infrastructure.rag.rag_chat_service import RagChatService
    from app.infrastructure.llm.anthropic_chat import AnthropicChatService
    from app.infrastructure.llm.gemini_chat import GeminiChatService

    index_dir = Path(os.getenv("RAG_STORE_DIR", "rag_store"))
    embedding_model_name = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")

    print(f"[startup] Loading embedding model: {embedding_model_name}")
    model = SentenceTransformer(embedding_model_name)

    print(f"[startup] Loading RAG index from: {index_dir}")
    index_data = load_index(index_dir)

    app.state.rag_service = RagChatService(index_data=index_data, model=model)

    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    if provider == "anthropic":
        app.state.llm_service = AnthropicChatService(
            api_key=os.environ["ANTHROPIC_API_KEY"],
            model=os.getenv("ANTHROPIC_TEXT_MODEL", "claude-3-haiku-20240307"),
        )
    elif provider == "google":
        app.state.llm_service = GeminiChatService(
            api_key=os.environ["GEMINI_API_KEY"],
            model=os.getenv("GEMINI_TEXT_MODEL", "models/gemini-2.0-flash"),
        )
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider!r}. Use 'anthropic' or 'google'.")

    app.state.history_turns = int(os.getenv("CHAT_HISTORY_TURNS", "6"))

    print(f"[startup] LLM provider: {provider} | history turns: {app.state.history_turns}")
    print("[startup] Ready.")

    yield

    print("[shutdown] Releasing RAG resources.")


app = FastAPI(lifespan=lifespan)

app.include_router(threads_router, prefix="/api")
app.include_router(runs_router, prefix="/api")
app.include_router(users_router, prefix="/api")

# Serve generated CV files (HTML + PDF) so the frontend can link to them.
# Accessible at /cvs/{cv_id}/cv.pdf and /cvs/{cv_id}/cv.html
app.mount("/cvs", StaticFiles(directory="cv_generation/data/cvs"), name="cvs")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/")
def hello():
    return {"message": "hello world"}
