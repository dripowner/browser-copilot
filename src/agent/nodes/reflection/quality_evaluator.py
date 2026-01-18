"""Evaluates quality of final result."""

from langgraph.types import Command
from langchain_core.messages import AIMessage, HumanMessage

from src.agent.state import BrowserAgentState
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_quality_evaluator(llm):
    """
    Factory for quality evaluator.

    Args:
        llm: ChatOpenAI instance

    Returns:
        Quality evaluation node function
    """

    def quality_evaluator(state: BrowserAgentState) -> Command:
        """
        Critically evaluate result quality.

        Checks:
        - Completeness
        - Accuracy
        - Edge cases handled

        Returns Command routing to:
        - "goal_validator" if quality good
        - "agent" if needs improvement (with feedback)
        """
        logger.info("Evaluating result quality")

        original_task = state.get("original_task")
        messages = state["messages"]

        quality_prompt = f"""
Task: {original_task}
Result: {_extract_result(messages)}

Evaluate quality:
1. Is result complete?
2. Is it accurate?
3. Are edge cases handled?

Return: GOOD, ACCEPTABLE, or NEEDS_IMPROVEMENT with specific feedback.
"""

        response = llm.invoke([HumanMessage(content=quality_prompt)])
        decision = response.content

        # Parse quality score
        if "GOOD" in decision:
            quality_score = 1.0
        elif "ACCEPTABLE" in decision:
            quality_score = 0.7
        else:
            quality_score = 0.5

        logger.info(f"Quality score: {quality_score} - {decision[:100]}...")

        if quality_score < 0.7:
            # Provide improvement feedback
            feedback = AIMessage(content=f"Quality evaluation: {decision}")
            return Command(
                update={"messages": [feedback], "quality_score": quality_score},
                goto="agent",
            )

        # Quality acceptable
        logger.info("Quality acceptable - proceeding to goal validation")
        return Command(update={"quality_score": quality_score}, goto="goal_validator")

    return quality_evaluator


def _extract_result(messages):
    """
    Extract final result from messages.

    Args:
        messages: List of messages

    Returns:
        Result string
    """
    for msg in reversed(messages):
        if hasattr(msg, "content") and len(msg.content) > 50:
            return msg.content[:500]
    return "No clear result found"
