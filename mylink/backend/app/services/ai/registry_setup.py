from app.services.ai import registry
from app.services.ai.agents.mismatch_agent import MismatchDetectorAgent
from app.services.ai.agents.question_generator_agent import QuestionGeneratorAgent
from app.services.ai.agents.relevance_scorer_agent import RelevanceScorerAgent
from app.services.ai.agents.dialog_summarizer_agent import DialogSummarizerAgent
from app.services.ai.agents.widget_orchestrator_agent import WidgetOrchestratorAgent


_REGISTERED = False


def register_all_agents() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    registry.register("mismatch", lambda: MismatchDetectorAgent())
    registry.register("question_generator", lambda: QuestionGeneratorAgent())
    registry.register("clarifier", lambda: QuestionGeneratorAgent())
    registry.register("orchestrator", lambda: WidgetOrchestratorAgent())
    registry.register("widget_orchestrator", lambda: WidgetOrchestratorAgent())
    registry.register("relevance_scorer", lambda: RelevanceScorerAgent())
    registry.register("scorer", lambda: RelevanceScorerAgent())
    registry.register("summarizer", lambda: RelevanceScorerAgent())
    registry.register("dialog_summarizer", lambda: DialogSummarizerAgent())
    _REGISTERED = True
