"""Tool execution node with error detection."""

from langgraph.prebuilt import ToolNode
from langgraph.types import Command

from src.agent.state import BrowserAgentState
from src.utils.logger import setup_logger

logger = setup_logger(__name__, level="DEBUG")


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
        - goto: "memory_manager", "progress_analyzer", or "progress_reporter"
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
                logger.debug(f"Tool content [{i}]: {msg.content[:500] if len(str(msg.content)) > 500 else msg.content}")
            else:
                logger.debug(f"Message [{i}] type: {type(msg).__name__}")

        # Validate tab creation sequence
        needs_reminder, reminder_msg = _validate_tab_creation(state)
        if needs_reminder:
            from langchain_core.messages import AIMessage

            logger.warning(
                "Detected browser_tabs(create) without navigate - adding reminder"
            )
            reminder = AIMessage(content=reminder_msg)
            tool_messages = list(tool_messages) + [reminder]

        # Success - route based on message count instead of steps
        message_count = len(state.get("messages", []))
        last_check = state.get("message_count_at_last_check", 0)

        # Глубокий анализ каждые 20 сообщений (complex tasks)
        if message_count - last_check >= 20:
            logger.info(f"Progress analysis at {message_count} messages")
            return Command(
                update={
                    "messages": tool_messages,
                    "message_count_at_last_check": message_count,
                },
                goto="progress_analyzer",
            )

        # Частые отчеты каждые 6 сообщений
        if message_count - last_check >= 6:
            logger.info(f"Progress report at {message_count} messages")
            return Command(
                update={
                    "messages": tool_messages,
                    "message_count_at_last_check": message_count,
                },
                goto="progress_reporter",
            )

        # Normal flow - through memory_manager to agent
        # Memory manager will check if summarization is needed and decide automatically
        logger.info("Tool execution successful - routing through memory_manager")
        return Command(
            update={
                "messages": tool_messages,
            },
            goto="memory_manager",
        )

    return tools_node
