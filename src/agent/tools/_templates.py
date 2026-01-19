"""JavaScript code templates for browser tools.

This module contains reusable JavaScript code fragments that are embedded
into the generated Playwright code by browser tools.
"""

# Clean text from invisible Unicode characters
# Used by: browser_get_text, browser_get_attribute
CLEAN_TEXT_JS = """
function cleanText(text) {
  if (!text) return '';
  return text
    .replace(/\\xAD/g, '')  // Remove soft hyphens completely
    .replace(/[\\u200B-\\u200D\\uFEFF\\xA0]/g, ' ')
    .replace(/\\s+/g, ' ')
    .trim();
}
"""

# Validate that an action had an effect
# Used by: browser_click (verify mode)
POST_ACTION_VALIDATION_JS = """
async function validateAction(page, checkFn, timeout = 3000) {
  const startTime = Date.now();
  while (Date.now() - startTime < timeout) {
    if (await checkFn()) return true;
    await page.waitForTimeout(200);
  }
  return false;
}
"""

# Build error response object
ERROR_RESPONSE_JS = """
function errorResponse(message, details = {}) {
  return JSON.stringify({
    success: false,
    error: message,
    ...details
  });
}
"""

# Build success response object
SUCCESS_RESPONSE_JS = """
function successResponse(data = {}) {
  return JSON.stringify({
    success: true,
    ...data
  });
}
"""

# Common wrapper that includes error handling
ASYNC_WRAPPER_START = """
async (page) => {
  try {
"""

ASYNC_WRAPPER_END = """
  } catch (error) {
    return JSON.stringify({
      success: false,
      error: error.message,
      errorType: error.name
    });
  }
}
"""


def wrap_with_error_handling(code: str) -> str:
    """
    Wrap JavaScript code with try-catch error handling.

    Args:
        code: JavaScript code to wrap (without async (page) => { })

    Returns:
        Complete async function with error handling
    """
    return f"""async (page) => {{
  try {{
{code}
  }} catch (error) {{
    return JSON.stringify({{
      success: false,
      error: error.message,
      errorType: error.name
    }});
  }}
}}"""


def build_async_function(
    body: str,
    helpers: list[str] | None = None,
    use_target_page: bool = False
) -> str:
    """
    Build complete async Playwright function.

    Args:
        body: Main function body (JavaScript code)
              When use_target_page=True, use 'targetPage' instead of 'page' in body
        helpers: List of helper function names to include
                 Options: 'cleanText', 'validateAction', 'errorResponse', 'successResponse'
        use_target_page: If True, includes page finder code and sets 'targetPage' variable.
                        The body should use 'targetPage' for operations that need to
                        target the correct tab in multi-tab scenarios.

    Returns:
        Complete async (page) => { ... } function
    """
    helper_code = ""

    if helpers:
        helper_map = {
            "cleanText": CLEAN_TEXT_JS,
            "validateAction": POST_ACTION_VALIDATION_JS,
            "errorResponse": ERROR_RESPONSE_JS,
            "successResponse": SUCCESS_RESPONSE_JS,
        }
        for helper in helpers:
            if helper in helper_map:
                helper_code += helper_map[helper] + "\n"

    # Page finder code for multi-tab support
    page_finder = ""
    if use_target_page:
        from src.agent.tools._executor import BrowserExecutor
        page_finder = BrowserExecutor.get_page_finder_code()

    return f"""async (page) => {{
  try {{
{helper_code}
{page_finder}
{body}
  }} catch (error) {{
    return JSON.stringify({{
      success: false,
      error: error.message,
      errorType: error.name
    }});
  }}
}}"""
