from typing import Any, Dict, List, Optional, Tuple
import re
from datetime import datetime, timezone

from app.services.ai import Agent


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_bool(text: str) -> Optional[bool]:
    t = text.strip().lower()
    if t in {"да", "yes", "y", "ok", "true", "+"}:
        return True
    if t in {"нет", "no", "n", "false", "-"}:
        return False
    return None


def _validate_level(level: str, allowed: Optional[List[str]]) -> Optional[str]:
    if not level:
        return None
    lvl = level.strip().upper()
    options = allowed or ["A1", "A2", "B1", "B2", "C1", "C2"]
    return lvl if lvl in options else None


def _parse_int_in_range(text: str, default_min: int, default_max: int, rng: Optional[Tuple[Optional[int], Optional[int]]] = None) -> Optional[int]:
    try:
        value = int(re.sub(r"[^0-9-]", "", text))
    except Exception:
        return None
    min_v = rng[0] if rng and rng[0] is not None else default_min
    max_v = rng[1] if rng and rng[1] is not None else default_max
    if value < min_v or value > max_v:
        return None
    return value


def _match_option(options: List[str], text: str) -> Optional[str]:
    if not options:
        return None
    t = text.strip().lower()
    for opt in options:
        if t == str(opt).strip().lower():
            return opt
    return None


def _validate_free_text(text: str, pattern: Optional[str], max_len: int = 200) -> Optional[str]:
    if text is None:
        return None
    value = text.strip()
    if len(value) == 0 or len(value) > max_len:
        return None
    if pattern:
        try:
            if not re.fullmatch(pattern, value):
                return None
        except re.error:
            # Invalid pattern; ignore regex constraint in production to avoid runtime crash
            pass
    return value


def _validate_date_yyyy_mm(text: str) -> Optional[str]:
    if not isinstance(text, str):
        return None
    if re.fullmatch(r"\d{4}-\d{2}", text.strip()):
        return text.strip()
    return None


def _is_skip(text: str) -> bool:
    return text.strip().lower() in {"skip", "пропустить"}


def _is_stop(text: str) -> bool:
    return text.strip().lower() in {"stop", "стоп"}


def _greeting(context: Dict[str, Any]) -> str:
    job_title = (context or {}).get("job_title")
    company = (context or {}).get("company")
    if company and job_title:
        return f"Здравствуйте! Я виртуальный ассистент команды {company}. Пара уточнений по вакансии {job_title}, займёт 1–2 минуты."
    return "Здравствуйте! Пара уточнений по вакансии, займёт 1–2 минуты."


def _units_for(answer_type: str) -> str:
    return {
        "yes_no": "boolean",
        "level_select": "cefr",
        "years_number": "years",
        "free_text_short": "text",
        "option_select": "option",
        "salary_number": "currency",
        "date_text": "date",
    }.get(answer_type, "text")


def _validate_answer(question: Dict[str, Any], raw: str, second_try: Optional[str], currency: Optional[str]) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """Validate and normalize a user's answer for a single question.

    Returns (normalized_block, transcript_tail)
    """
    transcript_tail: List[Dict[str, str]] = []
    answer_type: str = question.get("answer_type", "free_text_short")
    validation = question.get("validation") or {}
    options = question.get("options") or []
    units = _units_for(answer_type)

    # Helper to record follow-up assistant message
    def add_followup(msg: str) -> None:
        transcript_tail.append({"role": "assistant", "text": msg, "ts": _now_iso()})

    # First pass validation
    normalized: Dict[str, Any] = {"value": None, "units": units, "valid": False, "unknown": False, "skipped": False}
    notes: List[str] = []

    # Skip/Stop handled by caller

    if answer_type == "yes_no":
        value = _normalize_bool(raw)
        if value is None and second_try is not None:
            add_followup(question.get("on_ambiguous_followup") or "Правильно ли я понял(а)? Пожалуйста, ответьте да или нет.")
            value = _normalize_bool(second_try)
        if value is not None:
            normalized.update({"value": str(value).lower(), "valid": True})
        else:
            normalized.update({"unknown": True})
            notes.append("Не удалось нормализовать да/нет")

    elif answer_type == "level_select":
        allowed_levels = validation.get("allowed_levels")
        value = _validate_level(raw, allowed_levels)
        if value is None and second_try is not None:
            add_followup(question.get("on_ambiguous_followup") or "Уточните уровень по CEFR (A1..C2), одним значением.")
            value = _validate_level(second_try, allowed_levels)
        if value is not None:
            normalized.update({"value": value, "valid": True})
        else:
            normalized.update({"unknown": True})
            notes.append("Некорректный уровень CEFR")

    elif answer_type in {"years_number", "salary_number"}:
        default_min = 0
        default_max = 100 if answer_type == "years_number" else 100000000
        rng = (validation.get("min"), validation.get("max"))
        value = _parse_int_in_range(raw, default_min, default_max, rng)
        if value is None and second_try is not None:
            add_followup(question.get("on_ambiguous_followup") or "Уточните число в допустимом диапазоне, одним числом.")
            value = _parse_int_in_range(second_try, default_min, default_max, rng)
        if value is not None:
            val_block: Dict[str, Any] = {"value": str(value), "valid": True, "units": units}
            if answer_type == "salary_number" and currency:
                val_block["currency"] = currency
            normalized.update(val_block)
        else:
            normalized.update({"unknown": True})
            notes.append("Число вне диапазона или не распознано")

    elif answer_type == "option_select":
        value = _match_option(options, raw)
        if value is None and second_try is not None:
            add_followup(question.get("on_ambiguous_followup") or "Выберите один из предложенных вариантов.")
            value = _match_option(options, second_try)
        if value is not None:
            normalized.update({"value": value, "valid": True})
        else:
            normalized.update({"unknown": True})
            notes.append("Ответ вне предложенных опций")

    elif answer_type == "free_text_short":
        value = _validate_free_text(raw, validation.get("pattern"))
        if value is None and second_try is not None:
            add_followup(question.get("on_ambiguous_followup") or "Пожалуйста, кратко одним предложением (до 200 символов).")
            value = _validate_free_text(second_try, validation.get("pattern"))
        if value is not None:
            normalized.update({"value": value, "valid": True})
        else:
            normalized.update({"unknown": True})
            notes.append("Свободный текст некорректен или слишком длинный")

    elif answer_type == "date_text":
        value = _validate_date_yyyy_mm(raw)
        if value is None and second_try is not None:
            add_followup(question.get("on_ambiguous_followup") or "Пожалуйста, укажите в формате YYYY-MM.")
            value = _validate_date_yyyy_mm(second_try)
        if value is not None:
            normalized.update({"value": value, "valid": True})
        else:
            normalized.update({"unknown": True})
            notes.append("Дата не в формате YYYY-MM")

    validation_notes = "; ".join(notes) if notes else ""
    return normalized, validation_notes, transcript_tail


class WidgetOrchestratorAgent(Agent):
    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        questions: List[Dict[str, Any]] = list(payload.get("questions") or [])
        closing_message: str = payload.get("closing_message") or "Спасибо за ответы! Мы передадим информацию команде и вернёмся с обратной связью."
        meta: Dict[str, Any] = dict(payload.get("meta") or {})
        context: Dict[str, Any] = dict(payload.get("context") or {})
        currency: Optional[str] = context.get("currency")

        max_questions = int(meta.get("max_questions") or 3)
        questions.sort(key=lambda q: q.get("priority", 9999))
        questions = questions[:max_questions]

        # Responses provided by the client in order of asked questions.
        # Each response can be a string or an object {"text": str}
        raw_responses_input = payload.get("responses") or []
        responses: List[str] = []
        for item in raw_responses_input:
            if isinstance(item, dict):
                responses.append(str(item.get("text") or ""))
            else:
                responses.append(str(item))

        transcript: List[Dict[str, str]] = []
        answers: List[Dict[str, Any]] = []

        # Opening greeting
        transcript.append({"role": "system", "text": _greeting(context), "ts": _now_iso()})

        stopped_by_user = False
        skipped_count = 0
        asked = 0
        answered_count = 0

        resp_idx = 0
        for q in questions:
            asked += 1
            # Ask question
            transcript.append({"role": "assistant", "text": q.get("question_text", ""), "ts": _now_iso()})

            # Fetch first user response (may be missing)
            first_raw = responses[resp_idx] if resp_idx < len(responses) else ""
            if resp_idx < len(responses):
                resp_idx += 1

            # Handle commands
            if _is_stop(first_raw):
                stopped_by_user = True
                # Record as unknown without answer
                answers.append({
                    "id": q.get("id"),
                    "criterion": q.get("criterion"),
                    "question_text": q.get("question_text"),
                    "raw_answer": first_raw,
                    "normalized": {"value": None, "units": _units_for(q.get("answer_type", "free_text_short")), "valid": False, "unknown": True, "skipped": False},
                    "validation_notes": "Диалог остановлен пользователем",
                })
                break

            transcript.append({"role": "user", "text": first_raw, "ts": _now_iso()})

            if _is_skip(first_raw):
                skipped_count += 1
                answers.append({
                    "id": q.get("id"),
                    "criterion": q.get("criterion"),
                    "question_text": q.get("question_text"),
                    "raw_answer": first_raw,
                    "normalized": {"value": None, "units": _units_for(q.get("answer_type", "free_text_short")), "valid": True, "unknown": False, "skipped": True},
                    "validation_notes": "Пользователь пропустил вопрос",
                })
                continue

            # Try second attempt only if needed
            second_raw: Optional[str] = None
            normalized, notes, tail = _validate_answer(q, first_raw, None, currency)
            if not normalized.get("valid") and not normalized.get("unknown"):
                # Ask follow-up and expect second response if available
                tail_notes = tail[:]  # includes assistant follow-up
                transcript.extend(tail_notes)
                second_raw = responses[resp_idx] if resp_idx < len(responses) else ""
                if resp_idx < len(responses):
                    resp_idx += 1
                if second_raw is not None and second_raw != "":
                    transcript.append({"role": "user", "text": second_raw, "ts": _now_iso()})
                normalized, notes, _ = _validate_answer(q, first_raw, second_raw, currency)

            if normalized.get("valid"):
                answered_count += 1

            answers.append({
                "id": q.get("id"),
                "criterion": q.get("criterion"),
                "question_text": q.get("question_text"),
                "raw_answer": first_raw if second_raw is None else second_raw or first_raw,
                "normalized": normalized,
                "validation_notes": notes,
            })

        # Closing
        closing_text = closing_message
        if stopped_by_user:
            closing_text = closing_text.rstrip() + " " + "Спасибо! Если захотите, вы можете вернуться к вопросам позже."
        transcript.append({"role": "assistant", "text": closing_text, "ts": _now_iso()})

        session = {
            "completed": not stopped_by_user,
            "stopped_by_user": stopped_by_user,
            "skipped_count": skipped_count,
            "asked": asked if not stopped_by_user else max(1, asked - 1),
            "answered": answered_count,
            "language": meta.get("language") or "ru",
        }

        for_scorer_payload = _build_scorer_payload(answers)

        return {
            "answers": answers,
            "transcript": transcript,
            "session": session,
            "for_scorer_payload": for_scorer_payload,
        }


def _build_scorer_payload(answers: List[Dict[str, Any]]) -> Dict[str, Any]:
    relocation_ready = False
    salary_flex = None
    lang_proofs: List[str] = []
    other: List[str] = []

    for a in answers:
        crit = (a.get("criterion") or "").lower()
        norm = a.get("normalized") or {}
        val = (norm.get("value") or "").strip()
        if crit in {"location", "format"}:
            t = str(val).lower()
            if "переех" in t or t in {"готов переехать", "готов к переезду"}:
                relocation_ready = True
        if crit == "compensation":
            t = str(val).lower()
            if "обсуждаемо" in t or "negotiable" in t:
                salary_flex = "negotiable"
            elif "фикс" in t or "fixed" in t:
                salary_flex = "fixed"
            elif "диапаз" in t or "range" in t:
                salary_flex = "range"
        if crit == "langs" and isinstance(val, str) and len(val) > 0:
            # If there was an additional free-text proof question, it would appear as another answer; collect generic notes
            if a.get("question_text") and "сертифик" in a.get("question_text").lower():
                lang_proofs.append(val)
        # Collect compact other clarifications from valid short texts
        if norm.get("valid") and norm.get("units") in {"text", "option", "date"}:
            other.append(f"{crit}:{val}")

    return {
        "dialogFindings": {
            "relocation_ready": relocation_ready,
            "lang_proofs": lang_proofs,
            "salary_flex": salary_flex or "",
            "other_clarifications": other[:6],
        }
    }
