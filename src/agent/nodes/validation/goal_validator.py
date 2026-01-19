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

        # Use LLM to analyze goal achievement with task type detection
        validation_prompt = f"""Original task: {original_task}

Execution history: {_summarize_history(messages)}

Analyze whether the task goal has been achieved.

Step 1: Determine task type
- ACTION task: requires changing state (add, create, send, delete, buy, book, etc.)
- RESEARCH task: requires gathering information (find, show, check, what is, how many, etc.)

Step 2: Evaluate evidence
- For ACTION tasks: Did the agent VERIFY the final state after performing actions?
  * Performing an action (clicking, filling) is NOT the same as achieving the goal
  * The agent must check that the state actually changed as expected
  * Example: adding to cart requires checking the cart shows the items
  
- For RESEARCH tasks: Did the agent extract and provide the requested information?
  * The actual data must be present, not just "I searched for it"

Step 3: Check data integrity (CRITICAL)
If the agent provided specific facts (names, prices, quantities, etc.) in their response:
- Are these facts present in the tool results?
- Or did the agent "fill in" missing information based on context/expectations?

DATA_INTEGRITY_ISSUE: YES if agent stated facts not found in tool results, NO otherwise

Step 4: Make decision
Return your assessment in this format:

TASK_TYPE: ACTION | RESEARCH
STATUS: ACHIEVED | PARTIALLY_ACHIEVED | NOT_ACHIEVED
EVIDENCE: [What concrete evidence from the execution history proves/disproves goal achievement?]
VERIFICATION_DONE: YES | NO [For ACTION tasks - was final state verified?]
DATA_INTEGRITY: OK | ISSUE [Are stated facts backed by tool results?]
REASONING: [Brief explanation]"""

        response = llm.invoke([HumanMessage(content=validation_prompt)])
        decision = response.content

        # Detect task type from response
        is_action_task = (
            "TASK_TYPE: ACTION" in decision or "TASK_TYPE:ACTION" in decision
        )

        # Check evidence quality based on task type
        task_type = "action" if is_action_task else "research"
        has_evidence = _check_evidence_quality(decision, task_type)

        # For action tasks, also check if verification was done
        verification_done = (
            "VERIFICATION_DONE: YES" in decision or "VERIFICATION_DONE:YES" in decision
        )

        # Check for data integrity issues
        has_data_integrity_issue = (
            "DATA_INTEGRITY: ISSUE" in decision or "DATA_INTEGRITY:ISSUE" in decision
        )

        if has_data_integrity_issue and "ACHIEVED" in decision:
            # Agent stated facts not backed by tool results
            logger.warning(
                "Data integrity issue detected - agent stated facts not found in tool results"
            )
            feedback_msg = AIMessage(
                content="Data integrity issue: your response contains specific facts not found in tool results. Re-extract the data using appropriate tools and report only verified information. Do not fill in missing information based on context."
            )
            return Command(
                update={"messages": [feedback_msg], "goal_achieved": False},
                goto="agent",
            )

        if is_action_task and "ACHIEVED" in decision and not verification_done:
            # Action task claimed complete but no verification
            logger.warning(
                "Action task claimed achieved but no state verification - requiring verification"
            )
            feedback_msg = AIMessage(
                content="Task appears to involve state changes. Before completing, verify the final state - check that the expected changes actually occurred (not just that actions were performed)."
            )
            return Command(
                update={"messages": [feedback_msg], "goal_achieved": False},
                goto="agent",
            )

        if not has_evidence and "ACHIEVED" in decision:
            # Claimed success but no evidence
            logger.warning(
                "Goal claimed achieved but no concrete evidence - requiring verification"
            )
            feedback_msg = AIMessage(
                content="Goal validation requires evidence. Verify the final state to confirm the goal was achieved."
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

        # Goal achieved - generate final message for user
        logger.info(f"Goal achieved: {decision}")

        # Generate user-friendly summary
        final_message = _generate_final_message(llm, original_task, decision)

        return Command(
            update={"messages": [final_message], "goal_achieved": True}, goto=END
        )

    return goal_validator


def _generate_final_message(llm, original_task: str, validation_decision: str) -> AIMessage:
    """
    Generate user-friendly final message summarizing task completion.

    Args:
        llm: ChatOpenAI instance
        original_task: Original user task
        validation_decision: LLM's validation analysis with EVIDENCE and REASONING

    Returns:
        AIMessage with clear summary for user
    """
    prompt = f"""Задача пользователя: {original_task}

Анализ выполнения: {validation_decision}

Сформулируй КРАТКИЙ финальный ответ для пользователя (2-4 предложения).

Формат:
1. Что было сделано (1 предложение)
2. Конкретный результат (что именно добавлено/найдено/создано, с деталями если есть)

НЕ включай:
- Технические детали (селекторы, инструменты, шаги)
- Мета-комментарии о формате ответа
- Фразы типа "Задача выполнена" без конкретики

Пиши на языке пользователя, понятно и по делу."""

    response = llm.invoke([HumanMessage(content=prompt)])
    return AIMessage(content=response.content)


def _check_evidence_quality(response: str, task_type: str) -> bool:
    """
    Check if response contains concrete evidence of goal achievement.

    This is a lightweight heuristic check. The main validation is done by LLM.

    For action tasks: requires indication that final state was verified (not just actions taken).
    For research tasks: requires indication that data was extracted.

    Args:
        response: LLM response text
        task_type: "action" or "research"

    Returns:
        True if contains evidence pattern, False otherwise
    """
    response_lower = response.lower()

    # Weak evidence: only mentions actions without state verification
    action_only_patterns = [
        "clicked",
        "filled",
        "navigated",
        "searched",
        "added to cart",  # Action, not verification
        "submitted",
        "pressed",
    ]

    # Check if response ONLY mentions actions
    mentions_actions = any(
        pattern in response_lower for pattern in action_only_patterns
    )

    # State verification indicators (universal, not site-specific)
    state_verification_patterns = [
        "verified",
        "confirmed",
        "checked",
        "shows",
        "displays",
        "contains",
        "state:",
        "result:",
        "found that",
        "observed",
        "current state",
        "final state",
    ]

    has_verification = any(
        pattern in response_lower for pattern in state_verification_patterns
    )

    # For action tasks: actions alone are NOT sufficient
    if task_type == "action" and mentions_actions and not has_verification:
        return False

    return True


def _summarize_history(messages, last_n=15):
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
            # Full content for better data integrity validation
            summary.append(f"Result: {msg.content}")
    return "\n".join(summary)
