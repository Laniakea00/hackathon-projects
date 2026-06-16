from typing import Any, Dict
from app.services.ai import Agent


class DialogSummarizerAgent(Agent):
    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("DialogSummarizerAgent is not implemented yet")
