"""
Test script for InterviewService
Run from backend directory: python test_interview_service.py
"""

import asyncio
import sys
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.insert(0, '.')

from app.config import settings
from app.models.employer import Employer
from app.models.vacancy import Vacancy
from app.models.candidate import Candidate
from app.models.response import CandidateResponse
from app.services.interview_service import interview_service
from app.db.base import Base


async def test_interview_flow():
    """Test complete interview flow"""
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Create tables if needed
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        print("\n" + "="*60)
        print("🧪 TESTING INTERVIEW SERVICE")
        print("="*60 + "\n")
        
        # Step 1: Create test employer
        print("📝 Step 1: Creating test employer...")
        employer = Employer(
            company_name="Test Company",
            email=f"test_{uuid4().hex[:8]}@example.com",
            password_hash="test_hash"
        )
        session.add(employer)
        await session.flush()
        print(f"✅ Employer created: {employer.id}")
        
        # Step 2: Create test vacancy
        print("\n📝 Step 2: Creating test vacancy...")
        vacancy = Vacancy(
            employer_id=employer.id,
            title="Senior Python Developer",
            description="We are looking for an experienced Python developer",
            location="Almaty",
            salary_min=500000,
            salary_max=800000,
            requirements={
                "min_experience_years": 3,
                "required_skills": ["python", "fastapi", "postgresql"],
                "nice_to_have": ["docker", "kubernetes"],
                "lang_requirement": [{"lang": "EN", "level": "B2"}],
                "education_min": "bachelor",
                "employment_type": "office",
                "domain": "fintech"
            }
        )
        session.add(vacancy)
        await session.flush()
        print(f"✅ Vacancy created: {vacancy.id}")
        print(f"   Title: {vacancy.title}")
        print(f"   Location: {vacancy.location}")
        
        # Step 3: Create test candidate
        print("\n📝 Step 3: Creating test candidate...")
        candidate = Candidate(
            full_name="Ivan Petrov",
            email=f"candidate_{uuid4().hex[:8]}@example.com",
            phone="+77001234567",
            city="Astana",  # Different city - should trigger question
            resume_text="""
            Experienced Python developer with 2 years of experience.
            Skills: Python, Django, MySQL
            Education: Bachelor in Computer Science
            English: Intermediate (B1)
            """
        )
        session.add(candidate)
        await session.flush()
        print(f"✅ Candidate created: {candidate.id}")
        print(f"   Name: {candidate.full_name}")
        print(f"   City: {candidate.city}")
        
        # Step 4: Create candidate response
        print("\n📝 Step 4: Creating candidate response...")
        response = CandidateResponse(
            vacancy_id=vacancy.id,
            candidate_id=candidate.id
        )
        session.add(response)
        await session.flush()
        await session.commit()
        print(f"✅ Response created: {response.id}")
        
        # Step 5: Start interview (AI analysis)
        print("\n" + "="*60)
        print("🤖 Step 5: Starting AI-powered interview...")
        print("="*60)
        
        try:
            interview_result = await interview_service.start_interview(
                response_id=response.id,
                db=session,
                language="ru"
            )
            
            print("\n✅ Interview started successfully!")
            print(f"\n📊 Mismatch Summary:")
            print(f"   Total mismatches: {interview_result['mismatch_summary']['total_mismatches']}")
            print(f"   Missing data: {interview_result['mismatch_summary']['missing_data']}")
            
            print(f"\n❓ Generated Questions ({interview_result['total_questions']}):")
            for i, q in enumerate(interview_result['questions'], 1):
                print(f"\n   Question {i} (ID: {q.get('id')}):")
                print(f"   Criterion: {q.get('criterion')}")
                print(f"   Priority: {q.get('priority')}")
                print(f"   Text: {q.get('question_text')}")
                print(f"   Answer Type: {q.get('answer_type')}")
            
            print(f"\n💬 Closing Message:")
            print(f"   {interview_result['closing_message']}")
            
            # Step 6: Simulate answering questions
            print("\n" + "="*60)
            print("💬 Step 6: Simulating candidate answers...")
            print("="*60)
            
            questions = interview_result['questions']
            if questions:
                # Answer first question
                first_q = questions[0]
                test_answer = "Да, я готов к переезду в Алматы"
                
                print(f"\n📝 Answering question: {first_q.get('id')}")
                print(f"   Answer: {test_answer}")
                
                answer_result = await interview_service.process_answer(
                    response_id=response.id,
                    question_id=first_q.get('id'),
                    answer_text=test_answer,
                    db=session
                )
                
                print(f"✅ Answer processed: {answer_result}")
                
                # Step 7: Calculate relevance after answer
                print("\n" + "="*60)
                print("📊 Step 7: Calculating relevance score...")
                print("="*60)
                
                relevance_result = await interview_service.calculate_relevance(
                    response_id=response.id,
                    db=session
                )
                
                print(f"\n✅ Relevance calculated!")
                print(f"   Overall Score: {relevance_result['relevance_score']}%")
                print(f"   Verdict: {relevance_result['verdict']}")
                print(f"   Status: {relevance_result['status']}")
                print(f"\n   Scores Breakdown:")
                for criterion, score in relevance_result['scores_breakdown'].items():
                    print(f"      {criterion}: {score}%")
                
                # Step 8: Finalize interview
                print("\n" + "="*60)
                print("✅ Step 8: Finalizing interview...")
                print("="*60)
                
                final_result = await interview_service.finalize_interview(
                    response_id=response.id,
                    db=session
                )
                
                print(f"\n✅ Interview finalized!")
                print(f"   Final Score: {final_result['final_score']}%")
                print(f"   Verdict: {final_result['verdict']}")
                print(f"   Total Answers: {final_result['total_answers']}")
                print(f"   Status: {final_result['status']}")
            
            print("\n" + "="*60)
            print("✅ ALL TESTS PASSED!")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"\n❌ Error during interview: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(test_interview_flow())

