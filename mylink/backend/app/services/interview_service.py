"""
InterviewService - Orchestrates AI-powered candidate interview flow

This service integrates AI agents to:
1. Detect mismatches between vacancy and candidate resume
2. Generate clarifying questions dynamically
3. Process candidate answers and update findings
4. Recalculate relevance score after each answer
"""

from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import hashlib

from app.models.response import CandidateResponse, ResponseStatus
from app.models.vacancy import Vacancy
from app.models.candidate import Candidate
from app.services.ai.agents.mismatch_agent import MismatchDetectorAgent
from app.services.ai.agents.question_generator_agent import QuestionGeneratorAgent
from app.services.ai.agents.relevance_scorer_agent import RelevanceScorerAgent
from app.services.ai.agents.summary_generator_agent import SummaryGeneratorAgent
from app.db.redis import get_redis


class InterviewService:
    """Service for AI-powered candidate interview orchestration"""
    
    CACHE_TTL = 3600  # 1 hour cache TTL
    
    def __init__(self):
        self.mismatch_agent = MismatchDetectorAgent()
        self.question_agent = QuestionGeneratorAgent()
        self.scorer_agent = RelevanceScorerAgent()
        self.summary_agent = SummaryGeneratorAgent()
    
    def _generate_cache_key(self, vacancy: Vacancy, candidate: Candidate, dialog_answers_count: int = 0) -> str:
        """
        Generate cache key based on vacancy, candidate, and dialog state
        Cache is invalidated when dialog_answers_count changes
        """
        # Create hash from vacancy and candidate data
        data_str = f"{vacancy.id}:{vacancy.title}:{vacancy.description}:{vacancy.requirements}"
        data_str += f":{candidate.id}:{candidate.full_name}:{candidate.resume_text}"
        data_str += f":{dialog_answers_count}"  # Invalidate on new answers
        
        hash_obj = hashlib.md5(data_str.encode())
        return f"interview:analysis:{hash_obj.hexdigest()}"
    
    async def _get_cached_analysis(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis from Redis"""
        try:
            redis = await get_redis()
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            print(f"Redis cache get error: {e}")
        return None
    
    async def _set_cached_analysis(self, cache_key: str, data: Dict[str, Any]):
        """Set cached analysis in Redis"""
        try:
            redis = await get_redis()
            await redis.setex(
                cache_key,
                self.CACHE_TTL,
                json.dumps(data, default=str)
            )
        except Exception as e:
            print(f"Redis cache set error: {e}")
    
    async def _invalidate_cache(self, response_id: UUID, db: AsyncSession):
        """Invalidate all cache keys for a response"""
        try:
            redis = await get_redis()
            # Get response to build cache key pattern
            result = await db.execute(
                select(CandidateResponse).where(CandidateResponse.id == response_id)
            )
            response = result.scalar_one_or_none()
            if response:
                # Delete all cache keys matching this response
                pattern = f"interview:analysis:*"
                async for key in redis.scan_iter(match=pattern):
                    await redis.delete(key)
        except Exception as e:
            print(f"Redis cache invalidation error: {e}")
    
    async def start_interview(
        self, 
        response_id: UUID, 
        db: AsyncSession,
        language: str = "ru"
    ) -> Dict[str, Any]:
        """
        Start interview by analyzing vacancy vs candidate and generating questions
        
        Args:
            response_id: CandidateResponse ID
            db: Database session
            language: Interview language (ru/kk/en)
            
        Returns:
            Dict with questions, metadata, and initial analysis
        """
        # Fetch response with related data
        result = await db.execute(
            select(CandidateResponse)
            .where(CandidateResponse.id == response_id)
        )
        response = result.scalar_one_or_none()
        
        if not response:
            raise ValueError(f"CandidateResponse {response_id} not found")
        
        # Fetch vacancy
        vacancy_result = await db.execute(
            select(Vacancy).where(Vacancy.id == response.vacancy_id)
        )
        vacancy = vacancy_result.scalar_one_or_none()
        
        if not vacancy:
            raise ValueError(f"Vacancy {response.vacancy_id} not found")
        
        # Fetch candidate
        candidate_result = await db.execute(
            select(Candidate).where(Candidate.id == response.candidate_id)
        )
        candidate = candidate_result.scalar_one_or_none()
        
        if not candidate:
            raise ValueError(f"Candidate {response.candidate_id} not found")
        
        # Check if we have cached analysis (if no answers yet)
        dialog_answers_count = len(response.dialog_findings.get("answers", [])) if response.dialog_findings else 0
        cache_key = self._generate_cache_key(vacancy, candidate, dialog_answers_count)
        
        # Check if we already have analysis in DB
        if response.mismatch_analysis and dialog_answers_count == 0:
            # We have analysis in DB and no new answers - try cache
            cached_data = await self._get_cached_analysis(cache_key)
            if cached_data:
                # Cache hit! Use existing analysis
                print(f"✅ Cache HIT for response {response_id}")
                mismatch_analysis = response.mismatch_analysis
                questions_result = cached_data.get("questions_result", {})
            else:
                # DB has data but cache expired - use DB data and re-cache
                print(f"🔄 Using DB data for response {response_id}, re-caching")
                mismatch_analysis = response.mismatch_analysis
                # Need to regenerate questions from existing analysis
                question_payload = self._build_question_payload(
                    mismatch_analysis, 
                    vacancy, 
                    candidate,
                    language
                )
                questions_result = self.question_agent.run(question_payload)
                # Re-cache
                await self._set_cached_analysis(cache_key, {
                    "mismatch_analysis": mismatch_analysis,
                    "questions_result": questions_result
                })
        else:
            # No analysis in DB or answers changed - run AI analysis
            print(f"❌ Cache MISS for response {response_id} - Running AI analysis")
            
            # Step 1: Run mismatch detection
            mismatch_payload = self._build_mismatch_payload(vacancy, candidate)
            mismatch_analysis = self.mismatch_agent.run(mismatch_payload)
            
            # Step 2: Generate questions based on mismatches
            question_payload = self._build_question_payload(
                mismatch_analysis, 
                vacancy, 
                candidate,
                language
            )
            questions_result = self.question_agent.run(question_payload)
            
            # Step 3: Store analysis in database
            response.mismatch_analysis = mismatch_analysis
            if not response.dialog_findings:
                response.dialog_findings = {
                    "answers": [],
                    "relocation_ready": False,
                    "salary_flex": "",
                    "lang_proofs": [],
                    "other_clarifications": []
                }
            response.language_preference = language
            response.status = ResponseStatus.IN_CHAT
            
            await db.flush()
            await db.commit()
            
            # Cache the results
            await self._set_cached_analysis(cache_key, {
                "mismatch_analysis": mismatch_analysis,
                "questions_result": questions_result
            })
        
        return {
            "response_id": str(response_id),
            "questions": questions_result.get("questions", []),
            "closing_message": questions_result.get("closing_message", ""),
            "meta": questions_result.get("meta", {}),
            "total_questions": len(questions_result.get("questions", [])),
            "mismatch_summary": {
                "total_mismatches": len(mismatch_analysis.get("mismatches", [])),
                "missing_data": mismatch_analysis.get("missing_data", []),
                "coverage": mismatch_analysis.get("coverage_snapshot", {})
            }
        }
    
    async def process_answer(
        self,
        response_id: UUID,
        question_id: str,
        answer_text: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Process candidate's answer and update findings
        
        Args:
            response_id: CandidateResponse ID
            question_id: Question identifier (e.g., "q1")
            answer_text: Candidate's answer
            db: Database session
            
        Returns:
            Dict with updated findings and next action
        """
        # Fetch response
        result = await db.execute(
            select(CandidateResponse)
            .where(CandidateResponse.id == response_id)
        )
        response = result.scalar_one_or_none()
        
        if not response:
            raise ValueError(f"CandidateResponse {response_id} not found")
        
        # Get current findings
        findings = response.dialog_findings or {
            "answers": [],
            "relocation_ready": False,
            "salary_flex": "",
            "lang_proofs": [],
            "other_clarifications": []
        }
        
        # Store answer
        findings["answers"].append({
            "question_id": question_id,
            "answer": answer_text,
            "timestamp": None  # Will be set by DB
        })
        
        # Extract structured information from answer
        # This is a simplified version - you can enhance with NLP
        answer_lower = answer_text.lower().strip()
        
        # Check for relocation readiness
        if any(keyword in answer_lower for keyword in ["да", "готов", "yes", "иә"]):
            if "переезд" in answer_lower or "relocation" in answer_lower:
                findings["relocation_ready"] = True
        
        # Check for salary flexibility
        if any(keyword in answer_lower for keyword in ["обсуждаем", "negotiable", "гибко"]):
            findings["salary_flex"] = "negotiable"
        
        # Store updated findings
        response.dialog_findings = findings
        
        await db.flush()
        await db.commit()
        
        # Invalidate cache since dialog state changed
        await self._invalidate_cache(response_id, db)
        print(f"🔄 Cache invalidated for response {response_id} after new answer")
        
        return {
            "response_id": str(response_id),
            "question_id": question_id,
            "answer_stored": True,
            "findings_updated": True
        }
    
    async def calculate_relevance(
        self,
        response_id: UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Calculate updated relevance score based on current findings
        
        Args:
            response_id: CandidateResponse ID
            db: Database session
            
        Returns:
            Dict with relevance score and verdict
        """
        # Fetch response with related data
        result = await db.execute(
            select(CandidateResponse)
            .where(CandidateResponse.id == response_id)
        )
        response = result.scalar_one_or_none()
        
        if not response:
            raise ValueError(f"CandidateResponse {response_id} not found")
        
        # Fetch vacancy
        vacancy_result = await db.execute(
            select(Vacancy).where(Vacancy.id == response.vacancy_id)
        )
        vacancy = vacancy_result.scalar_one_or_none()
        
        # Fetch candidate
        candidate_result = await db.execute(
            select(Candidate).where(Candidate.id == response.candidate_id)
        )
        candidate = candidate_result.scalar_one_or_none()
        
        if not vacancy or not candidate:
            raise ValueError("Vacancy or Candidate not found")
        
        # Build payload for scorer
        scorer_payload = {
            "ids": {
                "job_id": str(vacancy.id),
                "candidate_id": str(candidate.id),
                "application_id": str(response.id)
            },
            "job_struct": self._extract_job_struct(vacancy),
            "cv_struct": self._extract_cv_struct(candidate),
            "mismatches": response.mismatch_analysis.get("mismatches", []) if response.mismatch_analysis else [],
            "missing_data": response.mismatch_analysis.get("missing_data", []) if response.mismatch_analysis else [],
            "widget_payload": {
                "dialogFindings": response.dialog_findings or {}
            },
            "weights_mode": "auto",
            "must_have_skills": [],
            "verdict_thresholds": {"fit": 75, "borderline": 60}
        }
        
        # Run scorer agent
        score_result = self.scorer_agent.run(scorer_payload)
        
        # Update response with new score
        overall_score = score_result.get("overall_match_pct", 0)
        response.relevance_score = overall_score / 100.0  # Store as 0-1 float
        
        # Update status based on verdict
        verdict = score_result.get("verdict", "не подходит")
        if verdict == "подходит":
            response.status = ResponseStatus.APPROVED
            response.rejection_reasons = None
        elif verdict == "сомнительно":
            response.status = ResponseStatus.IN_CHAT  # Keep in chat for more questions
            response.rejection_reasons = {
                "verdict": verdict,
                "summary": score_result.get("summary", {})
            }
        else:
            response.status = ResponseStatus.REJECTED
            response.rejection_reasons = {
                "verdict": verdict,
                "summary": score_result.get("summary", {}),
                "risks": score_result.get("summary", {}).get("risks", [])
            }
        
        await db.flush()
        await db.commit()
        
        return {
            "response_id": str(response_id),
            "relevance_score": overall_score,
            "verdict": verdict,
            "status": response.status.value,
            "scores_breakdown": score_result.get("scores_pct", {}),
            "summary": score_result.get("summary", {})
        }
    
    async def finalize_interview(
        self,
        response_id: UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Finalize interview and calculate final relevance score
        
        Args:
            response_id: CandidateResponse ID
            db: Database session
            
        Returns:
            Dict with final results
        """
        # Calculate final relevance
        relevance_result = await self.calculate_relevance(response_id, db)
        
        # Fetch updated response
        result = await db.execute(
            select(CandidateResponse)
            .where(CandidateResponse.id == response_id)
        )
        response = result.scalar_one_or_none()
        
        # Generate comprehensive summary for employer
        summary_result = await self.generate_summary(response_id, db)
        
        return {
            "response_id": str(response_id),
            "final_score": relevance_result["relevance_score"],
            "verdict": relevance_result["verdict"],
            "status": response.status.value,
            "total_answers": len(response.dialog_findings.get("answers", [])) if response.dialog_findings else 0,
            "summary": summary_result,
            "interview_completed": True
        }
    
    async def generate_summary(
        self,
        response_id: UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Generate comprehensive structured summary for employer
        
        Args:
            response_id: CandidateResponse ID
            db: Database session
            
        Returns:
            Dict with structured summary
        """
        # Fetch response with all related data
        result = await db.execute(
            select(CandidateResponse)
            .where(CandidateResponse.id == response_id)
        )
        response = result.scalar_one_or_none()
        
        if not response:
            raise ValueError(f"CandidateResponse {response_id} not found")
        
        # Fetch vacancy
        vacancy_result = await db.execute(
            select(Vacancy).where(Vacancy.id == response.vacancy_id)
        )
        vacancy = vacancy_result.scalar_one_or_none()
        
        # Fetch candidate
        candidate_result = await db.execute(
            select(Candidate).where(Candidate.id == response.candidate_id)
        )
        candidate = candidate_result.scalar_one_or_none()
        
        if not vacancy or not candidate:
            raise ValueError("Vacancy or Candidate not found")
        
        # Build payload for summary generator
        summary_payload = {
            "response_id": str(response_id),
            "vacancy": {
                "title": vacancy.title,
                "location": vacancy.location,
                "salary_min": vacancy.salary_min,
                "salary_max": vacancy.salary_max,
                "requirements": vacancy.requirements or {}
            },
            "candidate": {
                "name": candidate.full_name,
                "city": candidate.city,
                "resume": candidate.resume_text or ""
            },
            "mismatch_analysis": response.mismatch_analysis or {},
            "dialog_findings": response.dialog_findings or {},
            "relevance_score": response.relevance_score or 0,
            "chat_session_id": str(response.chat_session.id) if response.chat_session else None
        }
        
        # Generate summary using AI agent
        try:
            summary = self.summary_agent.run(summary_payload)
        except Exception as e:
            # Fallback to basic summary if AI fails
            summary = self._generate_basic_summary(response, vacancy, candidate)
        
        return summary
    
    def _generate_basic_summary(
        self,
        response: CandidateResponse,
        vacancy: Vacancy,
        candidate: Candidate
    ) -> Dict[str, Any]:
        """Generate a basic summary without AI if agent fails"""
        return {
            "overall_match_pct": int((response.relevance_score or 0) * 100),
            "verdict": "неизвестно",
            "must_have_coverage": {
                "covered": [],
                "missing": [],
                "partially_covered": []
            },
            "experience_breakdown": {
                "total_years": 0,
                "key_skills": []
            },
            "salary_info": {
                "expectation_min": None,
                "expectation_max": None,
                "vacancy_range_min": vacancy.salary_min,
                "vacancy_range_max": vacancy.salary_max,
                "currency": "KZT",
                "match": "неизвестно"
            },
            "location_format": {
                "candidate_city": candidate.city,
                "vacancy_city": vacancy.location,
                "employment_type": "unknown",
                "relocation_ready": False,
                "match": candidate.city.lower() == vacancy.location.lower()
            },
            "availability": {
                "ready_in_weeks": None,
                "notes": ""
            },
            "language_proficiency": {},
            "portfolio_links": [],
            "risks": [],
            "summary": {
                "one_liner": f"Кандидат: {candidate.full_name}",
                "strengths": [],
                "concerns": []
            },
            "transcript_id": str(response.chat_session.id) if response.chat_session else None
        }
    
    # Helper methods for building payloads
    
    def _build_mismatch_payload(self, vacancy: Vacancy, candidate: Candidate) -> Dict[str, Any]:
        """Build payload for mismatch detection agent"""
        return {
            "jd_text": f"{vacancy.title}\n{vacancy.description}\nLocation: {vacancy.location}\nRequirements: {json.dumps(vacancy.requirements) if vacancy.requirements else 'N/A'}",
            "cv_text": f"{candidate.full_name}\nCity: {candidate.city}\nResume: {candidate.resume_text or 'N/A'}"
        }
    
    def _build_question_payload(
        self, 
        mismatch_analysis: Dict[str, Any], 
        vacancy: Vacancy, 
        candidate: Candidate,
        language: str
    ) -> Dict[str, Any]:
        """Build payload for question generator agent"""
        # Get max_questions from vacancy (default to 3)
        max_questions = getattr(vacancy, 'max_questions', 3)
        
        # Calculate dynamic question limit based on mismatches and missing data
        # Start with 3 base questions, add more if there are many unclear areas
        mismatches = mismatch_analysis.get("mismatches", [])
        missing_data = mismatch_analysis.get("missing_data", [])
        
        # Count high-severity mismatches
        high_severity_count = sum(1 for m in mismatches if m.get("severity") == "high")
        
        # Dynamic logic: if everything is clear (< 2 high severity, < 3 missing), use 3 questions
        # Otherwise, use vacancy's max_questions setting
        if high_severity_count < 2 and len(missing_data) < 3:
            actual_limit = 3
        else:
            actual_limit = max_questions
        
        return {
            "job_struct": mismatch_analysis.get("job_struct", {}),
            "cv_struct": mismatch_analysis.get("cv_struct", {}),
            "mismatches": mismatches,
            "missing_data": missing_data,
            "coverage_snapshot": mismatch_analysis.get("coverage_snapshot", {}),
            "limits": {
                "max_questions": actual_limit
            },
            "language": language
        }
    
    def _extract_job_struct(self, vacancy: Vacancy) -> Dict[str, Any]:
        """Extract job structure from vacancy model"""
        requirements = vacancy.requirements or {}
        
        return {
            "title": vacancy.title,
            "min_experience_years": requirements.get("min_experience_years", 0),
            "required_skills": requirements.get("required_skills", []),
            "nice_to_have": requirements.get("nice_to_have", []),
            "lang_requirement": requirements.get("lang_requirement", []),
            "education_min": requirements.get("education_min", "unknown"),
            "location_requirement": {
                "city": vacancy.location,
                "employment_type": requirements.get("employment_type", "unknown")
            },
            "salary_range": {
                "min": vacancy.salary_min or 0,
                "max": vacancy.salary_max or 0,
                "currency": "KZT"
            },
            "domain": requirements.get("domain", "")
        }
    
    def _extract_cv_struct(self, candidate: Candidate) -> Dict[str, Any]:
        """Extract CV structure from candidate model"""
        return {
            "name": candidate.full_name,
            "total_experience_years": 0,  # TODO: Extract from resume_text
            "skills": [],  # TODO: Extract from resume_text
            "langs": [],  # TODO: Extract from resume_text
            "education_level": "unknown",
            "location": {
                "city": candidate.city
            },
            "employment_type": "unknown",
            "relocation_ready": False,
            "salary_expectation": {
                "value": 0,
                "currency": "KZT",
                "unknown": True
            },
            "domain_tags": [],
            "notes": candidate.resume_text or ""
        }


# Singleton instance
interview_service = InterviewService()

