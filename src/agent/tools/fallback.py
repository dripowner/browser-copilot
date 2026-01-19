"""Fallback browser tool for custom Playwright code."""

from langchain_core.tools import tool

from src.agent.tools._executor import BrowserExecutor
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def _wrap_with_target_page(user_code: str) -> str:
    """
    Wrap user's custom code to automatically use the correct target page.

    This ensures that even if MCP's internal page points to a different tab,
    the user's code will operate on the correct target page.

    Args:
        user_code: User's async (page) => { ... } code

    Returns:
        Wrapped code that finds target page and passes it to user's function
    """
    page_finder = BrowserExecutor.get_page_finder_code()

    # Wrap user code: find target page, then call user function with it
    return f"""async (page) => {{
  try {{
    {page_finder}

    // User's function - will receive targetPage as 'page' parameter
    const userFn = {user_code};
    return await userFn(targetPage);
  }} catch (error) {{
    return JSON.stringify({{
      success: false,
      error: error.message,
      errorType: error.name
    }});
  }}
}}"""


@tool
async def browser_run_custom(code: str, description: str) -> str:
    """
    Execute custom Playwright JavaScript code for edge-cases.

    USE ONLY when standard browser_* tools don't cover the scenario.

    Examples of when to use this tool:
    - Complex iframe handling
    - Drag-and-drop operations
    - File upload interactions
    - Custom keyboard combinations
    - Complex multi-step interactions that require page.evaluate()
    - Interacting with canvas elements
    - WebGL or SVG manipulations

    DO NOT use for standard operations - prefer:
    - browser_click for clicking
    - browser_fill for typing
    - browser_get_text for extracting text
    - browser_navigate for navigation
    - etc.

    Args:
        code: Playwright JavaScript code in format:
              async (page) => {
                // Your code here
                return result;
              }
        description: Human-readable description of what this code does.
                     Used for logging and debugging.

    Returns:
        Result of code execution (string or JSON stringified result)

    Note:
        The code receives `page` as Playwright Page object with full API.
        Always return a result (use JSON.stringify for objects).
        Wrap code in try-catch for error handling.

        MULTI-TAB: Your code automatically receives the correct target page.
        The `page` parameter will point to the page matching the current
        target URL pattern (set by browser_navigate), not MCP's internal tab.
    """
    logger.info(f"Executing custom Playwright code: {description}")

    # Wrap user code to automatically use target page
    wrapped_code = _wrap_with_target_page(code)

    result = await BrowserExecutor.execute(wrapped_code)

    logger.debug(f"Custom code result: {str(result)[:200]}...")

    return result
