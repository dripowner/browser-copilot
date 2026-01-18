"""Analyzes progress toward goal."""

from langgraph.types import Command

from src.agent.state import BrowserAgentState
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def _estimate_goal_proximity(messages: list, original_task: str) -> float:
    """
    Оценивает близость к цели на основе истории сообщений.

    Использует эвристики:
    - Tool success rate (успешные tool calls / общие tool calls)
    - Глубина истории (длинная = вероятно больше прогресса)

    Args:
        messages: Message history
        original_task: Original user task

    Returns:
        Score 0.0-1.0 representing estimated proximity to goal
    """
    if not messages:
        return 0.0

    # Подсчет tool calls и результатов
    tool_calls = 0
    successful_tools = 0

    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            tool_calls += len(msg.tool_calls)
        if hasattr(msg, "name") and hasattr(msg, "content"):
            # ToolMessage
            successful_tools += 1 if "error" not in str(msg.content).lower() else 0

    # Success rate компонент (0.0-0.5)
    success_rate = (successful_tools / tool_calls * 0.5) if tool_calls > 0 else 0.0

    # History depth компонент (0.0-0.5)
    # Больше сообщений = вероятно больше работы, но cap чтобы избежать бесконечного роста
    history_depth = min(len(messages) / 40, 0.5)  # Cap at 40 messages = 50%

    return success_rate + history_depth


def create_progress_analyzer(llm):
    """
    Factory for progress analyzer.

    Args:
        llm: ChatOpenAI instance (not used currently, but available for future LLM-based analysis)

    Returns:
        Progress analysis node function
    """

    def progress_analyzer(state: BrowserAgentState) -> Command:
        """
        Analyze task progress.

        Calculates progress score (0.0-1.0) based on:
        - Steps completed vs estimated total
        - Errors encountered
        - Tool success rate

        Returns Command routing to:
        - "strategy_adapter" if stuck (low progress, high errors)
        - "quality_evaluator" if near complete (score > 0.9)
        - "agent" otherwise
        """
        logger.info("Analyzing progress")

        messages = state.get("messages", [])
        error_count = state.get("error_count", 0)
        quality_score = state.get("quality_score", None)

        # Расчет близости к цели
        goal_proximity = _estimate_goal_proximity(messages, state.get("original_task"))
        error_penalty = min(error_count * 0.1, 0.4)  # Cap at 40%
        quality_bonus = (quality_score or 0.5) * 0.2  # Up to 20% boost

        progress_score = max(0.0, min(1.0, goal_proximity - error_penalty + quality_bonus))

        logger.info(
            f"Progress: {progress_score:.2f} (goal_proximity: {goal_proximity:.2f}, errors: {error_count}, quality: {quality_score})"
        )

        # Detect if stuck
        is_stuck = error_count > 3 or state.get("stuck_counter", 0) > 2

        if is_stuck:
            logger.warning(
                f"Agent appears stuck (errors: {error_count}, stuck_counter: {state.get('stuck_counter', 0)})"
            )
            return Command(
                update={
                    "progress_score": progress_score,
                    "stuck_counter": state.get("stuck_counter", 0) + 1,
                },
                goto="strategy_adapter",
            )

        if progress_score > 0.9:
            # Near completion - evaluate quality
            logger.info("Near completion - routing to quality evaluator")
            return Command(
                update={"progress_score": progress_score}, goto="quality_evaluator"
            )

        # Continue normal flow
        return Command(
            update={"progress_score": progress_score, "stuck_counter": 0},  # Reset
            goto="agent",
        )

    return progress_analyzer
