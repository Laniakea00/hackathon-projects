from typing import List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.models.chat import ChatSession, ChatMessage, SenderType
from app.models.response import CandidateResponse, ResponseStatus
from app.models.vacancy import Vacancy
from app.models.candidate import Candidate


class ChatService:
    """Service for handling chat logic"""
    
    @staticmethod
    async def get_or_create_session(response_id: UUID, db: AsyncSession) -> ChatSession:
        """Get existing session or create a new one"""
        # Try to find existing session
        result = await db.execute(
            select(ChatSession).where(ChatSession.response_id == response_id)
        )
        session = result.scalar_one_or_none()
        
        if session:
            return session
        
        # Create new session if not found
        session = ChatSession(response_id=response_id)
        db.add(session)
        await db.flush()
        await db.refresh(session)
        return session
    
    @staticmethod
    async def create_session(response_id: UUID, db: AsyncSession) -> ChatSession:
        """Create a new chat session (deprecated - use get_or_create_session)"""
        return await ChatService.get_or_create_session(response_id, db)
    
    @staticmethod
    async def add_message(
        session_id: UUID,
        sender_type: SenderType,
        message_text: str,
        db: AsyncSession
    ) -> ChatMessage:
        """Add a message to chat session"""
        message = ChatMessage(
            session_id=session_id,
            sender_type=sender_type,
            message_text=message_text
        )
        db.add(message)
        await db.flush()
        await db.refresh(message)
        return message
    
    @staticmethod
    async def get_session_messages(session_id: UUID, db: AsyncSession) -> List[ChatMessage]:
        """Get all messages for a session"""
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        return result.scalars().all()
    
    @staticmethod
    async def end_session(session_id: UUID, db: AsyncSession):
        """End a chat session"""
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            session.ended_at = datetime.utcnow()
            await db.flush()
    
    @staticmethod
    async def get_bot_questions() -> List[str]:
        """Get predefined bot questions (mock)"""
        return [
            "Здравствуйте! Подтвердите, пожалуйста, ваш город проживания?",
            "Какой у вас опыт работы в годах?",
            "Готовы ли вы к удаленной работе?",
        ]
    
    @staticmethod
    async def process_candidate_answer(
        response_id: UUID,
        question_index: int,
        answer: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Process candidate answer and determine if they should continue
        Mock logic for MVP
        """
        # Get response with related data
        result = await db.execute(
            select(CandidateResponse)
            .where(CandidateResponse.id == response_id)
        )
        response = result.scalar_one_or_none()
        
        if not response:
            return {"continue": False, "reason": "Response not found"}
        
        # Get vacancy and candidate
        vacancy_result = await db.execute(
            select(Vacancy).where(Vacancy.id == response.vacancy_id)
        )
        vacancy = vacancy_result.scalar_one_or_none()
        
        candidate_result = await db.execute(
            select(Candidate).where(Candidate.id == response.candidate_id)
        )
        candidate = candidate_result.scalar_one_or_none()
        
        if not vacancy or not candidate:
            return {"continue": False, "reason": "Data not found"}
        
        # Mock logic: Check city match on first question
        if question_index == 0:
            # Simple city comparison (case-insensitive)
            if answer.lower().strip() != vacancy.location.lower().strip():
                return {
                    "continue": False,
                    "reason": f"Город не совпадает с требованиями вакансии ({vacancy.location})",
                    "approved": False
                }
        
        # If all questions answered, approve
        if question_index >= 2:  # Last question (index 2)
            return {
                "continue": False,
                "reason": "Все вопросы пройдены",
                "approved": True
            }
        
        return {"continue": True}
    
    @staticmethod
    async def finalize_response(
        response_id: UUID,
        approved: bool,
        rejection_reason: str,
        db: AsyncSession
    ):
        """Finalize candidate response with score and status"""
        result = await db.execute(
            select(CandidateResponse).where(CandidateResponse.id == response_id)
        )
        response = result.scalar_one_or_none()
        
        if response:
            if approved:
                response.status = ResponseStatus.APPROVED
                response.relevance_score = 1.0
                response.rejection_reasons = None
            else:
                response.status = ResponseStatus.REJECTED
                response.relevance_score = 0.0
                response.rejection_reasons = {"reason": rejection_reason}
            
            await db.flush()

