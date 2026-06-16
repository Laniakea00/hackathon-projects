from typing import Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.vacancy import Vacancy
from app.models.candidate import Candidate


class RelevanceService:
    """Service for calculating candidate relevance (mock for MVP)"""
    
    @staticmethod
    async def calculate_relevance(
        vacancy_id: UUID,
        candidate_id: UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Calculate relevance score between vacancy and candidate
        Mock implementation for MVP
        """
        # Get vacancy
        vacancy_result = await db.execute(
            select(Vacancy).where(Vacancy.id == vacancy_id)
        )
        vacancy = vacancy_result.scalar_one_or_none()
        
        # Get candidate
        candidate_result = await db.execute(
            select(Candidate).where(Candidate.id == candidate_id)
        )
        candidate = candidate_result.scalar_one_or_none()
        
        if not vacancy or not candidate:
            return {
                "score": 0.0,
                "reasons": ["Данные не найдены"]
            }
        
        score = 0.0
        reasons = []
        
        # Simple mock logic: check city match
        if vacancy.location.lower() == candidate.city.lower():
            score += 0.5
            reasons.append("Город совпадает")
        else:
            reasons.append(f"Город не совпадает (требуется: {vacancy.location})")
        
        # Check if resume exists
        if candidate.resume_text:
            score += 0.3
            reasons.append("Резюме предоставлено")
        else:
            reasons.append("Резюме отсутствует")
        
        # Check if phone provided
        if candidate.phone:
            score += 0.2
            reasons.append("Контактный телефон указан")
        
        return {
            "score": min(score, 1.0),
            "reasons": reasons
        }

