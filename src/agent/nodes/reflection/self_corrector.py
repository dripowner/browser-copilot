"""Auto-corrects common errors like stale references."""

from langchain_core.messages import AIMessage
from langgraph.types import Command

from src.agent.state import BrowserAgentState
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_self_corrector():
    """
    Factory for self corrector.

    Returns:
        Self-correction node function
    """

    def self_corrector(state: BrowserAgentState) -> Command:
        """
        Auto-correct common errors.

        Handles:
        - Playwright syntax errors (InvalidSelectorError, TypeError)
        - Viewport errors (switch to JS click)
        - SPA timeout errors (switch to domcontentloaded)
        - Stale references (refresh snapshot)

        Returns Command routing to:
        - "agent" with correction message (LLM applies fix)
        """
        error_type = state.get("error_type")
        error_message = state.get("error_message", "")
        logger.info(f"Self-correcting error: {error_type}")

        correction_msg = None

        # Playwright Syntax Errors - provide explicit correction
        if error_type == "syntax_error" or "InvalidSelectorError" in error_message:
            if "unexpected symbol" in error_message or "button, [role=" in error_message:
                correction_msg = """SYNTAX ERROR DETECTED: Invalid CSS selector in locator().

ПРОБЛЕМА: Использован неверный синтаксис селектора (запятая вне кавычек или getByRole с множественными типами).

ИСПРАВЛЕНИЕ:
1. Если искал НЕСКОЛЬКО типов элементов → используй locator() с полным CSS:
   ✅ page.locator('button, a, [role="button"]')  // Корректный CSS
   ❌ page.getByRole('button, link')  // ОШИБКА!

2. Если искал ОДИН тип → используй getByRole() ТОЛЬКО с одной ролью:
   ✅ page.getByRole('button')  // Только кнопки

ДЕЙСТВИЕ: Перепиши предыдущий tool call с ПРАВИЛЬНЫМ синтаксисом согласно этим правилам."""

            elif "is not a function" in error_message:
                correction_msg = """SYNTAX ERROR DETECTED: Неправильные скобки для async/await.

ПРОБЛЕМА: Вызов array метода (.slice, .filter) на Promise вместо array.

ИСПРАВЛЕНИЕ:
Оберни allTextContents() в скобки перед вызовом array методов:
   ✅ (await page.getByRole('button').allTextContents()).slice(0, 10)
   ❌ await page.getByRole('button').allTextContents().slice(0, 10)

ДЕЙСТВИЕ: Перепиши предыдущий tool call с ПРАВИЛЬНЫМИ скобками."""

        # Viewport Errors - switch to JS click strategy
        elif error_type == "viewport_error" or "outside of the viewport" in error_message:
            viewport_count = state.get("viewport_error_count", 0) + 1

            if viewport_count >= 2:
                correction_msg = f"""VIEWPORT ERROR (попытка {viewport_count}): Элемент вне viewport, Playwright не может кликнуть.

SWITCH STRATEGY: После 2 viewport errors → используй page.evaluate() JS клик:

```javascript
await page.evaluate(() => {{
  const el = document.querySelector('ваш_селектор');
  if (el) el.click();
}});
```

ДЕЙСТВИЕ: Перепиши предыдущий tool call с JS evaluate вместо обычного click()."""

                return Command(
                    update={
                        "messages": [AIMessage(content=correction_msg)],
                        "viewport_error_count": viewport_count,
                        "error_type": None,
                    },
                    goto="agent",
                )
            else:
                correction_msg = """VIEWPORT ERROR: Элемент вне viewport.

ИСПРАВЛЕНИЕ: Попробуй scrollIntoViewIfNeeded() перед кликом:

```javascript
await element.scrollIntoViewIfNeeded();
await element.click();
```

ДЕЙСТВИЕ: Retry с scroll перед кликом."""

                return Command(
                    update={
                        "messages": [AIMessage(content=correction_msg)],
                        "viewport_error_count": viewport_count,
                        "error_type": None,
                    },
                    goto="agent",
                )

        # SPA Timeout Errors - switch to domcontentloaded
        elif error_type == "timeout" and "networkidle" in error_message:
            correction_msg = """TIMEOUT ERROR: page.goto с networkidle на SPA.

ПРОБЛЕМА: SPA делает бесконечные фоновые запросы - networkidle может никогда не наступить!

SWITCH STRATEGY: Используй waitUntil: 'domcontentloaded' вместо networkidle:

```javascript
await page.goto(url, {
  waitUntil: 'domcontentloaded',  // БЫСТРО - 1-3 сек
  timeout: 15000
});
```

ДЕЙСТВИЕ: Перепиши предыдущий goto с domcontentloaded."""

        # Stale Reference (legacy support)
        elif error_type == "stale_ref":
            logger.info("Auto-correction: Stale ref - routing to agent for retry")
            correction_msg = """STALE REFERENCE: Элемент изменился в DOM.

ДЕЙСТВИЕ: Получи новый локатор и повтори операцию."""

        # Send correction to agent if detected
        if correction_msg:
            logger.info(f"Auto-correction: {error_type} - providing fix guidance")
            return Command(
                update={
                    "messages": [AIMessage(content=correction_msg)],
                    "error_type": None,  # Clear error
                },
                goto="agent",
            )

        # Can't auto-fix - let agent handle through natural reasoning
        logger.warning(f"Cannot auto-correct error type: {error_type}")
        return Command(goto="agent")

    return self_corrector
