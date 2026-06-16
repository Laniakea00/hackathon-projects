"""QazCode – Medical RAG diagnostic API."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1.auth import router as auth_router
from backend.api.v1.chat import router as chat_router
from backend.database.session import init_db, init_vector_db
from backend.schemas.diagnose import DiagnoseRequest, DiagnoseResponse
from llm.generator import QazCodeHubConnector
from llm.retriever import MedicalRetriever
from llm.service import RAGService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising database …")
    await asyncio.to_thread(init_db)

    logger.info("Loading embeddings from cache …")
    await asyncio.to_thread(init_vector_db)

    logger.info("Loading embedding model …")
    retriever = MedicalRetriever()
    await retriever.initialize()

    connector = QazCodeHubConnector()
    app.state.service = RAGService(retriever, connector)

    logger.info("QazCode RAG server is ready.")
    yield

    logger.info("Shutting down …")
    await connector.close()


app = FastAPI(
    title="QazCode Medical RAG",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routers ───────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


# ── Evaluation endpoint (no auth — used by evaluate.py) ──────────────────────

@app.post("/diagnose", response_model=DiagnoseResponse)
async def handle_diagnose(body: DiagnoseRequest, request: Request) -> DiagnoseResponse:
    symptoms = (body.symptoms or "").strip()
    if not symptoms:
        raise HTTPException(status_code=422, detail="'symptoms' must not be empty.")
    diagnoses = await request.app.state.service.diagnose(symptoms)
    return DiagnoseResponse(diagnoses=diagnoses)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
