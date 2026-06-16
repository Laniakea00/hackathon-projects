from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.schemas.response import ResponseCreate, ResponseResponse, ResponseListItem
from app.models.response import CandidateResponse, ResponseStatus
from app.models.vacancy import Vacancy
from app.models.candidate import Candidate
from app.models.employer import Employer
from app.models.chat import ChatSession, ChatMessage
from app.utils.auth import get_current_employer
from app.schemas.chat import ChatSessionResponse, ChatMessageResponse
from app.services.interview_service import interview_service

router = APIRouter(prefix="/responses", tags=["Responses"])


@router.get("/candidate/{candidate_id}/vacancy/{vacancy_id}", response_model=ResponseResponse)
async def get_candidate_response_for_vacancy(
    candidate_id: UUID,
    vacancy_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get existing response for a candidate and vacancy combination"""
    result = await db.execute(
        select(CandidateResponse)
        .where(
            CandidateResponse.candidate_id == candidate_id,
            CandidateResponse.vacancy_id == vacancy_id
        )
    )
    response = result.scalar_one_or_none()
    
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No response found for this candidate and vacancy"
        )
    
    # Get candidate info
    candidate_result = await db.execute(
        select(Candidate).where(Candidate.id == response.candidate_id)
    )
    candidate = candidate_result.scalar_one_or_none()
    
    return ResponseResponse(
        id=response.id,
        vacancy_id=response.vacancy_id,
        candidate_id=response.candidate_id,
        candidate_name=candidate.full_name if candidate else "Unknown",
        candidate_email=candidate.email if candidate else "",
        candidate_city=candidate.city if candidate else "",
        status=response.status,
        relevance_score=response.relevance_score,
        rejection_reasons=response.rejection_reasons,
        created_at=response.created_at
    )


@router.post("", response_model=ResponseResponse, status_code=status.HTTP_201_CREATED)
async def create_response(
    response_data: ResponseCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new candidate response to a vacancy"""
    # Verify vacancy exists
    vacancy_result = await db.execute(
        select(Vacancy).where(Vacancy.id == response_data.vacancy_id)
    )
    vacancy = vacancy_result.scalar_one_or_none()
    
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found"
        )
    
    # Verify candidate exists
    candidate_result = await db.execute(
        select(Candidate).where(Candidate.id == response_data.candidate_id)
    )
    candidate = candidate_result.scalar_one_or_none()
    
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    # Check if response already exists
    existing_result = await db.execute(
        select(CandidateResponse).where(
            CandidateResponse.vacancy_id == response_data.vacancy_id,
            CandidateResponse.candidate_id == response_data.candidate_id
        )
    )
    existing_response = existing_result.scalar_one_or_none()
    
    if existing_response:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Response already exists for this vacancy and candidate"
        )
    
    # Create new response
    new_response = CandidateResponse(
        vacancy_id=response_data.vacancy_id,
        candidate_id=response_data.candidate_id,
        status=ResponseStatus.NEW
    )
    
    db.add(new_response)
    await db.flush()
    await db.refresh(new_response)
    
    return new_response


@router.get("/{response_id}", response_model=ResponseResponse)
async def get_response(
    response_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get response by ID"""
    result = await db.execute(
        select(CandidateResponse).where(CandidateResponse.id == response_id)
    )
    response = result.scalar_one_or_none()
    
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Response not found"
        )
    
    return response


@router.get("", response_model=List[ResponseListItem])
async def list_responses(
    vacancy_id: Optional[UUID] = None,
    current_employer: Employer = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db)
):
    """
    List all responses for employer's vacancies
    Optionally filter by vacancy_id
    """
    query = (
        select(CandidateResponse, Candidate)
        .join(Vacancy, CandidateResponse.vacancy_id == Vacancy.id)
        .join(Candidate, CandidateResponse.candidate_id == Candidate.id)
        .where(Vacancy.employer_id == current_employer.id)
    )
    
    if vacancy_id:
        query = query.where(CandidateResponse.vacancy_id == vacancy_id)
    
    result = await db.execute(query.order_by(CandidateResponse.created_at.desc()))
    rows = result.all()
    
    # Build response list with candidate info
    response_list = []
    for response, candidate in rows:
        item = ResponseListItem(
            id=response.id,
            vacancy_id=response.vacancy_id,
            candidate_id=response.candidate_id,
            status=response.status,
            relevance_score=response.relevance_score,
            rejection_reasons=response.rejection_reasons,
            created_at=response.created_at,
            candidate_name=candidate.full_name,
            candidate_email=candidate.email,
            candidate_city=candidate.city
        )
        response_list.append(item)
    
    return response_list


@router.get("/{response_id}/chat", response_model=ChatSessionResponse)
async def get_response_chat_history(
    response_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get complete chat history for a response"""
    from sqlalchemy.orm import selectinload
    
    # Get response with chat_session eagerly loaded
    response_result = await db.execute(
        select(CandidateResponse)
        .options(selectinload(CandidateResponse.chat_session))
        .where(CandidateResponse.id == response_id)
    )
    response = response_result.scalar_one_or_none()
    
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Response not found"
        )
    
    # Get chat session
    if not response.chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No chat session found for this response"
        )
    
    # Get all messages
    messages_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == response.chat_session.id)
        .order_by(ChatMessage.created_at)
    )
    messages = messages_result.scalars().all()
    
    # Build response
    chat_data = ChatSessionResponse(
        id=response.chat_session.id,
        response_id=response.chat_session.response_id,
        started_at=response.chat_session.started_at,
        ended_at=response.chat_session.ended_at,
        messages=[
            ChatMessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                sender_type=msg.sender_type,
                message_text=msg.message_text,
                created_at=msg.created_at
            )
            for msg in messages
        ]
    )
    
    return chat_data


@router.get("/{response_id}/summary")
async def get_response_summary(
    response_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive structured summary for employer review"""
    # Verify response exists
    response_result = await db.execute(
        select(CandidateResponse).where(CandidateResponse.id == response_id)
    )
    response = response_result.scalar_one_or_none()
    
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Response not found"
        )
    
    # Generate or retrieve summary
    try:
        summary = await interview_service.generate_summary(response_id, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate summary: {str(e)}"
        )
    
    return summary


@router.post("/{response_id}/approve")
async def approve_candidate(
    response_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Approve candidate - HR action"""
    from sqlalchemy.orm import selectinload
    
    # Verify response exists and eagerly load chat_session
    response_result = await db.execute(
        select(CandidateResponse)
        .options(selectinload(CandidateResponse.chat_session))
        .where(CandidateResponse.id == response_id)
    )
    response = response_result.scalar_one_or_none()
    
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Response not found"
        )
    
    # Check if already processed
    if response.status in [ResponseStatus.APPROVED, ResponseStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Candidate already {response.status.value}. Use update endpoint to change decision."
        )
    
    # Update status to approved
    response.status = ResponseStatus.APPROVED
    await db.commit()
    await db.refresh(response)
    
    # Send polite message to candidate via chat
    approval_message = (
        "🎉 Отличные новости! Наш HR-специалист заинтересовался вашей кандидатурой. "
        "Поздравляем! Будьте готовы к следующему этапу собеседования. "
        "Мы свяжемся с вами в ближайшее время для уточнения деталей."
    )
    
    if response.chat_session:
        from app.services.chat_service import ChatService
        from app.models.chat import SenderType
        
        await ChatService.add_message(
            response.chat_session.id,
            SenderType.BOT,
            approval_message,
            db
        )
        await db.commit()
    
    # Send message via WebSocket if candidate is connected
    from app.api.chat import send_message_to_candidate
    await send_message_to_candidate(response_id, approval_message, "hr_decision")
    
    return {"status": "approved", "message": "Candidate approved successfully"}


@router.post("/{response_id}/reject")
async def reject_candidate(
    response_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Reject candidate - HR action"""
    from sqlalchemy.orm import selectinload
    
    # Verify response exists and eagerly load chat_session
    response_result = await db.execute(
        select(CandidateResponse)
        .options(selectinload(CandidateResponse.chat_session))
        .where(CandidateResponse.id == response_id)
    )
    response = response_result.scalar_one_or_none()
    
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Response not found"
        )
    
    # Check if already processed
    if response.status in [ResponseStatus.APPROVED, ResponseStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Candidate already {response.status.value}. Use update endpoint to change decision."
        )
    
    # Update status to rejected
    response.status = ResponseStatus.REJECTED
    await db.commit()
    await db.refresh(response)
    
    # Send polite message to candidate via chat
    rejection_message = (
        "Благодарим вас за интерес к нашей вакансии и за время, уделённое собеседованию. "
        "К сожалению, на данный момент мы приняли решение продолжить поиск кандидата, "
        "чей профиль более точно соответствует текущим требованиям позиции. "
        "Мы ценим ваш профессионализм и желаем вам успехов в карьере. "
        "Возможно, в будущем у нас появятся вакансии, которые лучше подойдут вашему опыту."
    )
    
    if response.chat_session:
        from app.services.chat_service import ChatService
        from app.models.chat import SenderType
        
        await ChatService.add_message(
            response.chat_session.id,
            SenderType.BOT,
            rejection_message,
            db
        )
        await db.commit()
    
    # Send message via WebSocket if candidate is connected
    from app.api.chat import send_message_to_candidate
    await send_message_to_candidate(response_id, rejection_message, "hr_decision")
    
    return {"status": "rejected", "message": "Candidate rejected successfully"}


@router.put("/{response_id}/update-decision")
async def update_decision(
    response_id: UUID,
    new_status: str,  # "approved" or "rejected"
    db: AsyncSession = Depends(get_db)
):
    """Update HR decision - allows changing from approved to rejected or vice versa"""
    from sqlalchemy.orm import selectinload
    
    # Validate new_status
    if new_status not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be 'approved' or 'rejected'"
        )
    
    # Verify response exists and eagerly load chat_session
    response_result = await db.execute(
        select(CandidateResponse)
        .options(selectinload(CandidateResponse.chat_session))
        .where(CandidateResponse.id == response_id)
    )
    response = response_result.scalar_one_or_none()
    
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Response not found"
        )
    
    # Check if status is actually changing
    current_status = response.status
    target_status = ResponseStatus.APPROVED if new_status == "approved" else ResponseStatus.REJECTED
    
    if current_status == target_status:
        return {"status": new_status, "message": f"Candidate already {new_status}"}
    
    # Update status
    response.status = target_status
    await db.commit()
    await db.refresh(response)
    
    # Send update message to candidate
    if new_status == "approved":
        update_message = (
            "📝 Обновление: Наш HR-специалист пересмотрел вашу кандидатуру и принял решение продолжить с вами работу. "
            "Поздравляем! Будьте готовы к следующему этапу собеседования."
        )
    else:
        update_message = (
            "📝 Обновление: После дополнительного рассмотрения, мы приняли решение продолжить поиск кандидата, "
            "чей профиль более точно соответствует текущим требованиям позиции. "
            "Благодарим вас за понимание."
        )
    
    if response.chat_session:
        from app.services.chat_service import ChatService
        from app.models.chat import SenderType
        
        await ChatService.add_message(
            response.chat_session.id,
            SenderType.BOT,
            update_message,
            db
        )
        await db.commit()
    
    # Send message via WebSocket if candidate is connected
    from app.api.chat import send_message_to_candidate
    await send_message_to_candidate(response_id, update_message, "hr_decision_update")
    
    return {"status": new_status, "message": f"Decision updated to {new_status} successfully"}

