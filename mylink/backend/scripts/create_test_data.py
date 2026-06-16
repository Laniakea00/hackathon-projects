"""
Script to create test data for development
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.models.employer import Employer
from app.models.vacancy import Vacancy
from app.models.candidate import Candidate
from app.models.response import CandidateResponse, ResponseStatus
from app.utils.auth import get_password_hash


async def create_test_data():
    """Create test data"""
    async with AsyncSessionLocal() as db:
        try:
            print("🌱 Creating test data...")
            
            # Create test employer
            employer = Employer(
                company_name="Tech Solutions Inc",
                email="hr@techsolutions.com",
                password_hash=get_password_hash("password123")
            )
            db.add(employer)
            await db.flush()
            print(f"✅ Created employer: {employer.email}")
            
            # Create test vacancies
            vacancy1 = Vacancy(
                employer_id=employer.id,
                title="Senior Python Developer",
                description="We are looking for an experienced Python developer...",
                requirements={"experience": "3+ years", "skills": ["Python", "FastAPI", "PostgreSQL"]},
                location="Moscow",
                salary_min=150000,
                salary_max=250000
            )
            db.add(vacancy1)
            
            vacancy2 = Vacancy(
                employer_id=employer.id,
                title="Frontend Developer",
                description="Join our team as a frontend developer...",
                requirements={"experience": "2+ years", "skills": ["React", "TypeScript", "CSS"]},
                location="Saint Petersburg",
                salary_min=120000,
                salary_max=200000
            )
            db.add(vacancy2)
            await db.flush()
            print(f"✅ Created vacancies: {vacancy1.title}, {vacancy2.title}")
            
            # Create test candidates
            candidate1 = Candidate(
                full_name="Ivan Petrov",
                email="ivan.petrov@example.com",
                phone="+79991234567",
                city="Moscow",
                resume_text="Experienced Python developer with 5 years of experience..."
            )
            db.add(candidate1)
            
            candidate2 = Candidate(
                full_name="Maria Sidorova",
                email="maria.sidorova@example.com",
                phone="+79997654321",
                city="Kazan",
                resume_text="Frontend developer specializing in React..."
            )
            db.add(candidate2)
            await db.flush()
            print(f"✅ Created candidates: {candidate1.full_name}, {candidate2.full_name}")
            
            # Create test response
            response1 = CandidateResponse(
                vacancy_id=vacancy1.id,
                candidate_id=candidate1.id,
                status=ResponseStatus.NEW
            )
            db.add(response1)
            await db.flush()
            print(f"✅ Created response for {candidate1.full_name} to {vacancy1.title}")
            
            await db.commit()
            
            print("\n🎉 Test data created successfully!")
            print("\n📋 Summary:")
            print(f"   Employer: {employer.email} (password: password123)")
            print(f"   Vacancies: 2")
            print(f"   Candidates: 2")
            print(f"   Responses: 1")
            print(f"\n   Response ID for WebSocket test: {response1.id}")
            
        except Exception as e:
            print(f"❌ Error creating test data: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(create_test_data())

