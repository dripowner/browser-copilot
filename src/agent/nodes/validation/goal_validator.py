"""Validates if task goal is achieved."""

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage, HumanMessage

from src.agent.state import BrowserAgentState
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_goal_validator(llm):
    """
    Factory for goal validator.

    Args:
        llm: ChatOpenAI instance

    Returns:
        Goal validation node function
    """

    def goal_validator(state: BrowserAgentState) -> Command:
        """
        Check if original task goal is achieved.

        Returns Command routing to:
        - END if goal achieved
        - "quality_evaluator" if needs quality check
        - "agent" if goal not met (with feedback)
        """
        logger.info("Validating goal achievement")

        original_task = state.get("original_task")
        messages = state["messages"]

        # Use LLM to compare result with goal
        validation_prompt = f"""
Original task: {original_task}

Execution history: {_summarize_history(messages)}

Has the original task goal been achieved?
Return: ACHIEVED, PARTIALLY_ACHIEVED, or NOT_ACHIEVED with reasoning.
"""

        response = llm.invoke([HumanMessage(content=validation_prompt)])
        decision = response.content

        if "NOT_ACHIEVED" in decision:
            # Provide feedback and continue
            logger.warning(f"Goal not achieved: {decision}")
            feedback_msg = AIMessage(
                content=f"Goal validation: {decision}. Continuing work..."
            )
            return Command(
                update={"messages": [feedback_msg], "goal_achieved": False},
                goto="agent",
            )

        if "PARTIALLY_ACHIEVED" in decision:
            # Check quality before deciding
            logger.info(f"Goal partially achieved: {decision} - checking quality")
            return Command(update={"goal_achieved": False}, goto="quality_evaluator")

        # Goal achieved
        logger.info(f"Goal achieved: {decision}")
        return Command(update={"goal_achieved": True}, goto=END)

    return goal_validator


def _summarize_history(messages, last_n=10):
    """
    Summarize recent message history for context.

    Args:
        messages: List of messages
        last_n: Number of recent messages to include

    Returns:
        Summary string
    """
    recent = messages[-last_n:]
    summary = []
    for msg in recent:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            summary.append(f"Action: {msg.tool_calls[0]['name']}")
        elif hasattr(msg, "content"):
            summary.append(f"Result: {msg.content[:100]}...")
    return "\n".join(summary)
