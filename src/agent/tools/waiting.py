"""Waiting browser tools.

All tools support multi-tab operation through BrowserExecutor's target page
tracking. After browser_navigate or browser_switch_tab, all subsequent
operations will automatically target the correct page.
"""

import json
from typing import Literal

from langchain_core.tools import tool

from src.agent.tools._executor import BrowserExecutor
from src.agent.tools._selectors import target_to_locator_js
from src.agent.tools._templates import build_async_function


@tool
async def browser_wait_for(
    target: str,
    state: Literal["visible", "hidden", "attached", "detached"] = "visible",
    timeout: int = 10000,
) -> str:
    """
    Wait for an element to reach a specific state.

    Useful for waiting for dynamic content to load or disappear.
    Automatically operates on the current target tab.

    Target formats:
    - CSS: ".loading-spinner", "#content"
    - Role: "button:Submit"
    - Text: "text:Loading..."

    Args:
        target: Element selector to wait for
        state: State to wait for:
               - "visible" (default): Element is visible on page
               - "hidden": Element is not visible (or doesn't exist)
               - "attached": Element exists in DOM
               - "detached": Element removed from DOM
        timeout: Maximum time to wait in milliseconds (default: 10000)

    Returns:
        JSON string with:
        - success: bool
        - waited_for: str (the state we waited for)
        - found: bool (whether element was found in expected state)
        - error: str (only if success=false, typically timeout)
    """
    locator_js = target_to_locator_js(target, page_var="targetPage")
    escaped_state = state.replace("'", "\\'")

    code_body = f"""
    const locator = {locator_js};
    const targetState = '{escaped_state}';
    const timeoutMs = {timeout};

    await locator.waitFor({{
      state: targetState,
      timeout: timeoutMs
    }});

    return JSON.stringify({{
      success: true,
      waited_for: targetState,
      found: true
    }});
"""

    code = build_async_function(code_body, use_target_page=True)
    result = await BrowserExecutor.execute(code)

    try:
        parsed = json.loads(result)
        return json.dumps(parsed, ensure_ascii=False)
    except json.JSONDecodeError:
        return json.dumps(
            {"success": False, "error": f"Invalid response: {result}"},
            ensure_ascii=False,
        )


@tool
async def browser_wait_for_load(
    state: Literal["load", "domcontentloaded", "networkidle"] = "domcontentloaded",
    timeout: int = 15000,
) -> str:
    """
    Wait for page to reach a specific load state.

    Useful after navigation or triggering content loads.
    Automatically operates on the current target tab.

    Args:
        state: Load state to wait for:
               - "domcontentloaded" (default): DOM is ready (fast, good for SPA)
               - "load": Page fully loaded including resources
               - "networkidle": No network requests for 500ms (slow, avoid for SPA)
        timeout: Maximum time to wait in milliseconds (default: 15000)

    Returns:
        JSON string with:
        - success: bool
        - state: str (the state we waited for)
        - error: str (only if success=false)

    Note:
        For SPA applications, prefer "domcontentloaded" as "networkidle" may
        never be reached due to background requests.
    """
    escaped_state = state.replace("'", "\\'")

    code_body = f"""
    const targetState = '{escaped_state}';
    const timeoutMs = {timeout};

    await targetPage.waitForLoadState(targetState, {{ timeout: timeoutMs }});

    return JSON.stringify({{
      success: true,
      state: targetState
    }});
"""

    code = build_async_function(code_body, use_target_page=True)
    result = await BrowserExecutor.execute(code)

    try:
        parsed = json.loads(result)
        return json.dumps(parsed, ensure_ascii=False)
    except json.JSONDecodeError:
        return json.dumps(
            {"success": False, "error": f"Invalid response: {result}"},
            ensure_ascii=False,
        )
