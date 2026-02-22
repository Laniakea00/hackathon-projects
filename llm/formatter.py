"""Response parser and validator for LLM diagnostic output.

Guarantees that callers always receive a typed list of DiagnosisItem objects,
even when the model produces malformed JSON, wraps the array in a dict, or
embeds JSON inside a markdown code block.

``DiagnosisItem`` is defined in ``backend.schemas.diagnose`` and re-exported
here for backward compatibility with any code that imports it from this module.
"""

import json
import re

# DiagnosisItem lives in the schemas package; re-export for backward compat.
from backend.schemas.diagnose import DiagnosisItem  # noqa: F401

# Valid ICD-10 code pattern: letter + 2 digits, optional dot + 1-2 alphanums
_ICD_RE = re.compile(r"^[A-Z][0-9]{2}(\.[0-9A-Za-z]{1,2})?$")


# Returned when no diagnoses could be parsed or the retriever found nothing.
FALLBACK: list[DiagnosisItem] = [
    DiagnosisItem(
        rank=1,
        diagnosis="Диагноз не определён",
        icd10_code="Z03.9",
        explanation=(
            "По предоставленным симптомам не удалось найти соответствие "
            "в клинических протоколах. Рекомендуется очная консультация специалиста."
        ),
    )
]

# Patterns that mark JSON embedded in a markdown code fence.
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _extract_json_str(raw: str) -> str:
    """Strip markdown fences if present, otherwise return raw string."""
    m = _CODE_FENCE_RE.search(raw)
    return m.group(1).strip() if m else raw.strip()


def _items_from_data(data: object) -> list[dict]:
    """Normalise any LLM output shape into a flat list of dicts."""
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        # Try common wrapper keys in priority order
        for key in ("diagnoses", "results", "data", "output"):
            value = data.get(key)
            if isinstance(value, list):
                return value

        # The whole dict might be a single diagnosis
        if "diagnosis" in data or "icd10_code" in data:
            return [data]

    return []


def parse_llm_response(raw: str) -> list[DiagnosisItem]:
    """Parse *raw* LLM text into validated DiagnosisItem objects.

    - Returns ``FALLBACK`` on empty input or unrecoverable parse errors.
    - Returns an empty list when the LLM legitimately found no diagnoses
      (caller can decide whether to surface the fallback).
    """
    if not raw or not raw.strip():
        return FALLBACK

    try:
        data = json.loads(_extract_json_str(raw))
    except json.JSONDecodeError:
        return FALLBACK

    raw_items = _items_from_data(data)

    result: list[DiagnosisItem] = []
    for i, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            continue
        try:
            raw_code = (item.get("icd10_code") or "").strip().upper().replace(" ", "")
            # Reject dashes and anything that doesn't look like an ICD-10 code
            if not _ICD_RE.match(raw_code):
                continue
            result.append(
                DiagnosisItem(
                    rank=item.get("rank", i),
                    diagnosis=item.get("diagnosis", ""),
                    icd10_code=raw_code,
                    explanation=item.get("explanation", ""),
                )
            )
        except Exception:
            # Skip individual malformed entries, don't abort the whole list
            continue

    return result  # may be empty; caller handles that case
