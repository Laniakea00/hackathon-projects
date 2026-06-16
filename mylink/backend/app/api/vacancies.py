from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.schemas.vacancy import VacancyCreate, VacancyResponse, VacancyUpdate
from app.models.vacancy import Vacancy
from app.models.employer import Employer
from app.utils.auth import get_current_employer

router = APIRouter(prefix="/vacancies", tags=["Vacancies"])


@router.post("", response_model=VacancyResponse, status_code=status.HTTP_201_CREATED)
async def create_vacancy(
    vacancy_data: VacancyCreate,
    current_employer: Employer = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db)
):
    """Create a new vacancy"""
    new_vacancy = Vacancy(
        employer_id=current_employer.id,
        title=vacancy_data.title,
        description=vacancy_data.description,
        requirements=vacancy_data.requirements,
        location=vacancy_data.location,
        salary_min=vacancy_data.salary_min,
        salary_max=vacancy_data.salary_max
    )
    
    db.add(new_vacancy)
    await db.flush()
    await db.refresh(new_vacancy)
    
    return new_vacancy


@router.get("/{vacancy_id}", response_model=VacancyResponse)
async def get_vacancy(
    vacancy_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get vacancy by ID"""
    result = await db.execute(
        select(Vacancy).where(Vacancy.id == vacancy_id)
    )
    vacancy = result.scalar_one_or_none()
    
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found"
        )
    
    return vacancy


@router.get("", response_model=List[VacancyResponse])
async def list_vacancies(
    employer_id: UUID = None,
    db: AsyncSession = Depends(get_db)
):
    """List all vacancies, optionally filtered by employer"""
    query = select(Vacancy)
    
    if employer_id:
        query = query.where(Vacancy.employer_id == employer_id)
    
    result = await db.execute(query.order_by(Vacancy.created_at.desc()))
    vacancies = result.scalars().all()
    
    return vacancies


@router.put("/{vacancy_id}", response_model=VacancyResponse)
async def update_vacancy(
    vacancy_id: UUID,
    vacancy_data: VacancyUpdate,
    current_employer: Employer = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db)
):
    """Update a vacancy"""
    result = await db.execute(
        select(Vacancy).where(
            Vacancy.id == vacancy_id,
            Vacancy.employer_id == current_employer.id
        )
    )
    vacancy = result.scalar_one_or_none()
    
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found or you don't have permission"
        )
    
    # Update fields
    update_data = vacancy_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vacancy, field, value)
    
    await db.flush()
    await db.refresh(vacancy)
    
    return vacancy


@router.delete("/{vacancy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vacancy(
    vacancy_id: UUID,
    current_employer: Employer = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db)
):
    """Delete a vacancy"""
    result = await db.execute(
        select(Vacancy).where(
            Vacancy.id == vacancy_id,
            Vacancy.employer_id == current_employer.id
        )
    )
    vacancy = result.scalar_one_or_none()
    
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found or you don't have permission"
        )
    
    await db.delete(vacancy)
    await db.flush()

