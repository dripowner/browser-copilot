"""Tool execution node with error detection."""

import json

from langgraph.prebuilt import ToolNode
from langgraph.types import Command

from src.agent.state import BrowserAgentState
from src.utils.logger import setup_logger

logger = setup_logger(__name__, level="DEBUG")


def _detect_error_in_results(tool_messages: list) -> tuple[str, str | None]:
    """
    Detect errors in tool result messages and categorize them.

    Args:
        tool_messages: List of tool result messages

    Returns:
        (error_type, error_message) tuple
        error_type: "syntax_error", "viewport_error", "timeout", "none"
        error_message: Raw error message if error detected
    """
    if not tool_messages:
        return "none", None

    # Check ALL tool messages (not just last) for errors
    for message in tool_messages:
        if not hasattr(message, "content"):
            continue

        content = str(message.content).lower()

        # Playwright Syntax Errors (CRITICAL - must fix syntax)
        if "invalidselectorerror" in content or "unexpected symbol" in content:
            return "syntax_error", str(message.content)

        if "is not a function" in content and ("slice" in content or "filter" in content or "map" in content):
            return "syntax_error", str(message.content)

        # Viewport Errors (need strategy change)
        if "outside of the viewport" in content or "element is not visible" in content:
            return "viewport_error", str(message.content)

        # Timeout Errors - check for networkidle specific
        if "timeouterror" in content:
            if "networkidle" in content or "page.goto" in content:
                return "timeout", str(message.content)
            # Other timeouts - let agent handle
            return "timeout_other", str(message.content)

        # Stale Reference
        if "ref not found" in content or "stale" in content:
            return "stale_ref", str(message.content)

    return "none", None


def _validate_tab_creation(state: BrowserAgentState) -> tuple[bool, str]:
    """
    Проверить если browser_tabs(action="new") был вызван без последующих шагов.

    Args:
        state: Текущее состояние агента

    Returns:
        (needs_reminder, message_content) - нужно ли напоминание и его текст
    """
    # Проверить последний AIMessage с tool_calls для определения что именно было вызвано
    messages = state.get("messages", [])

    # Найти последний AIMessage с tool_calls
    last_tool_call_action = None
    for message in reversed(messages):
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tc in message.tool_calls:
                if tc.get("name") == "browser_tabs":
                    args = tc.get("args", {})
                    last_tool_call_action = args.get("action")
                    break
            if last_tool_call_action:
                break

    # Если последний вызов был browser_tabs(action="new") - нужно напоминание
    if last_tool_call_action == "new":
        reminder_msg = """КРИТИЧЕСКОЕ НАПОМИНАНИЕ: Только что создана ПУСТАЯ вкладка (about:blank).

Необходимая последовательность:

1. ✅ browser_tabs(action="new") - выполнено
2. ⚠️ browser_tabs(action="list") - получить список (новая вкладка будет ПОСЛЕДНЕЙ)
3. ⚠️ ВАЖНО: browser_tabs(select) использует 1-BASED индексацию!
   Если list показывает новую вкладку как `41: [about:blank]`, используй index=42 (+1)!
4. ⚠️ browser_tabs(action="select", index=N+1) - переключиться на новую
5. ⚠️ browser_navigate(url="https://...") - теперь навигация в правильной вкладке

ПРАВИЛО: ВСЕГДА добавляй +1 к индексу из list перед вызовом select!"""

        return True, reminder_msg

    return False, ""


def create_tools_node(tools):
    """
    Factory to create tools execution node.

    Args:
        tools: List of LangChain tools

    Returns:
        Tools node function that returns Command for routing
    """
    # Use LangGraph's ToolNode for execution with automatic error handling
    tool_executor = ToolNode(tools, handle_tool_errors=True)

    async def tools_node(state: BrowserAgentState) -> Command:
        """
        Execute tool calls from agent (async version for MCP tools).

        Returns Command with:
        - update: Tool results, error tracking
        - goto: "memory_manager"
        """
        logger.info("Tools node - executing tool calls")

        # Execute tools using ToolNode (async)
        result = await tool_executor.ainvoke(state)

        # Extract tool results
        tool_messages = result["messages"]

        # LOG TOOL RESULTS FOR DEBUGGING
        for i, msg in enumerate(tool_messages):
            if hasattr(msg, "name"):
                logger.info(f"Tool result [{i}]: {msg.name}")
                # Format content with proper Unicode (no escape sequences)
                try:
                    content = msg.content
                    if isinstance(content, str):
                        parsed = json.loads(content)
                    else:
                        parsed = content
                    content_str = json.dumps(parsed, ensure_ascii=False)
                except (json.JSONDecodeError, TypeError):
                    content_str = str(msg.content)
                logger.debug(f"Tool content [{i}]: {content_str[:500]}")
            else:
                logger.debug(f"Message [{i}] type: {type(msg).__name__}")

        # Detect errors in tool results
        error_type, error_message = _detect_error_in_results(tool_messages)

        # Route to self_corrector for auto-fixable errors
        if error_type in ["syntax_error", "viewport_error", "timeout", "stale_ref"]:
            logger.warning(f"Detected {error_type} - routing to self_corrector")
            return Command(
                update={
                    "messages": tool_messages,
                    "error_type": error_type,
                    "error_message": error_message,
                    "current_step": state.get("current_step", 0) + 1,
                },
                goto="self_corrector",
            )

        # Validate tab creation sequence
        needs_reminder, reminder_msg = _validate_tab_creation(state)
        if needs_reminder:
            from langchain_core.messages import AIMessage

            logger.warning(
                "Detected browser_tabs(create) without navigate - adding reminder"
            )
            reminder = AIMessage(content=reminder_msg)
            tool_messages = list(tool_messages) + [reminder]

        # Success - route directly to agent
        # Суммаризация отключена - routing напрямую без memory_manager
        logger.info("Tool execution successful - routing to agent")
        return Command(
            update={
                "messages": tool_messages,
                "current_step": state.get("current_step", 0) + 1,
            },
            goto="agent",
        )

    return tools_node
