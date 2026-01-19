"""Special browser tools for modals, scrolling, etc.

All tools support multi-tab operation through BrowserExecutor's target page
tracking. After browser_navigate or browser_switch_tab, all subsequent
operations will automatically target the correct page.
"""

import json
from typing import Literal, Optional

from langchain_core.tools import tool

from src.agent.tools._executor import BrowserExecutor
from src.agent.tools._selectors import target_to_locator_js
from src.agent.tools._templates import build_async_function


@tool
async def browser_close_modal(
    strategy: Literal["auto", "escape", "click_close", "click_backdrop"] = "auto",
) -> str:
    """
    Close any open modal/dialog on the page.

    Tries multiple strategies to close modals, overlays, and popups.
    Automatically operates on the current target tab.

    Args:
        strategy: How to close the modal:
                  - "auto" (default): Tries all strategies in order
                  - "escape": Press Escape key
                  - "click_close": Click close button (X)
                  - "click_backdrop": Click outside the modal

    Returns:
        JSON string with:
        - success: bool
        - modal_found: bool
        - strategy_used: str (which strategy worked)
        - error: str (only if success=false)
    """
    code_body = f"""
    const strategy = '{strategy}';

    // Find any open modals/dialogs
    const modalSelectors = [
      'dialog[open]',
      '[role="dialog"]',
      '.Modal',
      '.modal',
      '[class*="modal"]',
      '[class*="Modal"]',
      '.Popup',
      '.popup',
      '[class*="popup"]',
      '[class*="Popup"]',
      '[class*="overlay"]'
    ];

    let modalFound = false;
    let modal = null;

    for (const selector of modalSelectors) {{
      const elements = await targetPage.locator(selector).all();
      for (const el of elements) {{
        if (await el.isVisible()) {{
          modalFound = true;
          modal = el;
          break;
        }}
      }}
      if (modalFound) break;
    }}

    if (!modalFound) {{
      return JSON.stringify({{
        success: true,
        modal_found: false,
        note: 'No visible modal found on the page'
      }});
    }}

    // Try strategies
    const strategies = strategy === 'auto'
      ? ['escape', 'click_close', 'click_backdrop']
      : [strategy];

    for (const strat of strategies) {{
      try {{
        if (strat === 'escape') {{
          await targetPage.keyboard.press('Escape');
          await targetPage.waitForTimeout(500);

          // Check if modal closed
          if (!await modal.isVisible()) {{
            return JSON.stringify({{
              success: true,
              modal_found: true,
              strategy_used: 'escape'
            }});
          }}
        }}

        if (strat === 'click_close') {{
          // Find close button inside or near modal
          const closeSelectors = [
            'button[aria-label*="close"]',
            'button[aria-label*="Close"]',
            'button[aria-label*="закрыть"]',
            'button[aria-label*="Закрыть"]',
            '.close-button',
            '.close',
            '[class*="close"]',
            'button:has-text("×")',
            'button:has-text("X")',
            'button:has-text("Close")',
            'button:has-text("Закрыть")'
          ];

          for (const closeSelector of closeSelectors) {{
            const closeBtn = targetPage.locator(closeSelector).first();
            if (await closeBtn.count() > 0 && await closeBtn.isVisible()) {{
              await closeBtn.click({{ force: true }});
              await targetPage.waitForTimeout(500);

              // Check if modal closed
              if (!await modal.isVisible()) {{
                return JSON.stringify({{
                  success: true,
                  modal_found: true,
                  strategy_used: 'click_close'
                }});
              }}
            }}
          }}
        }}

        if (strat === 'click_backdrop') {{
          // Click at coordinates outside the modal
          const box = await modal.boundingBox();
          if (box) {{
            // Click to the left of the modal
            const x = Math.max(10, box.x - 50);
            const y = box.y + box.height / 2;
            await targetPage.mouse.click(x, y);
            await targetPage.waitForTimeout(500);

            // Check if modal closed
            const stillVisible = await modal.isVisible().catch(() => false);
            if (!stillVisible) {{
              return JSON.stringify({{
                success: true,
                modal_found: true,
                strategy_used: 'click_backdrop'
              }});
            }}
          }}
        }}
      }} catch (e) {{
        // Strategy failed, try next
        continue;
      }}
    }}

    return JSON.stringify({{
      success: false,
      modal_found: true,
      error: 'Could not close modal with any strategy'
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
async def browser_scroll(
    direction: Literal["up", "down", "left", "right"] = "down",
    amount: int = 500,
    target: Optional[str] = None,
) -> str:
    """
    Scroll the page or a specific element.

    Automatically operates on the current target tab.

    Args:
        direction: Direction to scroll (default: "down")
        amount: Pixels to scroll (default: 500)
        target: Optional element selector. If provided, scrolls that element
                into view. If not provided, scrolls the page.

    Returns:
        JSON string with:
        - success: bool
        - scrolled: str (direction)
        - error: str (only if success=false)
    """
    if target:
        # Scroll element into view
        locator_js = target_to_locator_js(target, page_var="targetPage")
        code_body = f"""
    const locator = {locator_js};

    const count = await locator.count();

    if (count === 0) {{
      return JSON.stringify({{
        success: false,
        error: 'No elements found matching the selector'
      }});
    }}

    await locator.first().scrollIntoViewIfNeeded();

    return JSON.stringify({{
      success: true,
      scrolled: 'to_element'
    }});
"""
    else:
        # Scroll page
        scroll_x = 0
        scroll_y = 0

        if direction == "down":
            scroll_y = amount
        elif direction == "up":
            scroll_y = -amount
        elif direction == "right":
            scroll_x = amount
        elif direction == "left":
            scroll_x = -amount

        code_body = f"""
    await targetPage.evaluate(() => {{
      window.scrollBy({scroll_x}, {scroll_y});
    }});

    return JSON.stringify({{
      success: true,
      scrolled: '{direction}'
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
async def browser_go_back() -> str:
    """
    Navigate back in browser history.

    Equivalent to clicking the browser's back button.
    Automatically operates on the current target tab.

    Returns:
        JSON string with:
        - success: bool
        - url: str (URL after going back)
        - error: str (only if success=false)

    Note:
        For SPA applications, prefer direct navigation with browser_navigate
        as history navigation may not work as expected.
    """
    code_body = """
    await targetPage.goBack({ waitUntil: 'domcontentloaded', timeout: 10000 });

    return JSON.stringify({
      success: true,
      url: targetPage.url()
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


@tool
async def browser_reload() -> str:
    """
    Reload the current page.

    Useful when page content becomes stale or needs refresh.
    Automatically operates on the current target tab.

    Returns:
        JSON string with:
        - success: bool
        - url: str (current URL after reload)
        - error: str (only if success=false)
    """
    code_body = """
    await targetPage.reload({ waitUntil: 'domcontentloaded', timeout: 15000 });

    return JSON.stringify({
      success: true,
      url: targetPage.url()
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
