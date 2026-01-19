"""Модульная система промптов для Browser Copilot Agent."""

from src.agent.prompts.base import BASE_PROMPT
from src.agent.prompts.browser_rules import BROWSER_RULES
from src.agent.prompts.error_recovery import ERROR_RECOVERY_GUIDE
from src.agent.prompts.examples.complex import COMPLEX_EXAMPLES
from src.agent.prompts.examples.simple import SIMPLE_EXAMPLES

__all__ = [
    # Модули
    "BASE_PROMPT",
    "BROWSER_RULES",
    "ERROR_RECOVERY_GUIDE",
    "SIMPLE_EXAMPLES",
    "COMPLEX_EXAMPLES",
    # Готовые промпты
    "SYSTEM_PROMPT",
]

# Базовый системный промпт (по умолчанию)
# PLAYWRIGHT_PATTERNS удалён - код теперь инкапсулирован в browser tools
# Tools описываются через bind_tools() - не дублируем в промпте
SYSTEM_PROMPT = "\n\n".join(
    [
        BASE_PROMPT,
        BROWSER_RULES,
        ERROR_RECOVERY_GUIDE,
    ]
)
