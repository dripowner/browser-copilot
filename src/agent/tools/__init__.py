"""Browser tools package.

This package provides high-level browser automation tools that wrap
the browser_run_code MCP tool with predefined Playwright code.

Usage:
    from src.agent.tools import get_browser_tools
    from src.agent.tools._executor import BrowserExecutor

    # Initialize executor with MCP tool (in main.py)
    BrowserExecutor.initialize(browser_run_code_mcp_tool)

    # Get all browser tools
    tools = get_browser_tools()
"""

from src.agent.tools._executor import BrowserExecutor
from src.agent.tools.exploration import browser_explore_page, browser_inspect_container
from src.agent.tools.extraction import (
    browser_get_attribute,
    browser_get_page_info,
    browser_get_text,
)
from src.agent.tools.fallback import browser_run_custom
from src.agent.tools.interaction import (
    browser_check,
    browser_click,
    browser_fill,
    browser_hover,
    browser_press_key,
    browser_select,
)
from src.agent.tools.navigation import browser_navigate
from src.agent.tools.special import (
    browser_close_modal,
    browser_go_back,
    browser_reload,
    browser_scroll,
)
from src.agent.tools.tabs import (
    browser_close_tab,
    browser_list_tabs,
    browser_new_tab,
    browser_switch_tab,
)
from src.agent.tools.user_confirmation import request_user_confirmation
from src.agent.tools.waiting import browser_wait_for, browser_wait_for_load

__all__ = [
    # Executor
    "BrowserExecutor",
    # Exploration
    "browser_explore_page",
    "browser_inspect_container",
    # Navigation
    "browser_navigate",
    # Tabs
    "browser_list_tabs",
    "browser_switch_tab",
    "browser_new_tab",
    "browser_close_tab",
    # Interaction
    "browser_click",
    "browser_fill",
    "browser_press_key",
    "browser_select",
    "browser_hover",
    "browser_check",
    # Extraction
    "browser_get_text",
    "browser_get_attribute",
    "browser_get_page_info",
    # Waiting
    "browser_wait_for",
    "browser_wait_for_load",
    # Special
    "browser_close_modal",
    "browser_scroll",
    "browser_go_back",
    "browser_reload",
    # Fallback
    "browser_run_custom",
    # HITL
    "request_user_confirmation",
    # Factory
    "get_browser_tools",
]


def get_browser_tools() -> list:
    """
    Get all browser tools for LLM.

    Returns:
        List of all browser tools (excluding HITL tool which should be
        added separately).

    Note:
        BrowserExecutor must be initialized before calling this function.
        Call BrowserExecutor.initialize(mcp_tool) first in main.py.
    """
    if not BrowserExecutor.is_initialized():
        raise RuntimeError(
            "BrowserExecutor not initialized. "
            "Call BrowserExecutor.initialize(browser_run_code_tool) first."
        )

    return [
        # Exploration (USE FIRST on new pages!)
        browser_explore_page,
        # browser_inspect_container,  # Временно отключен - влияет на reasoning LLM
        # Navigation
        browser_navigate,
        # Tabs
        browser_list_tabs,
        browser_switch_tab,
        browser_new_tab,
        browser_close_tab,
        # Interaction
        browser_click,
        browser_fill,
        browser_press_key,
        browser_select,
        browser_hover,
        browser_check,
        # Extraction
        browser_get_text,
        browser_get_attribute,
        browser_get_page_info,
        # Waiting
        browser_wait_for,
        browser_wait_for_load,
        # Special
        browser_close_modal,
        browser_scroll,
        browser_go_back,
        browser_reload,
        # Fallback
        browser_run_custom,
    ]
