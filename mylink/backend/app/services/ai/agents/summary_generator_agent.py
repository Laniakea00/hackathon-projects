"""
SummaryGeneratorAgent - Generates structured summaries for employer review

This agent creates comprehensive candidate summaries including:
- Overall match percentage
- Must-have skills coverage
- Years of experience breakdown
- Salary expectations
- Location and work format
- Availability timeline
- English/language proficiency
- Portfolio/project links
- Risk assessment
- Transcript reference
"""

from typing import Any, Dict
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.services.ai.llm_client import get_llm
from app.services.ai import Agent


PROMPT_SYSTEM = (
    "You are Summary Generator for hiring process. Create structured, fact-based summaries "
    "for employers reviewing candidates. Extract and organize information from mismatch analysis, "
    "dialog findings, and relevance scores. Output strictly valid JSON. Be concise and factual."
)

PROMPT_USER = (
    "Input data:\n{input_json}\n\n"
    "Create a comprehensive summary for the employer following this exact structure:\n{schema_json}\n\n"
    "Rules:\n"
    "- Extract only factual information from inputs\n"
    "- If data is missing/unclear, mark as 'unknown' or null\n"
    "- Calculate experience years from dialog answers or CV\n"
    "- Extract salary from dialog_findings or CV\n"
    "- Identify risks from high-severity mismatches\n"
    "- Generate concise one-liner conclusion\n"
    "- Strict JSON only, no extra text\n"
)

SCHEMA_EXAMPLE = {
    "overall_match_pct": 75,
    "verdict": "подходит|сомнительно|не подходит",
    "must_have_coverage": {
        "covered": ["python", "django"],
        "missing": ["docker"],
        "partially_covered": ["kubernetes"]
    },
    "experience_breakdown": {
        "total_years": 5,
        "key_skills": [
            {"skill": "python", "years": 5},
            {"skill": "django", "years": 3}
        ]
    },
    "salary_info": {
        "expectation_min": 500000,
        "expectation_max": 700000,
        "vacancy_range_min": 600000,
        "vacancy_range_max": 800000,
        "currency": "KZT",
        "match": "подходит|выше ожиданий|ниже ожиданий|неизвестно"
    },
    "location_format": {
        "candidate_city": "Алматы",
        "vacancy_city": "Алматы",
        "employment_type": "hybrid",
        "relocation_ready": False,
        "match": True
    },
    "availability": {
        "ready_in_weeks": 2,
        "notes": "Может выйти через 2 недели"
    },
    "language_proficiency": {
        "english": "B2",
        "kazakh": "C2",
        "russian": "C2",
        "required_level": "B2",
        "match": True
    },
    "portfolio_links": [
        {"type": "github", "url": "https://github.com/user"},
        {"type": "linkedin", "url": "https://linkedin.com/in/user"}
    ],
    "risks": [
        {"severity": "high", "risk": "Отсутствует ключевой навык Docker"},
        {"severity": "medium", "risk": "Зарплатные ожидания на верхней границе"}
    ],
    "summary": {
        "one_liner": "Сильный кандидат с 5 годами опыта в Python, готов к старту через 2 недели",
        "strengths": ["Опыт с Django", "Готов к гибридному формату"],
        "concerns": ["Нет опыта с Docker", "Высокие зарплатные ожидания"]
    },
    "transcript_id": "uuid-of-chat-session"
}


class SummaryGeneratorAgent(Agent):
    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        llm = get_llm(temperature=0)
        prompt = ChatPromptTemplate.from_messages([
            ("system", PROMPT_SYSTEM),
            ("user", PROMPT_USER),
        ])
        chain = prompt | llm | StrOutputParser()

        input_json = json.dumps(payload, ensure_ascii=False)
        schema_json = json.dumps(SCHEMA_EXAMPLE, ensure_ascii=False)
        raw = chain.invoke({"input_json": input_json, "schema_json": schema_json})

        # Extract JSON body
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end >= start:
            raw = raw[start : end + 1]

        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Invalid JSON result for Summary Generator")

        return data

