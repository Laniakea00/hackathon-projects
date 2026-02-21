"""Pydantic v2 schemas for the /diagnose endpoint.

DiagnosisItem is the canonical type shared by the formatter, service, and API
layers.  Keeping it here (rather than in llm/formatter.py) avoids the LLM
package depending on the backend package.
"""

from typing import Optional

from pydantic import BaseModel, field_validator


class DiagnoseRequest(BaseModel):
    symptoms: Optional[str] = ""


class DiagnosisItem(BaseModel):
    """A single diagnosis entry – mirrors the mock server's contract."""

    rank: int
    diagnosis: str
    icd10_code: str
    explanation: str

    @field_validator("rank", mode="before")
    @classmethod
    def _coerce_rank(cls, v: object) -> int:
        try:
            return int(v)
        except (TypeError, ValueError):
            return 1

    @field_validator("diagnosis", "icd10_code", "explanation", mode="before")
    @classmethod
    def _coerce_str(cls, v: object) -> str:
        return str(v) if v is not None else ""


class DiagnoseResponse(BaseModel):
    diagnoses: list[DiagnosisItem]
