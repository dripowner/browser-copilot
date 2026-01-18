"""Core reasoning node - LLM decides next action."""

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command

from src.agent.prompts import (
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_MINIMAL,
)
from src.agent.state import BrowserAgentState
from src.utils.logger import setup_logger

logger = setup_logger(__name__, level="DEBUG")


def create_agent_node(llm, tools):
    """
    Factory to create agent node with LLM and tools.

    Args:
        llm: ChatOpenAI instance
        tools: List of LangChain tools

    Returns:
        Agent node function that returns Command for routing
    """
    # Disable parallel tool calls to prevent race conditions
    # Example: select_page(31) + take_snapshot() would execute concurrently
    # causing snapshot from wrong tab. Sequential execution ensures correctness.
    llm_with_tools = llm.bind_tools(tools, parallel_tool_calls=False)

    def agent_node(state: BrowserAgentState) -> Command:
        """
        Core reasoning node.

        Analyzes state, generates reasoning, decides next action.

        Returns Command with:
        - update: New messages and state updates
        - goto: Next node ("tools", "critical_action_validator", "memory_manager", "goal_validator", or END)
        """
        logger.info(f"Agent node - Messages: {len(state['messages'])}")

        messages = state["messages"]

        # Adaptive prompt selection based on message count
        current_step = state.get("current_step", 0)

        if current_step > 25:
            # After 25+ steps - minimal prompt to save tokens
            prompt = SYSTEM_PROMPT_MINIMAL
            logger.info("Using minimal prompt to save tokens (25+ steps)")
        else:
            # Standard full prompt (includes ERROR_RECOVERY_GUIDE)
            prompt = SYSTEM_PROMPT
            logger.debug("Using standard prompt with error recovery patterns")

        # Add system prompt if not present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=prompt)] + list(messages)

        # Tab intent analysis removed - let agent decide based on available tabs
        # Agent will check browser_tabs first and use existing tabs when appropriate

        # Generate LLM response
        response = llm_with_tools.invoke(messages)

        # Detect if this is a critical action
        is_critical = _detect_critical_action(response)

        # Check if task is complete (no tool calls)
        has_tool_calls = hasattr(response, "tool_calls") and response.tool_calls

        if not has_tool_calls:
            # Task appears complete - validate before finishing
            logger.info("No tool calls - routing to goal_validator")
            return Command(
                update={"messages": [response]},
                goto="goal_validator",
            )

        # Route based on action criticality
        if is_critical and not state.get("validation_passed", False):
            logger.warning(
                f"Critical action detected: {response.tool_calls[0]['name']} - routing to validator"
            )
            return Command(
                update={
                    "messages": [response],
                    "needs_validation": True,
                    "pending_action": response.tool_calls[0]["name"],
                },
                goto="critical_action_validator",
            )

        # Normal flow - execute tools
        tool_names = [tc['name'] for tc in response.tool_calls]
        logger.info(f"Executing {len(response.tool_calls)} tool(s): {tool_names}")

        # DEBUG: Log tool call arguments
        for tc in response.tool_calls:
            logger.debug(f"Tool call: {tc['name']}({tc.get('args', {})})")
        return Command(
            update={
                "messages": [response],
                "validation_passed": False,  # Reset for next action
            },
            goto="tools",
        )

    return agent_node


def _detect_critical_action(message) -> bool:
    """
    Detect if message contains critical/irreversible actions.

    Args:
        message: AI message with potential tool calls

    Returns:
        True if message contains critical action
    """
    if not hasattr(message, "tool_calls") or not message.tool_calls:
        return False

    # Define critical tool names
    critical_tools = {
        "delete_element",
        "submit_form",
        "confirm_payment",
        "delete_message",
        "remove_item",
        "cancel_order",
    }

    for tool_call in message.tool_calls:
        if tool_call.get("name") in critical_tools:
            return True

    return False


def _analyze_tab_intent(task: str, llm) -> dict:
    """
    Analyze user task for tab usage intent.

    Args:
        task: User's original task
        llm: ChatOpenAI instance

    Returns:
        Dict with mode ("create_new" or "use_existing") and reasoning
    """
    prompt = f"""Проанализируй задачу и определи намерение по использованию вкладок.

Задача: "{task}"

Ответь JSON (без markdown):
{{
    "mode": "create_new" или "use_existing",
    "reasoning": "обоснование"
}}

ПРАВИЛА:
1. Нет явного указания → "create_new"
2. Есть "используй вкладку", "в текущей", "в открытой" → "use_existing"
3. Сомнения → "create_new"

ПРИМЕРЫ:
"Открой hh.ru" → {{"mode": "create_new", "reasoning": "Нет явного указания"}}
"Используй открытую вкладку с hh.ru" → {{"mode": "use_existing", "reasoning": "Явное указание"}}
"В текущей вкладке найди" → {{"mode": "use_existing", "reasoning": "Указано 'в текущей'"}}
"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()

        # Remove markdown code blocks
        json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        elif content.startswith("```"):
            content = content[3:-3].strip()

        result = json.loads(content)

        if result.get("mode") not in ["create_new", "use_existing"]:
            raise ValueError("Invalid mode")

        return result

    except Exception as e:
        logger.warning(f"Tab intent parse failed: {e}. Using safe default.")
        return {"mode": "create_new", "reasoning": "Parse error, safe default"}
