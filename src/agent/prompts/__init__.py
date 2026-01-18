"""Модульная система промптов для Browser Copilot Agent."""

from src.agent.prompts.base import BASE_PROMPT
from src.agent.prompts.browser_rules import BROWSER_RULES
from src.agent.prompts.error_recovery import ERROR_RECOVERY_GUIDE
from src.agent.prompts.examples.complex import COMPLEX_EXAMPLES
from src.agent.prompts.examples.simple import SIMPLE_EXAMPLES
from src.agent.prompts.playwright_patterns import PLAYWRIGHT_PATTERNS

__all__ = [
    # Модули
    "BASE_PROMPT",
    "BROWSER_RULES",
    "PLAYWRIGHT_PATTERNS",
    "ERROR_RECOVERY_GUIDE",
    "SIMPLE_EXAMPLES",
    "COMPLEX_EXAMPLES",
    # Готовые промпты
    "SYSTEM_PROMPT",
    "SYSTEM_PROMPT_MINIMAL",
    "SYSTEM_PROMPT_COMPLEX",
]

# Базовый системный промпт (по умолчанию)
# Включает: роль + правила + Playwright patterns + error recovery
# Tools описываются через bind_tools() - не дублируем в промпте
# PLAYWRIGHT_PATTERNS содержит comprehensive guide по Playwright Page API
SYSTEM_PROMPT = "\n\n".join(
    [
        BASE_PROMPT,
        BROWSER_RULES,
        PLAYWRIGHT_PATTERNS,  # Comprehensive Playwright Page API guide
        ERROR_RECOVERY_GUIDE,  # Паттерны восстановления для автономности
    ]
)

# Минимальный промпт без Playwright patterns (после 25+ шагов для экономии токенов)
# Только основа: роль + правила + error recovery (критично!)
# Tools описываются через bind_tools() - не дублируем в промпте
SYSTEM_PROMPT_MINIMAL = "\n\n".join(
    [
        BASE_PROMPT,
        BROWSER_RULES,
        ERROR_RECOVERY_GUIDE,  # Критично для правильной обработки ошибок
    ]
)

# Промпт для сложных задач с циклами
# Включает дополнительные примеры со сложной логикой
# Tools описываются через bind_tools() - не дублируем в промпте
SYSTEM_PROMPT_COMPLEX = "\n\n".join(
    [
        BASE_PROMPT,
        BROWSER_RULES,
        SIMPLE_EXAMPLES,
        COMPLEX_EXAMPLES,
    ]
)
