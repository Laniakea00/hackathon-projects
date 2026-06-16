# QazCode — Medical RAG Diagnostic API

Clinical decision support system. Takes a patient complaint in Russian, retrieves relevant clinical protocols via hybrid vector + BM25 search, and returns ranked ICD-10 diagnoses using an LLM.

## Stack

- **Backend** — FastAPI + SQLAlchemy 2.0 + pgvector (HNSW)
- **Embedding** — `intfloat/multilingual-e5-large` (1024-dim)
- **Retrieval** — pgvector cosine search + BM25 -> Reciprocal Rank Fusion
- **LLM** — OpenAI-compatible endpoint (QazCode Hub / any compatible API)
- **DB** — PostgreSQL 15 + pgvector extension
- **Frontend** — React + Nginx (port 3000)

---

## Quick Start

### Step 1. Download the data folder

The protocols corpus and test set are **not stored in the repo**. Download them from Google Drive:

**[Download data folder from Google Drive](https://drive.google.com/drive/folders/14qThUpugy6GL0Aj1YanQvDi8wuLIdqPF?usp=sharing)**

Extract the downloaded `data/` folder into the **project root** so the layout looks like:

```
QazCode/
  data/
    corpus.jsonl
    test_set/
    .embeddings/
    ...
  backend/
  llm/
  ...
```

### Step 2. Install uv

**Linux / macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Or via pip:**
```bash
pip install uv
```

### Step 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your LLM API key:

```env
LLM_BASE_URL=https://hub.qazcode.ai/v1
LLM_API_KEY=your_api_key_here
LLM_MODEL=oss-120b
```

The PostgreSQL defaults (`postgres/postgres/qazcode`) work out of the box with Docker.

### Step 4. Start the database

```bash
docker compose up db -d
```

Wait until healthy (~5 seconds):

```bash
docker compose ps
```

### Step 5. Install Python dependencies

```bash
uv sync
```

### Step 6. Start the backend

```bash
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

On first run the backend will:
1. Create the DB schema and load protocols from `data/corpus.jsonl`
2. Compute and cache embeddings into `data/.embeddings/` (takes a few minutes the first time)
3. Build the HNSW vector index

Wait until you see **`QazCode RAG server is ready.`** in the logs before proceeding.

### Step 7. Run evaluation

Open a second terminal:

```bash
uv run python evaluate.py
```

Results are saved to `data/evals/`.

---

## Full Docker Stack (all services)

Runs DB + backend + frontend together:

```bash
docker compose up --build
```

| Service  | URL                   |
|----------|-----------------------|
| Frontend | http://localhost:3000 |
| Backend  | http://localhost:8000 |
| DB       | localhost:5432        |

> **Note:** First build downloads ~4 GB of Python packages (torch + CUDA libs). Subsequent builds use the Docker layer cache.

---

## API Reference

### `POST /diagnose`

```json
{
  "symptoms": "opisanie zhalob patsiyenta"
}
```

**Response:**

```json
{
  "diagnoses": [
    {
      "rank": 1,
      "diagnosis": "Ostryy kholyetsistit",
      "icd10_code": "K81.0",
      "explanation": "..."
    }
  ]
}
```

### `GET /health`

Returns `{"status": "ok"}` when the server is ready.

---

## Environment Variables

| Variable            | Default                                                 | Description                    |
|---------------------|---------------------------------------------------------|--------------------------------|
| `DATABASE_URL`      | `postgresql://postgres:postgres@localhost:5432/qazcode` | Sync DB URL                    |
| `LLM_BASE_URL`      | `https://hub.qazcode.ai/v1`                            | OpenAI-compatible LLM endpoint |
| `LLM_API_KEY`       | *(required)*                                            | API key for the LLM            |
| `LLM_MODEL`         | `oss-120b`                                              | Model name to use              |
| `EMBEDDING_MODEL`   | `intfloat/multilingual-e5-large`                        | HuggingFace embedding model    |
| `JWT_SECRET`        | `change-me-in-production`                               | Secret for JWT auth            |
