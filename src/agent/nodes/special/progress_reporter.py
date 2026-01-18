"""Reports progress to user."""

from langgraph.types import Command

from src.agent.state import BrowserAgentState
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_progress_reporter():
    """
    Factory for progress reporter.

    Returns:
        Progress reporting node function
    """

    def progress_reporter(state: BrowserAgentState) -> Command:
        """
        Send progress update to user.

        Logs progress update without adding to message history.
        CLI can display these via streaming events or logs.

        Returns Command routing to "agent".
        """
        message_count = len(state.get("messages", []))
        progress_score = state.get("progress_score", 0.0)
        error_count = state.get("error_count", 0)

        # Генерация семантического описания прогресса
        if progress_score >= 0.9:
            status = "Near completion"
        elif progress_score >= 0.6:
            status = "Making good progress"
        elif progress_score >= 0.3:
            status = "Working on task"
        else:
            status = "Starting out"

        progress_text = f"{status} - {int(progress_score * 100)}% ({message_count} exchanges, {error_count} errors)"
        logger.info(f"Progress report - {progress_text}")

        # Don't add to messages - progress is UI-only, not needed for LLM reasoning
        return Command(
            update={"message_count_at_last_check": message_count},
            goto="agent",
        )

    return progress_reporter
