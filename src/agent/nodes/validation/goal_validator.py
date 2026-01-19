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

        # Use LLM to compare result with goal (with evidence requirement)
        validation_prompt = f"""
Original task: {original_task}

Execution history: {_summarize_history(messages)}

Has the original task goal been achieved?

IMPORTANT: Provide EVIDENCE-BASED assessment.

For research tasks (information gathering):
- Evidence = the data you extracted from the browser
- Example: "Found price: $99, rating: 4.5 stars"

For action tasks (state changes):
- Evidence = verification of state change
- Example: "Verified cart shows 3 items, total $150"
- NOT acceptable: "I clicked add button" (action ≠ goal)

Return format:
Status: ACHIEVED / PARTIALLY_ACHIEVED / NOT_ACHIEVED
Evidence: [concrete facts from browser state]
Reasoning: [why this evidence proves/disproves goal achievement]
"""

        response = llm.invoke([HumanMessage(content=validation_prompt)])
        decision = response.content

        # Check if response contains evidence (not just reasoning)
        has_evidence = _check_evidence_quality(decision)
        if not has_evidence and "ACHIEVED" in decision:
            # Claimed success but no evidence - require verification
            logger.warning("Goal claimed achieved but no concrete evidence - requiring verification")
            feedback_msg = AIMessage(
                content="Goal validation requires evidence. For action tasks, verify the final state (check what changed). For research tasks, confirm you extracted the needed data."
            )
            return Command(
                update={"messages": [feedback_msg], "goal_achieved": False},
                goto="agent",
            )

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


def _check_evidence_quality(response: str) -> bool:
    """
    Check if response contains concrete evidence vs just reasoning.

    Evidence indicators:
    - Specific values (numbers, URLs, text excerpts)
    - Verification keywords (verified, checked, shows, contains)
    - State descriptions (count = X, total = Y, status = Z)

    Args:
        response: LLM response text

    Returns:
        True if contains evidence, False if only reasoning
    """
    response_lower = response.lower()

    # Evidence keywords - indicates actual browser state check
    evidence_keywords = [
        "verified",
        "checked",
        "shows",
        "contains",
        "count =",
        "total =",
        "found:",
        "extracted:",
        "current state",
        "state shows",
    ]

    # Check for evidence keywords
    has_keywords = any(keyword in response_lower for keyword in evidence_keywords)

    # Check for numbers (often indicate concrete data)
    import re

    has_numbers = bool(re.search(r"\d+", response))

    # Weak evidence: only mentions actions without verification
    weak_patterns = ["clicked", "filled", "navigated", "searched"]
    only_actions = (
        any(pattern in response_lower for pattern in weak_patterns)
        and not has_keywords
    )

    if only_actions:
        return False

    # Good evidence: keywords + numbers, or just strong keywords
    return has_keywords or has_numbers


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
