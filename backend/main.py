"""QazCode – Medical RAG diagnostic API.

POST /diagnose
    Accepts patient symptoms, retrieves the most relevant clinical protocol
    chunks via pgvector hybrid search, then asks an LLM to reason over
    them and return structured diagnoses.

    Request  body : {"symptoms": "..."}
    Response body : {"diagnoses": [{rank, diagnosis, icd10_code, explanation}]}

API contract is intentionally identical to src/main.py (mock server) so
existing evaluation tooling works without changes.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.api.deps import require_role
from backend.api.v1.auth import router as auth_router
from backend.database.session import init_db
from backend.models.user import UserRole
from backend.schemas.diagnose import DiagnoseRequest, DiagnoseResponse
from llm.generator import QazCodeHubConnector
from llm.retriever import MedicalRetriever
from llm.service import RAGService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan: startup / shutdown ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("Initialising database …")
    await asyncio.to_thread(init_db)

    logger.info("Loading embedding model …")
    retriever = MedicalRetriever()
    await retriever.initialize()

    connector = QazCodeHubConnector()

    service = RAGService(retriever, connector)
    app.state.service = service

    logger.info("QazCode RAG server is ready.")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down …")
    await connector.close()


# ── FastAPI application ───────────────────────────────────────────────────────

app = FastAPI(
    title="QazCode Medical RAG",
    description="Diagnostic API backed by clinical protocol knowledge base.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


# ── Dependency ────────────────────────────────────────────────────────────────

def _get_service(request: Request) -> RAGService:
    return request.app.state.service  # type: ignore[return-value]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/diagnose", response_model=DiagnoseResponse)
async def handle_diagnose(
    body: DiagnoseRequest,
    request: Request,
    _: object = Depends(require_role(UserRole.PATIENT, UserRole.ADMIN)),
) -> DiagnoseResponse:
    """Full RAG pipeline: hybrid retrieval → LLM reasoning → structured response."""
    symptoms = (body.symptoms or "").strip()
    if not symptoms:
        raise HTTPException(status_code=422, detail="'symptoms' must not be empty.")

    service = _get_service(request)
    diagnoses = await service.diagnose(symptoms)
    return DiagnoseResponse(diagnoses=diagnoses)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
