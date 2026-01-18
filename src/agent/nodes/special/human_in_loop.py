"""Pause for human confirmation/clarification."""

from langgraph.types import Command, interrupt
from langchain_core.messages import HumanMessage

from src.agent.state import BrowserAgentState
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_human_in_loop():
    """
    Factory for human in loop node.

    Returns:
        Human-in-the-loop node function
    """

    def human_in_loop(state: BrowserAgentState) -> Command:
        """
        Pause execution for user input.

        Uses LangGraph interrupt() to pause and present question.
        User response is captured via CLI and graph resumes.

        Question format: "Question text (y=option1, n=option2)"
        User responds: "y" or "n"

        Returns Command routing to "agent" with user feedback.
        """
        pending_action = state.get("pending_action")
        logger.info(f"Pausing for human confirmation: {pending_action}")

        # Always use y/n options
        user_response = interrupt(
            {
                "type": "confirmation",
                "message": pending_action,
                "options": ["y", "n"],
            }
        )

        logger.info(f"User response: {user_response}")

        # Set validation_passed based on response
        validation_passed = user_response == "y"

        # Create feedback message
        if validation_passed:
            feedback = HumanMessage(
                content="User approved. You may proceed."
            )
        else:
            feedback = HumanMessage(
                content="User declined. Please adjust your approach."
            )

        return Command(
            update={
                "messages": [feedback],
                "requires_human_approval": False,
                "validation_passed": validation_passed,
            },
            goto="agent",
        )

    return human_in_loop
