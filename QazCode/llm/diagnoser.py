"""DEPRECATED – LLM diagnostic client (superseded by llm.generator).

This module is kept as an inert shim so any code that still imports
``MedicalDiagnoser`` continues to work.  New code should use
``llm.generator.QazCodeHubConnector`` and ``llm.service.RAGService`` instead.
"""

import warnings

warnings.warn(
    "llm.diagnoser is deprecated.  Use llm.generator.QazCodeHubConnector "
    "and llm.service.RAGService instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export the new class under the old name for backward compatibility.
from llm.generator import QazCodeHubConnector as MedicalDiagnoser  # noqa: F401, E402

__all__ = ["MedicalDiagnoser"]
