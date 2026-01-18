"""Validates critical/irreversible actions before execution."""

from langgraph.types import Command
from langchain_core.messages import HumanMessage

from src.agent.state import BrowserAgentState
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_critical_action_validator(llm):
    """
    Factory for critical action validator.

    Args:
        llm: ChatOpenAI instance

    Returns:
        Validation node function
    """

    def critical_action_validator(state: BrowserAgentState) -> Command:
        """
        Validate critical action before execution.

        Analyzes:
        - Is action reversible?
        - Does it match user intent?
        - Are there safer alternatives?

        Returns Command routing to:
        - "human_in_loop" if uncertain or high risk
        - "tools" if validated successfully
        """
        logger.info(f"Validating critical action: {state.get('pending_action')}")

        action = state.get("pending_action")
        original_task = state.get("original_task")

        # Use LLM to analyze action safety
        validation_prompt = f"""
Task: {original_task}
Pending action: {action}

Analyze:
1. Is this action reversible?
2. Does it clearly match user intent?
3. What are potential risks?

Return APPROVE or NEEDS_CONFIRMATION with reasoning.
"""

        response = llm.invoke([HumanMessage(content=validation_prompt)])
        decision = response.content

        if "NEEDS_CONFIRMATION" in decision or "uncertain" in decision.lower():
            logger.warning(f"Action requires confirmation: {decision}")

            # Format action for HITL with y/n options
            formatted_action = f"{action} (y=proceed, n=cancel)"

            return Command(
                update={
                    "requires_human_approval": True,
                    "validation_passed": False,
                    "pending_action": formatted_action,
                },
                goto="human_in_loop",
            )

        # Action validated
        logger.info(f"Action approved: {decision}")
        return Command(
            update={"validation_passed": True, "requires_human_approval": False},
            goto="tools",
        )

    return critical_action_validator
