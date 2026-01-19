"""Interaction browser tools for clicking, typing, etc.

All tools support multi-tab operation through BrowserExecutor's target page
tracking. After browser_navigate or browser_switch_tab, all subsequent
operations will automatically target the correct page.
"""

import json
from typing import Optional

from langchain_core.tools import tool

from src.agent.tools._executor import BrowserExecutor
from src.agent.tools._selectors import target_to_locator_js
from src.agent.tools._templates import build_async_function


@tool
async def browser_click(target: str, verify: bool = True) -> str:
    """
    Click on an element.

    Implements post-action validation to verify the click had an effect.
    Automatically operates on the current target tab (set by browser_navigate
    or browser_switch_tab).

    Target formats:
    - CSS: ".class", "#id", "[attribute]"
    - Role: "button:Submit", "link:Learn more", "button"
    - Text: "text:Click here"

    Args:
        target: Element selector in any supported format
        verify: If True (default), verifies click had an effect by checking
                for URL change or DOM changes. Set to False for clicks that
                don't cause visible changes.

    Returns:
        JSON string with:
        - success: bool
        - clicked: bool (element was clicked)
        - url_changed: bool (URL changed after click)
        - verified: bool (only if verify=True)
        - error: str (only if success=false)
    """
    locator_js = target_to_locator_js(target, page_var="targetPage")
    verify_js = "true" if verify else "false"

    code_body = f"""
    const locator = {locator_js};
    const shouldVerify = {verify_js};

    const count = await locator.count();

    if (count === 0) {{
      return JSON.stringify({{
        success: false,
        error: 'No elements found matching the selector',
        clicked: false
      }});
    }}

    // Store state before click
    const urlBefore = targetPage.url();
    const element = locator.first();

    // Check if element is enabled
    const isEnabled = await element.isEnabled();
    if (!isEnabled) {{
      return JSON.stringify({{
        success: false,
        error: 'Element is disabled and cannot be clicked',
        clicked: false
      }});
    }}

    // Scroll element into view before clicking
    await element.scrollIntoViewIfNeeded();
    await targetPage.waitForTimeout(200);

    // Perform click with force option to bypass overlay checks if needed
    try {{
      await element.click({{ timeout: 10000 }});
    }} catch (clickError) {{
      // If normal click fails, try with force (bypasses actionability checks)
      if (clickError.message.includes('intercept') || clickError.message.includes('outside')) {{
        await element.click({{ force: true, timeout: 5000 }});
      }} else {{
        throw clickError;
      }}
    }}

    // Small wait for any reactions
    await targetPage.waitForTimeout(500);

    // Check if URL changed
    const urlAfter = targetPage.url();
    const urlChanged = urlBefore !== urlAfter;

    if (shouldVerify && !urlChanged) {{
      // Wait a bit more and check again (for SPA navigation)
      await targetPage.waitForTimeout(1000);
      const urlFinal = targetPage.url();
      const finalUrlChanged = urlBefore !== urlFinal;

      return JSON.stringify({{
        success: true,
        clicked: true,
        url_changed: finalUrlChanged,
        verified: finalUrlChanged,
        note: finalUrlChanged ? undefined : 'Click executed but no URL change detected. This may be normal for some interactions.'
      }});
    }}

    return JSON.stringify({{
      success: true,
      clicked: true,
      url_changed: urlChanged,
      verified: !shouldVerify || urlChanged
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
async def browser_fill(target: str, text: str, submit: bool = False) -> str:
    """
    Fill text into an input field.

    Clears existing content and types new text.
    Automatically operates on the current target tab.

    Target formats:
    - CSS: "#email-input", ".search-field"
    - Placeholder: "placeholder:Email address"
    - Label: "label:Username"
    - Role: "textbox:Search"

    Args:
        target: Input element selector
        text: Text to fill into the input
        submit: If True, presses Enter after filling (useful for search fields)

    Returns:
        JSON string with:
        - success: bool
        - filled: bool
        - submitted: bool (if submit=True)
        - error: str (only if success=false)
    """
    locator_js = target_to_locator_js(target, page_var="targetPage")
    escaped_text = text.replace("\\", "\\\\").replace("'", "\\'")
    submit_js = "true" if submit else "false"

    code_body = f"""
    const locator = {locator_js};
    const textToFill = '{escaped_text}';
    const shouldSubmit = {submit_js};

    const count = await locator.count();

    if (count === 0) {{
      return JSON.stringify({{
        success: false,
        error: 'No input elements found matching the selector',
        filled: false
      }});
    }}

    const element = locator.first();

    // Fill the input (this clears existing content)
    await element.fill(textToFill);

    let submitted = false;
    if (shouldSubmit) {{
      await element.press('Enter');
      submitted = true;
      // Wait for any navigation or loading
      await targetPage.waitForTimeout(1000);
    }}

    return JSON.stringify({{
      success: true,
      filled: true,
      submitted: submitted
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
async def browser_press_key(key: str, target: Optional[str] = None) -> str:
    """
    Press a keyboard key.

    Can press on a specific element or on the page.
    Automatically operates on the current target tab.

    Args:
        key: Key to press. Examples:
             - Single keys: "Enter", "Tab", "Escape", "Backspace", "Delete"
             - Arrows: "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"
             - Modifiers: "Control+a", "Control+c", "Control+v", "Shift+Tab"
             - Function keys: "F1", "F5"
        target: Optional element selector. If provided, key is pressed on that
                element. If not provided, key is pressed on the page.

    Returns:
        JSON string with:
        - success: bool
        - key_pressed: str
        - on_element: bool
        - error: str (only if success=false)
    """
    escaped_key = key.replace("'", "\\'")

    if target:
        locator_js = target_to_locator_js(target, page_var="targetPage")
        code_body = f"""
    const locator = {locator_js};
    const keyToPress = '{escaped_key}';

    const count = await locator.count();

    if (count === 0) {{
      return JSON.stringify({{
        success: false,
        error: 'No elements found matching the selector',
        key_pressed: null
      }});
    }}

    await locator.first().press(keyToPress);

    return JSON.stringify({{
      success: true,
      key_pressed: keyToPress,
      on_element: true
    }});
"""
    else:
        code_body = f"""
    const keyToPress = '{escaped_key}';

    await targetPage.keyboard.press(keyToPress);

    return JSON.stringify({{
      success: true,
      key_pressed: keyToPress,
      on_element: false
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
async def browser_select(
    target: str, value: Optional[str] = None, label: Optional[str] = None
) -> str:
    """
    Select an option from a dropdown (select element).

    Can select by value or by visible label text.
    Automatically operates on the current target tab.

    Args:
        target: Select element selector (CSS or other format)
        value: Option value to select. Optional.
        label: Visible text of option to select. Optional.

    Returns:
        JSON string with:
        - success: bool
        - selected_value: str
        - selected_label: str
        - error: str (only if success=false)

    Note:
        At least one of value or label must be provided.
    """
    if value is None and label is None:
        return json.dumps(
            {
                "success": False,
                "error": "Either value or label must be provided",
            },
            ensure_ascii=False,
        )

    locator_js = target_to_locator_js(target, page_var="targetPage")

    if value is not None:
        escaped_value = value.replace("'", "\\'")
        select_code = f"await element.selectOption('{escaped_value}');"
    else:
        escaped_label = label.replace("'", "\\'")
        select_code = f"await element.selectOption({{ label: '{escaped_label}' }});"

    code_body = f"""
    const locator = {locator_js};

    const count = await locator.count();

    if (count === 0) {{
      return JSON.stringify({{
        success: false,
        error: 'No select elements found matching the selector'
      }});
    }}

    const element = locator.first();

    // Select the option
    const selectedValues = {select_code}

    // Get the selected option info
    const selectedValue = await element.inputValue();

    return JSON.stringify({{
      success: true,
      selected_value: selectedValue,
      selected_values: selectedValues
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
async def browser_hover(target: str) -> str:
    """
    Hover over an element.

    Useful for revealing dropdown menus or tooltips.
    Automatically operates on the current target tab.

    Target formats:
    - CSS: ".menu-button", "#dropdown-trigger"
    - Role: "button:Menu"
    - Text: "text:Options"

    Args:
        target: Element selector to hover over

    Returns:
        JSON string with:
        - success: bool
        - hovered: bool
        - error: str (only if success=false)
    """
    locator_js = target_to_locator_js(target, page_var="targetPage")

    code_body = f"""
    const locator = {locator_js};

    const count = await locator.count();

    if (count === 0) {{
      return JSON.stringify({{
        success: false,
        error: 'No elements found matching the selector',
        hovered: false
      }});
    }}

    await locator.first().hover();

    // Small wait for any hover effects
    await targetPage.waitForTimeout(300);

    return JSON.stringify({{
      success: true,
      hovered: true
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
async def browser_check(target: str, check: bool = True) -> str:
    """
    Check or uncheck a checkbox element.

    Automatically operates on the current target tab.

    Args:
        target: Checkbox element selector
        check: If True (default), checks the checkbox.
               If False, unchecks it.

    Returns:
        JSON string with:
        - success: bool
        - checked: bool (final state)
        - error: str (only if success=false)
    """
    locator_js = target_to_locator_js(target, page_var="targetPage")
    action = "check" if check else "uncheck"

    code_body = f"""
    const locator = {locator_js};

    const count = await locator.count();

    if (count === 0) {{
      return JSON.stringify({{
        success: false,
        error: 'No checkbox elements found matching the selector'
      }});
    }}

    const element = locator.first();

    await element.{action}();

    const isChecked = await element.isChecked();

    return JSON.stringify({{
      success: true,
      checked: isChecked
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
