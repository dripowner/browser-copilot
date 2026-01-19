"""Navigation browser tool."""

import json

from langchain_core.tools import tool

from src.agent.tools._executor import BrowserExecutor
from src.agent.tools._templates import build_async_function


@tool
async def browser_navigate(url: str, new_tab: bool = True) -> str:
    """
    Navigate to a URL.

    By default creates a new tab for navigation to avoid overwriting
    existing user tabs. Set new_tab=False to navigate in the current tab.

    IMPORTANT: When new_tab=True, the new tab is created AND navigated
    in a single operation. The new tab automatically becomes the target
    for all subsequent browser operations.

    Waits for DOM content loaded (fast, works with SPA).

    Args:
        url: Full URL to navigate to (must include https:// or http://)
        new_tab: If True (default), creates a new tab for navigation.
                 If False, navigates in the current target tab.

    Returns:
        JSON string with:
        - success: bool
        - url: str (final URL after navigation)
        - title: str (page title)
        - new_tab_created: bool
        - tab_index: int (index of the tab)
        - error: str (only if success=false)
    """
    escaped_url = url.replace("'", "\\'")

    if new_tab:
        # Create new tab AND navigate in a single browser_run_code call
        # This ensures the navigation happens on the NEW tab
        code_body = f"""
    const targetUrl = '{escaped_url}';

    // Create new page and navigate immediately
    const newPage = await page.context().newPage();
    await newPage.goto(targetUrl, {{
      waitUntil: 'domcontentloaded',
      timeout: 15000
    }});

    // Get tab index
    const pages = page.context().pages();
    const tabIndex = pages.indexOf(newPage);

    const finalUrl = newPage.url();
    const title = await newPage.title();

    return JSON.stringify({{
      success: true,
      url: finalUrl,
      title: title,
      new_tab_created: true,
      tab_index: tabIndex
    }});
"""
    else:
        # Navigate in current target tab (uses page finder)
        page_finder = BrowserExecutor.get_page_finder_code()
        code_body = f"""
    const targetUrl = '{escaped_url}';

    {page_finder}

    // Navigate current target page
    await targetPage.goto(targetUrl, {{
      waitUntil: 'domcontentloaded',
      timeout: 15000
    }});

    // Get tab index
    const pages = page.context().pages();
    const tabIndex = pages.indexOf(targetPage);

    const finalUrl = targetPage.url();
    const title = await targetPage.title();

    return JSON.stringify({{
      success: true,
      url: finalUrl,
      title: title,
      new_tab_created: false,
      tab_index: tabIndex
    }});
"""

    code = build_async_function(code_body)

    try:
        result = await BrowserExecutor.execute(code)

        # Update target page URL if successful
        try:
            parsed = json.loads(result)
            if parsed.get("success") and parsed.get("url"):
                final_url = parsed["url"]
                # Extract domain from URL for targeting
                from urllib.parse import urlparse
                parsed_url = urlparse(final_url)
                if parsed_url.netloc:
                    BrowserExecutor.set_target_page(parsed_url.netloc)
            return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            return result

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "new_tab_created": False
        }, ensure_ascii=False)
