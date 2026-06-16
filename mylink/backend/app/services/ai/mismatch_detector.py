from typing import Any, Dict
from app.services.ai.agents.mismatch_agent import MismatchDetectorAgent


def run_mismatch_detector(payload: Dict[str, Any]) -> Dict[str, Any]:
    agent = MismatchDetectorAgent()
    return agent.run(payload)
