"""Data extraction browser tools.

All tools support multi-tab operation through BrowserExecutor's target page
tracking. After browser_navigate or browser_switch_tab, all subsequent
operations will automatically target the correct page.
"""

import json

from langchain_core.tools import tool

from src.agent.tools._executor import BrowserExecutor
from src.agent.tools._selectors import target_to_locator_js
from src.agent.tools._templates import build_async_function


@tool
async def browser_get_text(
    target: str, all_matches: bool = False, limit: int = 50
) -> str:
    """
    Extract text content from element(s) on the page.

    Automatically cleans text from invisible Unicode characters.
    Automatically operates on the current target tab.

    Target formats:
    - CSS: ".class", "#id", "[attribute]"
    - Role: "button:Submit", "link:Learn more", "button"
    - Text: "text:Some text"
    - Placeholder: "placeholder:Email"
    - Label: "label:Username"
    - TestId: "testid:submit-button"

    Args:
        target: Element selector in any supported format
        all_matches: If True, returns text from ALL matching elements.
                     If False (default), returns text from first match only.
        limit: Maximum number of elements to extract when all_matches=True.
               Default: 50. Prevents memory issues with large lists.

    Returns:
        JSON string with:
        - success: bool
        - text: str (single text if all_matches=False)
        - texts: list[str] (list of texts if all_matches=True)
        - count: int (number of elements found)
        - error: str (only if success=false)
    """
    locator_js = target_to_locator_js(target, page_var="targetPage")
    all_matches_js = "true" if all_matches else "false"

    code_body = f"""
    function cleanText(text) {{
      if (!text) return '';
      return text
        .replace(/\\xAD/g, '')  // Remove soft hyphens completely
        .replace(/[\\u200B-\\u200D\\uFEFF\\xA0]/g, ' ')
        .replace(/\\s+/g, ' ')
        .trim();
    }}

    const locator = {locator_js};
    const allMatches = {all_matches_js};
    const limit = {limit};

    const count = await locator.count();

    if (count === 0) {{
      return JSON.stringify({{
        success: false,
        error: 'No elements found matching the selector',
        count: 0
      }});
    }}

    if (allMatches) {{
      // Extract text from multiple elements
      const texts = [];
      const extractCount = Math.min(count, limit);

      for (let i = 0; i < extractCount; i++) {{
        const text = await locator.nth(i).textContent();
        texts.push(cleanText(text));
      }}

      return JSON.stringify({{
        success: true,
        texts: texts,
        count: count,
        extracted: extractCount
      }});
    }} else {{
      // Extract from first match only
      const text = await locator.first().textContent();

      return JSON.stringify({{
        success: true,
        text: cleanText(text),
        count: count
      }});
    }}
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
async def browser_get_attribute(target: str, attribute: str) -> str:
    """
    Get attribute value from an element.

    Useful for extracting href, src, data-* attributes, etc.
    Automatically operates on the current target tab.

    Target formats:
    - CSS: ".class", "#id", "[attribute]"
    - Role: "button:Submit", "link:Learn more"
    - Text: "text:Some text"

    Args:
        target: Element selector in any supported format
        attribute: Attribute name to get (e.g., "href", "src", "data-id")

    Returns:
        JSON string with:
        - success: bool
        - value: str or null (attribute value)
        - error: str (only if success=false)
    """
    locator_js = target_to_locator_js(target, page_var="targetPage")
    escaped_attr = attribute.replace("'", "\\'")

    code_body = f"""
    function cleanText(text) {{
      if (!text) return text;
      return text
        .replace(/\\xAD/g, '')  // Remove soft hyphens completely
        .replace(/[\\u200B-\\u200D\\uFEFF\\xA0]/g, ' ')
        .replace(/\\s+/g, ' ')
        .trim();
    }}

    const locator = {locator_js};
    const attributeName = '{escaped_attr}';

    const count = await locator.count();

    if (count === 0) {{
      return JSON.stringify({{
        success: false,
        error: 'No elements found matching the selector'
      }});
    }}

    const value = await locator.first().getAttribute(attributeName);

    return JSON.stringify({{
      success: true,
      value: value ? cleanText(value) : null
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
async def browser_get_page_info() -> str:
    """
    Get current page information.

    Returns URL and title of the current target page.
    No parameters needed.

    Returns:
        JSON string with:
        - success: bool
        - url: str (current page URL)
        - title: str (current page title)
        - error: str (only if success=false)
    """
    code_body = """
    const url = targetPage.url();
    const title = await targetPage.title();

    return JSON.stringify({
      success: true,
      url: url,
      title: title
    });
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
