"""Product Manager Agent: transforms user input into structured PRD."""

from codeforge.agents.product_manager.agent import ProductManagerAgent
from codeforge.agents.product_manager.clarification import ClarificationEngine, ClarificationSet
from codeforge.agents.product_manager.intent_parser import IntentParser, ParsedIntent
from codeforge.agents.product_manager.prd_generator import PRDGenerator

__all__ = [
    "ClarificationEngine",
    "ClarificationSet",
    "IntentParser",
    "PRDGenerator",
    "ParsedIntent",
    "ProductManagerAgent",
]
