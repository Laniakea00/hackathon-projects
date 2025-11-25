# SmartBot HR Assistant

AI-powered assistant for HR teams that helps **analyze CVs**, **match candidates to vacancies**, and **speed up screening** using LLMs.

Built during a hackathon as an end-to-end prototype with:
- Backend: FastAPI + SQLAlchemy
- Frontend: React
- AI layer: LangChain + LLM provider (e.g. OpenAI)
- Containerization: Docker / docker-compose

---

## 🚀 Features

- 📄 **CV analysis**
  - Upload CVs (PDF / DOCX / text)
  - Extract key skills, experience, education
  - Summarize candidate profile in a structured way

- 🎯 **Vacancy–candidate matching**
  - Input a job description
  - Get a relevance score for each candidate
  - See short justification: _why this candidate fits / doesn't fit_

- 💬 **HR Chatbot**
  - Chat interface to ask questions like:
    - “Show me the top-5 candidates for Junior Python Developer”
    - “Who has experience with Docker and FastAPI?”
  - Bot uses vector search + LLM to answer based on stored CV data

- 📊 **Dashboard for HR**
  - List of candidates and their match scores
  - Filtering by skills / experience / seniority

*(If что-то из этого у тебя не реализовано дословно — можно убрать или переформулировать.)*

---

## 🏗️ Architecture

High-level architecture:

- **Frontend (React)**
  - UI for HR: upload CVs, manage vacancies, see rankings, chat with bot
  - Communicates with backend via REST API

- **Backend (FastAPI)**
  - Endpoints for:
    - CV upload & parsing
    - Vacancy creation
    - Running match / analysis
    - Chatbot interaction
  - Stores structured candidate data in a relational database

- **AI Layer (LangChain + LLM)**
  - Prompts for:
    - Extracting structured info from CV text
    - Scoring candidate vs vacancy
    - Generating natural-language explanations
  - (Optional) Vector store for semantic search over candidates

- **Database**
  - SQLAlchemy models: `Candidate`, `Vacancy`, `Skill`, `MatchResult`, etc.
  - Any SQL DB (e.g. PostgreSQL / SQLite during development)

- **Infra**
  - Docker images for backend & frontend
  - `docker-compose.yml` to run everything locally

---

## 🧰 Tech Stack 

**Backend (Web Service)**:
- Root: backend/
- Build: pip install -r requirements.txt
- Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
- Env:
  - DATABASE_URL, DATABASE_URL_SYNC
  - REDIS_URL
  - SECRET_KEY
  - ALLOWED_ORIGINS (e.g. https://your-frontend.onrender.com)
  - OPENAI_API_KEY, OPENAI_MODEL

**Frontend (Static Site)**:
- Root: frontend/
- Build: npm ci && npm run build
- Publish dir: dist
- Env:
  - VITE_API_BASE=https://your-backend.onrender.com

**AI / NLP**
- LangChain
- LLM provider (e.g. OpenAI API)

**Infra**
- Docker, docker-compose
- GitHub for version control

## ⚙️ Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/Laniakea00/mylink.git
```

### 2. Setup environment variables

### 3. Run with Docker (recommended)

```bash
docker-compose up --build
```

Then: 
- Backend available at: http://localhost:8000
- Frontend available at: http://localhost:8011

4. Run locally without Docker

Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Frontend
```bash
cd frontend
npm install
npm ci && npm run build # or npm start
```

## 🔍 How SmartBot Works (Data Flow)

### 1. HR uploads CV
→ Backend receives file → parses text → extracts key info via LLM prompt → saves structured data in DB.

### 2. HR creates vacancy
→ Job description stored in DB → optional extraction of required skills/seniority.

### 3. Matching process
- For each candidate:
    - Build a prompt: “Given this CV and this job description, evaluate the fit on a 0–100 scale...”
    - LLM returns:
        - numeric score
        - short pros/cons
          
- Results stored as MatchResult.

### 4. HR uses dashboard & chatbot
- Frontend fetches ranked candidates from backend.
- Chatbot endpoint uses:
    - DB + (optional) vector search
    - LLM to answer queries about candidates.
