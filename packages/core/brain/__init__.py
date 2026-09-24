"""Brain v1 package for OmniBrain."""
from .web_research import is_research_query, search_web_realtime, format_research_context

try:
    from .context import ContextEngine, SystemContext
except Exception:
    ContextEngine = None
    SystemContext = None

from .classifier import IntentEngine, TaskClassification
from .planner import DAGPlanner, DAGPlan, StepPlan
from .synthesizer import ResultSynthesizer, StructuredReport

__all__ = [
    "ContextEngine",
    "SystemContext",
    "IntentEngine",
    "TaskClassification",
    "DAGPlanner",
    "DAGPlan",
    "StepPlan",
    "ResultSynthesizer",
    "StructuredReport",
    "is_research_query",
    "search_web_realtime",
    "format_research_context",
]

