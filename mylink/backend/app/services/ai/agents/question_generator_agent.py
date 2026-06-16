from typing import Any, Dict, List
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.services.ai.llm_client import get_llm
from app.services.ai import Agent
from app.config import settings


ALLOWED_ANSWER_TYPES = {
    "yes_no",
    "level_select",
    "years_number",
    "free_text_short",
    "option_select",
    "salary_number",
    "date_text",
}

ALLOWED_CRITERIA = {
    "skills",
    "experience",
    "location",
    "format",
    "langs",
    "compensation",
    "education",
    "domain",
}

PROMPT_SYSTEM = (
    "You are Clarifier in a hiring funnel. Input is normalized JD/CV structures with mismatches and missing_data. "
    "Select up to N most important clarification topics (must-have, experience below min, location/format, language/CEFR, compensation). "
    "Write short, unambiguous, safe, professional, empathetic questions in Russian (≤ 25 words), one topic per question. "
    "Return strictly valid JSON as per the schema. Avoid any discriminatory or sensitive topics."
)

PROMPT_USER = (
    "Input JSON (ru):\n{input_json}\n\n"
    "Prioritization (desc): must-have high blockers; experience below min; location/format; language (CEFR); compensation; domain.\n"
    "If missing_data is empty and no critical mismatches -> return 0 questions and only closing_message.\n\n"
    "Output JSON schema EXACTLY:\n{schema_json}\n\n"
    "Constraints:\n"
    "- questions ≤ 25 words, 1 topic, no jargon or leading phrasing.\n"
    "- Use only provided enums for 'criterion' and 'answer_type'.\n"
    "- For option_select provide concrete neutral options.\n"
    "- language: ru; tone: профессиональный, вежливый, без давления.\n"
    "- Strict JSON only."
)

SCHEMA_EXAMPLE = {
    "questions": [
        {
            "id": "q1",
            "priority": 1,
            "criterion": "skills",
            "reason": "коротко, почему этот вопрос важен",
            "question_text": "сам вопрос (вежливо, ≤25 слов)",
            "answer_type": "yes_no",
            "options": ["при answer_type=option_select перечислите варианты"],
            "validation": {
                "pattern": "",
                "allowed_levels": ["A1", "A2", "B1", "B2", "C1", "C2"],
                "min": 0,
                "max": 50,
            },
            "examples": ["1–2 мини-примера корректного ответа"],
            "on_ambiguous_followup": "если ответ расплывчатый — задать эту короткую переспрашивающую реплику",
        }
    ],
    "closing_message": "дружелюбная благодарность + что будет дальше (1–2 предложения)",
    "meta": {
        "max_questions": 3,
        "tone": "профессиональный, вежливый, без давления",
        "language": "ru",
    },
}


class QuestionGeneratorAgent(Agent):
    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        max_questions = _get_max_questions(payload)
        llm = get_llm(temperature=0)
        prompt = ChatPromptTemplate.from_messages([
            ("system", PROMPT_SYSTEM),
            ("user", PROMPT_USER),
        ])
        chain = prompt | llm | StrOutputParser()

        input_json = json.dumps(payload, ensure_ascii=False)
        # Inject runtime max into example for clarity
        schema_with_max = dict(SCHEMA_EXAMPLE)
        schema_with_max["meta"] = {
            "max_questions": max_questions,
            "tone": "профессиональный, вежливый, без давления",
            "language": "ru",
        }
        schema_json = json.dumps(schema_with_max, ensure_ascii=False)
        raw = chain.invoke({"input_json": input_json, "schema_json": schema_json})

        # Extract JSON body if model emits extra text
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end >= start:
            raw = raw[start : end + 1]

        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Invalid JSON result for Clarifier agent")

        return _postprocess_questions(data, max_questions)


def _get_max_questions(payload: Dict[str, Any]) -> int:
    limits = payload.get("limits") or {}
    value = limits.get("max_questions")
    if isinstance(value, int) and value > 0:
        return min(value, settings.AI_MAX_QUESTIONS)
    return int(settings.AI_MAX_QUESTIONS)


def _postprocess_questions(data: Dict[str, Any], max_questions: int) -> Dict[str, Any]:
    questions: List[Dict[str, Any]] = list(data.get("questions") or [])

    # Enforce max questions and filter invalid entries
    cleaned: List[Dict[str, Any]] = []
    for item in questions:
        if not isinstance(item, dict):
            continue
        criterion = item.get("criterion")
        answer_type = item.get("answer_type")
        if criterion not in ALLOWED_CRITERIA:
            continue
        if answer_type not in ALLOWED_ANSWER_TYPES:
            continue
        cleaned.append(item)
        if len(cleaned) >= max_questions:
            break

    data["questions"] = cleaned

    # Ensure meta exists and is correct
    meta = dict(data.get("meta") or {})
    meta.setdefault("tone", "профессиональный, вежливый, без давления")
    meta.setdefault("language", "ru")
    meta["max_questions"] = max_questions
    data["meta"] = meta

    # Ensure closing_message exists
    if not isinstance(data.get("closing_message"), str) or not data["closing_message"].strip():
        data["closing_message"] = (
            "Спасибо за ответы! Мы передадим информацию команде и вернёмся с обратной связью."
        )

    return data
