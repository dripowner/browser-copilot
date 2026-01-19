"""BrowserExecutor singleton for executing Playwright code via MCP."""

import json
import re

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class BrowserExecutor:
    """
    Singleton that holds reference to MCP browser_run_code tool.

    This class must be initialized with the MCP tool before any browser tools
    can be used. All browser_* tools use this executor internally.

    Tab Management Strategy:
    Since MCP's internal _currentTab doesn't update correctly when new pages
    are created via browser_run_code, we use a different approach:
    - Track the "target page URL" that tools should operate on
    - Each browser_run_code call finds the correct page by URL pattern
    - This allows multi-tab workflows without relying on MCP's tab tracking
    """

    _browser_run_code_tool = None
    _initialized = False
    _target_page_url: str | None = None  # URL pattern to find target page

    @classmethod
    def initialize(cls, browser_run_code_tool) -> None:
        """
        Initialize the executor with MCP browser_run_code tool.

        Called from main.py after getting MCP tools.

        Args:
            browser_run_code_tool: The browser_run_code tool from MCP server
        """
        cls._browser_run_code_tool = browser_run_code_tool
        cls._initialized = True
        cls._target_page_url = None
        logger.info("BrowserExecutor initialized with browser_run_code tool")

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if executor is initialized."""
        return cls._initialized

    @classmethod
    def _extract_json_from_mcp_response(cls, text: str) -> str:
        """
        Extract JSON from MCP markdown response format.

        @playwright/mcp returns responses in markdown format:
        ```
        ### Result
        "{\"success\":true,...}"

        ### Ran Playwright code
        await (async (page) => {...
        ```

        This method extracts the JSON string from the Result block.

        Args:
            text: Raw MCP response text

        Returns:
            Extracted JSON string, or original text if no Result block found
        """
        if "### Result" not in text:
            return text

        # Pattern to match: ### Result\n"<json string>"\n
        # The JSON is escaped and wrapped in quotes
        match = re.search(r'### Result\s*\n"(.*?)"(?:\s*\n|$)', text, re.DOTALL)
        if not match:
            # Try alternative: JSON might not be in quotes (direct value)
            match = re.search(r'### Result\s*\n(.+?)(?:\n###|$)', text, re.DOTALL)
            if match:
                return match.group(1).strip()
            return text

        escaped_json = match.group(1)

        # Unescape the JSON string (it's double-escaped from MCP)
        try:
            # First unescape: convert \" to " and \\ to \
            unescaped = escaped_json.replace('\\"', '"').replace("\\\\", "\\")

            # Validate it's proper JSON
            json.loads(unescaped)
            return unescaped
        except json.JSONDecodeError:
            # If unescaping failed, try the original
            logger.warning(f"Failed to unescape JSON, using original: {escaped_json[:100]}...")
            return escaped_json

    @classmethod
    async def execute(cls, code: str) -> str:
        """
        Execute Playwright JavaScript code via browser_run_code MCP tool.

        Args:
            code: Playwright JavaScript code in format:
                  async (page) => { ... return result; }

        Returns:
            Result of code execution as string (JSON)

        Raises:
            RuntimeError: If executor not initialized
        """
        if not cls._initialized or cls._browser_run_code_tool is None:
            raise RuntimeError(
                "BrowserExecutor not initialized. "
                "Call BrowserExecutor.initialize(tool) first."
            )

        logger.debug(f"Executing Playwright code: {code[:100]}...")

        result = await cls._browser_run_code_tool.ainvoke({"code": code})

        logger.debug(f"Execution raw result type: {type(result)}, value: {str(result)[:200]}...")

        # MCP tool может возвращать разные типы:
        # - str: прямой результат (часто в markdown формате от @playwright/mcp)
        # - list: список content blocks
        # - dict: структурированный ответ
        raw_text: str
        if isinstance(result, str):
            raw_text = result
        elif isinstance(result, list):
            # Извлечь текст из content blocks
            texts = []
            for item in result:
                if isinstance(item, dict) and "text" in item:
                    texts.append(item["text"])
                elif isinstance(item, str):
                    texts.append(item)
            raw_text = "\n".join(texts) if texts else str(result)
        elif isinstance(result, dict):
            # Попробовать извлечь text или content
            if "text" in result:
                raw_text = result["text"]
            elif "content" in result:
                raw_text = str(result["content"])
            else:
                raw_text = str(result)
        else:
            raw_text = str(result)

        # Extract JSON from MCP markdown response format
        extracted = cls._extract_json_from_mcp_response(raw_text)
        logger.debug(f"Extracted result: {extracted[:200]}...")

        return extracted

    @classmethod
    def set_target_page(cls, url_pattern: str | None) -> None:
        """
        Set the target page URL pattern for subsequent operations.

        All browser tools will find and operate on the page matching this pattern.
        Set to None to use MCP's default page (current tab).

        Args:
            url_pattern: URL substring to match (e.g., 'lavka.yandex.ru')
        """
        cls._target_page_url = url_pattern
        logger.debug(f"Target page set to: {url_pattern}")

    @classmethod
    def get_target_page(cls) -> str | None:
        """Get the current target page URL pattern."""
        return cls._target_page_url

    @classmethod
    def get_page_finder_code(cls) -> str:
        """
        Generate JavaScript code to find the target page.

        Returns JS code that sets `targetPage` variable to the correct page.
        If no target URL is set, uses the default `page` from MCP.
        """
        if cls._target_page_url is None:
            return "const targetPage = page;"

        escaped_url = cls._target_page_url.replace("'", "\\'")
        return f"""
    const allPages = page.context().pages();
    let targetPage = allPages.find(p => p.url().toLowerCase().includes('{escaped_url}'.toLowerCase()));
    if (!targetPage) {{
        // Fallback to last page (most recently created) or default page
        targetPage = allPages.length > 0 ? allPages[allPages.length - 1] : page;
    }}
"""
