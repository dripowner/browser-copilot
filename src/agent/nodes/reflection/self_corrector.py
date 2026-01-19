"""Self-correction node for automatic error recovery using high-level tools."""

from langchain_core.messages import AIMessage
from langgraph.types import Command

from src.agent.state import BrowserAgentState
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_self_corrector():
    """
    Factory for self corrector.

    Returns:
        Self-correction node function that provides recovery instructions
        using high-level browser tools (not raw Playwright API).
    """

    def self_corrector(state: BrowserAgentState) -> Command:
        """
        Auto-correct common errors using high-level browser tools.

        Handles:
        - viewport_error: Element outside visible area
        - timeout / timeout_other: Page load timeout
        - stale_ref: DOM changed, element reference invalid
        - element_not_found: Element not found on page

        Returns Command routing to "agent" with recovery instructions.
        """
        error_type = state.get("error_type")
        error_message = state.get("error_message", "")

        logger.info(f"Self-correcting error: {error_type}")

        correction_msg = None

        # Viewport Error - element outside visible area
        if error_type == "viewport_error":
            correction_msg = """VIEWPORT ERROR: Элемент вне видимой области.

ДЕЙСТВИЯ для восстановления:

1. Возможно модалка или overlay блокирует — закрой их:
   browser_close_modal(strategy="auto")

2. Прокрути к элементу:
   browser_scroll(target="[твой селектор]")

3. Повтори исходное действие (browser_click или browser_fill)

Пример:
browser_close_modal(strategy="auto")
browser_scroll(target="button:Оформить заказ")
browser_click(target="button:Оформить заказ")

Если не помогает — используй browser_explore_page() чтобы найти альтернативный элемент."""

        # Timeout Error - networkidle specific
        elif error_type == "timeout":
            if "networkidle" in error_message.lower():
                correction_msg = """TIMEOUT: Превышено время ожидания (networkidle).

ПРИЧИНА: SPA делает бесконечные фоновые запросы.

ДЕЙСТВИЯ:

1. Дождись загрузки DOM (быстрее чем networkidle):
   browser_wait_for_load(state="domcontentloaded")

2. Проверь что страница готова:
   browser_explore_page()

3. Продолжай работу с найденными элементами

НЕ жди networkidle на SPA сайтах — это может занять бесконечно!"""
            else:
                correction_msg = """TIMEOUT: Превышено время ожидания.

ДЕЙСТВИЯ:

1. Перезагрузи страницу:
   browser_reload()

2. Дождись загрузки:
   browser_wait_for_load(state="domcontentloaded")

3. Исследуй страницу заново:
   browser_explore_page()

4. Найди нужный элемент и повтори действие

Если страница не загружается — проверь подключение к браузеру."""

        # Timeout Other - generic timeout
        elif error_type == "timeout_other":
            correction_msg = """TIMEOUT: Операция заняла слишком много времени.

ДЕЙСТВИЯ:

1. Дождись стабилизации страницы:
   browser_wait_for_load(state="domcontentloaded")

2. Проверь что элемент появился:
   browser_wait_for(target="[твой селектор]", state="visible")

3. Если элемент всё ещё не появляется — исследуй страницу:
   browser_explore_page()

4. Возможно элемент находится в другом месте или имеет другой селектор."""

        # Stale Reference - DOM changed
        elif error_type == "stale_ref":
            correction_msg = """STALE REFERENCE: DOM изменился, селектор недействителен.

ОБЯЗАТЕЛЬНЫЕ ДЕЙСТВИЯ:

1. Исследуй страницу заново — получи НОВЫЕ селекторы:
   browser_explore_page()

2. В результате найди нужный элемент по тексту или типу

3. Используй НОВЫЙ selector из результата для повтора действия

ВАЖНО:
- Старый селектор больше НЕ работает — не используй его!
- browser_explore_page() даст актуальные селекторы
- Если элемент исчез — проверь URL через browser_get_page_info()"""

        # Element Not Found
        elif error_type == "element_not_found":
            correction_msg = """ELEMENT NOT FOUND: Элемент не найден на странице.

ДЕЙСТВИЯ:

1. Возможно элемент ниже — прокрути страницу:
   browser_scroll(direction="down", amount=500)

2. Исследуй видимые элементы:
   browser_explore_page()

3. Найди похожий элемент в результатах

Если элемент должен появиться динамически:
   browser_wait_for(target="[селектор]", state="visible", timeout=10000)

Если элемент всё ещё не найден:
1. Проверь что ты на правильной странице: browser_get_page_info()
2. Если URL неправильный — перейди на нужную страницу
3. Попробуй альтернативный способ достичь цели"""

        # Send correction to agent
        if correction_msg:
            logger.info(f"Providing recovery guidance for: {error_type}")
            return Command(
                update={
                    "messages": [AIMessage(content=correction_msg)],
                    "error_type": None,  # Clear error type
                },
                goto="agent",
            )

        # Unknown error - let agent handle naturally
        logger.warning(f"No recovery strategy for error type: {error_type}")
        return Command(goto="agent")

    return self_corrector
