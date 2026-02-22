import json
import hashlib
import os
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.rag import BM25Index

BASE_URL = "https://api.openai.com/v1"
MODEL = "gpt-4.1-mini"
RETRIEVAL_MODEL = "gpt-4.1-mini"
API_KEY = os.getenv("OPENAI_API_KEY")

CORPUS_JSONL = "./data/protocols_corpus.jsonl"
INDEX = None

FALLBACK = {
    "diagnoses": [
        {"rank": 1, "diagnosis": "Недостаточно данных", "icd10_code": "R69",
         "explanation": "Недостаточно информации для точного диагноза."},
        {"rank": 2, "diagnosis": "Другие общие симптомы и признаки", "icd10_code": "R68.8",
         "explanation": "Требуется уточнение симптомов и обследование."},
        {"rank": 3, "diagnosis": "Общий медицинский осмотр", "icd10_code": "Z00.0",
         "explanation": "Рекомендуется очная оценка врачом."},
    ]
}

SYSTEM = """You are a clinical decision support system for Kazakhstan clinical protocols.

Return JSON ONLY, exactly in this schema:
{
  "diagnoses": [
    {"rank": 1, "diagnosis": "...", "icd10_code": "...", "explanation": "..."},
    {"rank": 2, "diagnosis": "...", "icd10_code": "...", "explanation": "..."},
    {"rank": 3, "diagnosis": "...", "icd10_code": "...", "explanation": "..."}
  ]
}

Rules:
- Output ONLY JSON, no markdown, no extra text.
- Use ICD-10 code format like G91.1, J20.9, A01.
- Keep explanation 1-2 sentences.
- Prefer ICD-10 codes that appear in the retrieved protocol excerpts or their ICD candidates list.
- If you output a code not present in context, keep it only if strongly implied by symptoms.
"""

# Шаг 1: "перевод" длинного текста в короткий поисковый запрос
RETRIEVAL_SYSTEM = """You convert a patient free-text complaint into a compact retrieval query
for searching clinical protocols.

Return JSON ONLY:
{
  "key_findings": ["..."],
  "context": ["..."],
  "retrieval_query": "..."
}

Rules:
- Do NOT give a diagnosis.
- key_findings: 5-12 short medical findings (symptoms, timing, localization).
- context: 0-5 important background facts (pregnancy, oncology, chemo, trauma, etc).
- retrieval_query: ONE LINE in Russian, compact, only medically useful terms.
- Avoid emotions/irrelevant narrative.
"""

# простой in-memory кэш, чтобы не платить за rewrite повторно
_RETRIEVAL_CACHE: dict[str, str] = {}


class DiagnoseRequest(BaseModel):
    symptoms: Optional[str] = ""


class Diagnosis(BaseModel):
    rank: int = Field(ge=1)
    diagnosis: str
    icd10_code: str
    explanation: str


class DiagnoseResponse(BaseModel):
    diagnoses: list[Diagnosis]


def normalize_icd(code: str) -> str:
    # легкая нормализация для стабильности метрики
    if not code:
        return ""
    return code.strip().upper().replace(" ", "")


def _hash_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global INDEX
    print("\n🏥 Diagnostic Server (FastAPI + OpenAI)")
    print("=" * 50)
    print("Endpoint: /diagnose")
    print("Method:   POST")
    print('Body:     {"symptoms": "..."}')
    print("Docs:     /docs")
    print("=" * 50)

    print(f"📚 Building BM25 index from: {CORPUS_JSONL}")
    INDEX = BM25Index.build_from_jsonl(CORPUS_JSONL)
    print(f"✅ Index ready. Chunks: {len(INDEX.chunks)}")

    if not API_KEY:
        print("⚠️  OPENAI_API_KEY is not set. Requests will fail.")
    yield


app = FastAPI(title="Diagnosis Server", lifespan=lifespan)


async def build_retrieval_query(symptoms: str) -> str:
    """LLM -> делает короткий retrieval_query. С кэшем."""
    if not API_KEY:
        return ""

    key = _hash_text(symptoms)
    if key in _RETRIEVAL_CACHE:
        return _RETRIEVAL_CACHE[key]

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": RETRIEVAL_MODEL,
        "messages": [
            {"role": "system", "content": RETRIEVAL_SYSTEM},
            {"role": "user", "content": symptoms},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            obj = json.loads(content)
            rq = (obj.get("retrieval_query") or "").strip()
    except Exception:
        rq = ""

    _RETRIEVAL_CACHE[key] = rq
    return rq


async def build_context(symptoms: str) -> str:
    """BM25 retrieval по LLM-rewritten query (или по исходному, если rewrite пустой)."""
    if not INDEX:
        return ""

    rq = await build_retrieval_query(symptoms)
    query_for_search = rq if rq else symptoms

    hits = INDEX.search_diverse(symptoms, top_k=6, per_protocol=1)
    if not hits:
        return ""

    blocks = []
    for i, (score, ch) in enumerate(hits, start=1):
        blocks.append(
            f"[{i}] score={score:.3f} protocol_id={ch.protocol_id} | source={ch.source_file} | title={ch.title}\n"
            f"ICD candidates: {', '.join(ch.icd_codes[:30])}\n"
            f"TEXT:\n{ch.text}\n"
        )
    return "\n---\n".join(blocks)


async def call_llm(symptoms: str) -> dict:
    if not API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    context = await build_context(symptoms)

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": (
                    f"SYMPTOMS:\n{symptoms}\n\n"
                    f"RETRIEVED PROTOCOL EXCERPTS:\n{context}"
                ),
            },
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]

    return json.loads(content)


def normalize_response(obj: dict) -> DiagnoseResponse:
    diagnoses = obj.get("diagnoses", [])
    if not isinstance(diagnoses, list) or not diagnoses:
        diagnoses = FALLBACK["diagnoses"]

    diagnoses = sorted(diagnoses, key=lambda d: d.get("rank", 999))[:3]

    norm = []
    for i, d in enumerate(diagnoses, start=1):
        norm.append(
            Diagnosis(
                rank=i,
                diagnosis=str(d.get("diagnosis", ""))[:200],
                icd10_code=normalize_icd(str(d.get("icd10_code", ""))),
                explanation=str(d.get("explanation", ""))[:400],
            )
        )

    return DiagnoseResponse(diagnoses=norm)


@app.post("/diagnose", response_model=DiagnoseResponse)
async def handle_diagnose(request: DiagnoseRequest) -> DiagnoseResponse:
    symptoms = request.symptoms or ""
    if not isinstance(symptoms, str):
        symptoms = str(symptoms)
    symptoms = symptoms.strip()

    if not symptoms:
        return normalize_response(FALLBACK)

    try:
        raw = await call_llm(symptoms)
        return normalize_response(raw)
    except Exception:
        return normalize_response(FALLBACK)