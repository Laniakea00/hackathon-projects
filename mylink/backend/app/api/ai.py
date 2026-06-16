from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Any, Dict, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.ai.mismatch_detector import run_mismatch_detector
from app.services.ai import registry
from app.db.session import get_db
from app.models.vacancy import Vacancy
from app.models.candidate import Candidate
from app.models.response import CandidateResponse
from app.models.candidate import Candidate as CandidateModel
from app.services.ai.llm_client import get_llm

router = APIRouter(prefix="/ai", tags=["AI"])


class Hints(BaseModel):
    must_have_skills: Optional[list[str]] = None
    lang_requirement: Optional[str] = None
    location_requirement: Optional[str] = None
    salary_range: Optional[Dict[str, Any]] = None


class MismatchInput(BaseModel):
    job_text: str
    cv_text: str
    hints: Optional[Hints] = None


@router.post("/mismatch")
async def mismatch_detector(input_data: MismatchInput) -> Dict[str, Any]:
    try:
        payload = input_data.model_dump()
        return run_mismatch_detector(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"AI error: {e}")


class AgentInvokeInput(BaseModel):
    payload: Dict[str, Any]


@router.get("/agents")
async def list_agents() -> Dict[str, Any]:
    return {"agents": registry.list_ids()}


@router.post("/agents/{agent_id}/invoke")
async def invoke_agent(agent_id: str, body: AgentInvokeInput) -> Dict[str, Any]:
    try:
        agent = registry.get(agent_id)
        return agent.run(body.payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"AI agent error: {e}")


class PipelineScreenInput(BaseModel):
    job_text: str
    cv_text: str
    hints: Optional[Hints] = None
    limits: Optional[Dict[str, Any]] = None


@router.post("/pipeline/screen")
async def pipeline_screen(body: PipelineScreenInput) -> Dict[str, Any]:
    """Run end-to-end screening: mismatch -> clarifier -> orchestrator -> scorer."""
    try:
        # 1) Mismatch
        mismatch_payload = {
            "job_text": body.job_text,
            "cv_text": body.cv_text,
            "hints": body.hints.model_dump() if body.hints else None,
        }
        mismatch = run_mismatch_detector(mismatch_payload)

        # 2) Clarifier
        clarifier_payload = {
            "job_struct": mismatch.get("job_struct") or {},
            "cv_struct": mismatch.get("cv_struct") or {},
            "mismatches": mismatch.get("mismatches") or [],
            "missing_data": mismatch.get("missing_data") or [],
            "limits": {"max_questions": (body.limits or {}).get("max_questions", 3)},
        }
        clarifier = registry.get("clarifier").run(clarifier_payload)

        # 3) Orchestrator (no interactive responses here; just greeting+closing)
        orchestrator_payload = {
            **clarifier,
            "context": {
                "job_title": mismatch.get("job_struct", {}).get("title") or "",
                "company": "",
                "currency": (mismatch.get("job_struct", {}).get("salary_range") or {}).get("currency") or "",
            },
            "responses": [],
        }
        orchestrator = registry.get("orchestrator").run(orchestrator_payload)

        # 4) Scorer
        ids = {"job_id": "", "candidate_id": "", "application_id": ""}
        weights_mode = "auto"
        must_have_skills = (body.hints.must_have_skills if body.hints and body.hints.must_have_skills else [])
        scorer_payload = {
            "ids": ids,
            "job_struct": mismatch.get("job_struct") or {},
            "cv_struct": mismatch.get("cv_struct") or {},
            "mismatches": mismatch.get("mismatches") or [],
            "missing_data": mismatch.get("missing_data") or [],
            "widget_payload": orchestrator,
            "weights_mode": weights_mode,
            "weights": {},
            "must_have_skills": must_have_skills,
            "verdict_thresholds": {"fit": 75, "borderline": 60},
        }
        scorer = registry.get("relevance_scorer").run(scorer_payload)

        return {
            "mismatch": mismatch,
            "clarifier": clarifier,
            "orchestrator": orchestrator,
            "scorer": scorer,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"AI pipeline error: {e}")


class PipelineByIdsInput(BaseModel):
    vacancy_id: UUID
    candidate_id: UUID
    response_id: Optional[UUID] = None
    limits: Optional[Dict[str, Any]] = None


@router.post("/pipeline/screen_by_ids")
async def pipeline_screen_by_ids(body: PipelineByIdsInput, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Run screening pipeline using vacancy/candidate data from DB. Optionally persist score into CandidateResponse."""
    # Load DB entities
    v_res = await db.execute(select(Vacancy).where(Vacancy.id == body.vacancy_id))
    vacancy = v_res.scalar_one_or_none()
    c_res = await db.execute(select(Candidate).where(Candidate.id == body.candidate_id))
    candidate = c_res.scalar_one_or_none()
    if not vacancy or not candidate:
        raise HTTPException(status_code=404, detail="Vacancy or Candidate not found")

    # Assemble texts and hints
    job_text = f"{vacancy.title or ''}. {vacancy.description or ''}"
    cv_text = f"{candidate.full_name or ''}. {candidate.resume_text or ''}. City: {candidate.city or ''}"
    req = (getattr(vacancy, "requirements", None) or {})
    must_have_skills = [str(s).strip().lower() for s in (req.get("stack") or []) if str(s).strip()]
    hints = {
        "must_have_skills": must_have_skills or None,
        "lang_requirement": None,
        "location_requirement": vacancy.location or None,
        "salary_range": {"min": vacancy.salary_min or 0, "max": vacancy.salary_max or 0, "currency": "KZT"} if (vacancy.salary_min or vacancy.salary_max) else None,
    }

    # Delegate to in-process pipeline
    pipeline = await pipeline_screen(PipelineScreenInput(job_text=job_text, cv_text=cv_text, hints=Hints(**{k: v for k, v in hints.items() if v is not None}) if any(hints.values()) else None, limits=body.limits))

    # Optionally persist score to response
    if body.response_id:
        r_res = await db.execute(select(CandidateResponse).where(CandidateResponse.id == body.response_id))
        resp = r_res.scalar_one_or_none()
        if resp:
            try:
                overall = int(pipeline.get("scorer", {}).get("overall_match_pct") or 0)
                resp.relevance_score = float(overall) / 100.0
                resp.rejection_reasons = {
                    "verdict": pipeline.get("scorer", {}).get("verdict"),
                    "scores_pct": pipeline.get("scorer", {}).get("scores_pct"),
                    "summary": pipeline.get("scorer", {}).get("summary"),
                }
                await db.flush()
            except Exception:
                # Do not fail the response if persistence fails
                pass

    return pipeline


class EmployerAssistantBody(BaseModel):
    vacancy_id: UUID
    question: str


@router.post("/employer/assistant")
async def employer_assistant(body: EmployerAssistantBody, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Answer employer questions about candidates for a vacancy using LLM and real scores."""
    # Load responses with candidate names
    q = (
        select(CandidateResponse, CandidateModel)
        .join(CandidateModel, CandidateResponse.candidate_id == CandidateModel.id)
        .where(CandidateResponse.vacancy_id == body.vacancy_id)
    )
    rows = (await db.execute(q)).all()
    if not rows:
        return {"answer": "Пока нет откликов по этой вакансии."}

    def fmt(row):
        resp, cand = row
        score = resp.relevance_score or 0.0
        summary = (resp.rejection_reasons or {}).get("summary", {})
        positives = "; ".join(summary.get("positives") or [])
        risks = "; ".join(summary.get("risks") or [])
        return f"- {cand.full_name}: score={int(round(score*100))}% | + {positives or '—'} | риски: {risks or '—'}"

    context_list = "\n".join(fmt(r) for r in rows)

    sys = (
        "Ты помощник HR. Отвечай кратко и по делу, опираясь только на предоставленные данные."
        " Если просят сравнить/рекомендовать, поясни на 1–2 предложения почему."
    )
    prompt = (
        f"Вакансия имеет отклики (score и сводка):\n{context_list}\n\n"
        f"Вопрос работодателя: {body.question}\n"
        "Дай полезный ответ на русском, учитывая score и риски/сильные стороны."
    )

    try:
        llm = get_llm()
        res = await llm.ainvoke([{"role": "system", "content": sys}, {"role": "user", "content": prompt}])
        text = res.content if hasattr(res, "content") else str(res)
        return {"answer": text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"LLM error: {e}")
