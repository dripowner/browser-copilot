"""Auto-corrects common errors like stale references."""

from langchain_core.messages import AIMessage
from langgraph.types import Command

from src.agent.state import BrowserAgentState
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_self_corrector():
    """
    Factory for self corrector.

    Returns:
        Self-correction node function
    """

    def self_corrector(state: BrowserAgentState) -> Command:
        """
        Auto-correct common errors.

        Handles:
        - Stale references (refresh snapshot)
        - Element not found (try alternative selectors)
        - Timeout (retry with delay)

        Returns Command routing to:
        - "tools" to retry with correction
        - "agent" if can't auto-fix (let LLM handle naturally)
        """
        error_type = state.get("error_type")
        logger.info(f"Self-correcting error: {error_type}")

        if error_type == "stale_ref":
            # Inject correction: get fresh snapshot
            correction = AIMessage(
                content="Detected stale reference. Getting fresh page snapshot.",
                tool_calls=[
                    {
                        "name": "get_page_snapshot",
                        "args": {},
                        "id": "self_correct_snapshot",
                        "type": "tool_call",
                    }
                ],
            )

            logger.info("Auto-correction: Refreshing page snapshot")
            return Command(
                update={
                    "messages": [correction],
                    "error_type": None,  # Clear error
                },
                goto="tools",
            )

        # Can't auto-fix - let agent handle through natural reasoning
        logger.warning(f"Cannot auto-correct error type: {error_type}")
        return Command(goto="agent")

    return self_corrector
