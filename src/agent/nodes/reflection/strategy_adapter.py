"""Adapts strategy when stuck."""

from langgraph.types import Command
from langchain_core.messages import AIMessage, HumanMessage

from src.agent.state import BrowserAgentState
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_strategy_adapter(llm):
    """
    Factory for strategy adapter.

    Args:
        llm: ChatOpenAI instance

    Returns:
        Strategy adaptation node function
    """

    def strategy_adapter(state: BrowserAgentState) -> Command:
        """
        Re-plan strategy when stuck.

        Uses LLM to:
        - Analyze why current approach isn't working
        - Generate alternative strategy
        - Provide new plan to agent

        Returns Command routing to "agent" with new strategy.
        """
        logger.warning("Agent stuck - adapting strategy")

        original_task = state.get("original_task")
        error_count = state.get("error_count", 0)
        messages = state["messages"]

        reflection_prompt = f"""
Task: {original_task}
Errors encountered: {error_count}
Recent history: {_get_recent_history(messages)}

Current approach is not working. Analyze why and propose alternative strategy.
Be specific about what to do differently.
"""

        response = llm.invoke([HumanMessage(content=reflection_prompt)])

        strategy_msg = AIMessage(content=f"Strategy adaptation: {response.content}")

        logger.info(f"New strategy proposed: {response.content[:200]}...")

        return Command(
            update={
                "messages": [strategy_msg],
                "strategy_changes": state.get("strategy_changes", 0) + 1,
                "stuck_counter": 0,  # Reset after adaptation
            },
            goto="agent",
        )

    return strategy_adapter


def _get_recent_history(messages, last_n=5):
    """
    Get recent message history.

    Args:
        messages: List of messages
        last_n: Number of recent messages to include

    Returns:
        List of recent message contents
    """
    return [
        msg.content[:200] if hasattr(msg, "content") else str(msg)
        for msg in messages[-last_n:]
    ]
