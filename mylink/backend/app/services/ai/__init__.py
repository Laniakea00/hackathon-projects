from typing import Any, Dict, Protocol, runtime_checkable, Callable


@runtime_checkable
class Agent(Protocol):
    """Protocol for AI agents returning structured dict output.

    Input and output are plain dictionaries to decouple API from specific models.
    Implementations should validate inputs and raise ValueError on invalid payloads.
    """

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        ...


class LazyAgent:
    """Wraps a factory for lazy initialization on first use."""

    def __init__(self, factory: Callable[[], Agent]) -> None:
        self._factory = factory
        self._instance: Agent | None = None

    def _ensure(self) -> Agent:
        if self._instance is None:
            self._instance = self._factory()
        return self._instance

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._ensure().run(payload)


class AgentRegistry:
    """Simple registry to manage AI agents by id.

    This allows dynamic agent selection via API without coupling to specific classes.
    """

    def __init__(self) -> None:
        self._agents: Dict[str, Agent] = {}

    def register(self, agent_id: str, factory: Callable[[], Agent]) -> None:
        if not agent_id or not isinstance(agent_id, str):
            raise ValueError("agent_id must be a non-empty string")
        # Lazy factory provides late binding and avoids heavy initialization at import time
        self._agents[agent_id] = LazyAgent(factory)

    def get(self, agent_id: str) -> Agent:
        try:
            return self._agents[agent_id]
        except KeyError as exc:
            raise KeyError(f"Unknown agent_id: {agent_id}") from exc

    def list_ids(self) -> list[str]:
        return list(self._agents.keys())


# Global registry for application
registry = AgentRegistry()

__all__ = [
    "Agent",
    "LazyAgent",
    "AgentRegistry",
    "registry",
]
