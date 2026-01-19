"""Tab management browser tools using browser_run_code.

Uses page.context().pages() to access all open pages and manage tabs.
This approach works correctly with CDP connection since it doesn't rely
on MCP's internal _currentTab tracking.
"""

import json
from typing import Optional

from langchain_core.tools import tool

from src.agent.tools._executor import BrowserExecutor
from src.agent.tools._templates import build_async_function


@tool
async def browser_list_tabs() -> str:
    """
    List all open browser tabs.

    Returns information about all tabs in the browser context.
    Tab indices are 0-based.

    Returns:
        JSON string with:
        - success: bool
        - tabs: list of {index: int, url: str, title: str}
        - current_target: str or null (current target URL pattern)
        - error: str (only if success=false)
    """
    code_body = """
    const pages = page.context().pages();
    const tabs = [];

    for (let i = 0; i < pages.length; i++) {
        const p = pages[i];
        tabs.push({
            index: i,
            url: p.url(),
            title: await p.title()
        });
    }

    return JSON.stringify({
        success: true,
        tabs: tabs,
        count: tabs.length
    });
"""

    code = build_async_function(code_body)

    try:
        result = await BrowserExecutor.execute(code)

        # Add current target info
        try:
            parsed = json.loads(result)
            parsed["current_target"] = BrowserExecutor.get_target_page()
            return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            return result

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)


@tool
async def browser_switch_tab(
    index: Optional[int] = None, domain: Optional[str] = None
) -> str:
    """
    Switch to another browser tab for subsequent operations.

    Can switch by tab index (0-based) or by domain name.
    If both are provided, index takes priority.

    IMPORTANT: This sets the target page URL pattern that ALL subsequent
    browser operations will use. Call browser_list_tabs() first to see
    available tabs.

    Args:
        index: Tab index to switch to (0-based). Optional.
        domain: Domain to find and switch to (e.g., 'google.com'). Optional.

    Returns:
        JSON string with:
        - success: bool
        - tab_index: int (switched to)
        - url: str
        - title: str
        - error: str (only if success=false)

    Note:
        At least one of index or domain must be provided.
    """
    if index is None and domain is None:
        return json.dumps({
            "success": False,
            "error": "Either index or domain must be provided",
        }, ensure_ascii=False)

    # Build code based on selection method
    if index is not None:
        # Switch by index
        code_body = f"""
    const pages = page.context().pages();
    const targetIndex = {index};

    if (targetIndex < 0 || targetIndex >= pages.length) {{
        return JSON.stringify({{
            success: false,
            error: `Tab index ${{targetIndex}} out of range. Available: 0-${{pages.length - 1}}`
        }});
    }}

    const targetPage = pages[targetIndex];
    await targetPage.bringToFront();

    return JSON.stringify({{
        success: true,
        tab_index: targetIndex,
        url: targetPage.url(),
        title: await targetPage.title()
    }});
"""
    else:
        # Switch by domain
        escaped_domain = domain.replace("'", "\\'").lower()
        code_body = f"""
    const pages = page.context().pages();
    const domain = '{escaped_domain}';

    let targetIndex = -1;
    for (let i = 0; i < pages.length; i++) {{
        if (pages[i].url().toLowerCase().includes(domain)) {{
            targetIndex = i;
            break;
        }}
    }}

    if (targetIndex === -1) {{
        const available = pages.map((p, i) => `${{i}}: ${{p.url()}}`).join(', ');
        return JSON.stringify({{
            success: false,
            error: `No tab found with domain '${{domain}}'. Available tabs: [${{available}}]`
        }});
    }}

    const targetPage = pages[targetIndex];
    await targetPage.bringToFront();

    return JSON.stringify({{
        success: true,
        tab_index: targetIndex,
        url: targetPage.url(),
        title: await targetPage.title()
    }});
"""

    code = build_async_function(code_body)

    try:
        result = await BrowserExecutor.execute(code)

        # Update target page URL if successful
        try:
            parsed = json.loads(result)
            if parsed.get("success") and parsed.get("url"):
                # Extract domain from URL for targeting
                url = parsed["url"]
                # Set target to domain part of URL
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                if parsed_url.netloc:
                    BrowserExecutor.set_target_page(parsed_url.netloc)
            return result
        except json.JSONDecodeError:
            return result

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)


@tool
async def browser_new_tab(url: Optional[str] = None) -> str:
    """
    Create a new browser tab.

    Optionally navigates to a URL immediately. The new tab becomes
    the target for all subsequent browser operations.

    Args:
        url: Optional URL to navigate to. If not provided, creates blank tab.

    Returns:
        JSON string with:
        - success: bool
        - tab_index: int (index of new tab)
        - url: str
        - title: str
        - error: str (only if success=false)
    """
    if url:
        escaped_url = url.replace("'", "\\'")
        code_body = f"""
    const newPage = await page.context().newPage();
    await newPage.goto('{escaped_url}', {{
        waitUntil: 'domcontentloaded',
        timeout: 15000
    }});

    const pages = page.context().pages();
    const newIndex = pages.indexOf(newPage);

    return JSON.stringify({{
        success: true,
        tab_index: newIndex,
        url: newPage.url(),
        title: await newPage.title()
    }});
"""
    else:
        code_body = """
    const newPage = await page.context().newPage();

    const pages = page.context().pages();
    const newIndex = pages.indexOf(newPage);

    return JSON.stringify({
        success: true,
        tab_index: newIndex,
        url: newPage.url(),
        title: await newPage.title()
    });
"""

    code = build_async_function(code_body)

    try:
        result = await BrowserExecutor.execute(code)

        # Update target page URL if successful
        try:
            parsed = json.loads(result)
            if parsed.get("success") and parsed.get("url"):
                url_result = parsed["url"]
                if url_result and url_result != "about:blank":
                    from urllib.parse import urlparse
                    parsed_url = urlparse(url_result)
                    if parsed_url.netloc:
                        BrowserExecutor.set_target_page(parsed_url.netloc)
            return result
        except json.JSONDecodeError:
            return result

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)


@tool
async def browser_close_tab(index: Optional[int] = None) -> str:
    """
    Close a browser tab.

    Args:
        index: Tab index to close (0-based). If not provided, closes
               the current target tab (or last tab if no target set).

    Returns:
        JSON string with:
        - success: bool
        - closed_index: int
        - remaining_count: int
        - error: str (only if success=false)
    """
    if index is not None:
        code_body = f"""
    const pages = page.context().pages();
    const targetIndex = {index};

    if (targetIndex < 0 || targetIndex >= pages.length) {{
        return JSON.stringify({{
            success: false,
            error: `Tab index ${{targetIndex}} out of range. Available: 0-${{pages.length - 1}}`
        }});
    }}

    if (pages.length <= 1) {{
        return JSON.stringify({{
            success: false,
            error: 'Cannot close the last tab'
        }});
    }}

    await pages[targetIndex].close();

    return JSON.stringify({{
        success: true,
        closed_index: targetIndex,
        remaining_count: pages.length - 1
    }});
"""
    else:
        # Close current target or last tab
        target_url = BrowserExecutor.get_target_page()
        if target_url:
            escaped_url = target_url.replace("'", "\\'").lower()
            code_body = f"""
    const pages = page.context().pages();

    if (pages.length <= 1) {{
        return JSON.stringify({{
            success: false,
            error: 'Cannot close the last tab'
        }});
    }}

    const targetUrl = '{escaped_url}';
    let targetIndex = -1;
    for (let i = 0; i < pages.length; i++) {{
        if (pages[i].url().toLowerCase().includes(targetUrl)) {{
            targetIndex = i;
            break;
        }}
    }}

    if (targetIndex === -1) {{
        // Close last tab as fallback
        targetIndex = pages.length - 1;
    }}

    await pages[targetIndex].close();

    return JSON.stringify({{
        success: true,
        closed_index: targetIndex,
        remaining_count: pages.length - 1
    }});
"""
        else:
            code_body = """
    const pages = page.context().pages();

    if (pages.length <= 1) {
        return JSON.stringify({
            success: false,
            error: 'Cannot close the last tab'
        });
    }

    // Close last tab
    const targetIndex = pages.length - 1;
    await pages[targetIndex].close();

    return JSON.stringify({
        success: true,
        closed_index: targetIndex,
        remaining_count: pages.length - 1
    });
"""

    code = build_async_function(code_body)

    try:
        result = await BrowserExecutor.execute(code)

        # Clear target if we closed the target tab
        try:
            parsed = json.loads(result)
            if parsed.get("success"):
                # Reset target to avoid pointing to closed tab
                BrowserExecutor.set_target_page(None)
            return result
        except json.JSONDecodeError:
            return result

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)
