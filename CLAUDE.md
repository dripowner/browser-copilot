# Browser Copilot - Development Guide

Руководство для разработки и доработки Browser Copilot Agent.

## Архитектура

### Обзор

```text
src/
├── agent/                  # AI Agent (LangGraph)
│   ├── graph.py           # Main graph with Command API
│   ├── state.py           # BrowserAgentState definition
│   ├── prompts.py         # System prompt с планированием
│   └── nodes/             # Modular nodes (Command-based routing)
│       ├── agent_node.py          # Core reasoning
│       ├── tools_node.py          # Tool execution
│       ├── validation/            # Validation nodes
│       │   ├── critical_action_validator.py
│       │   └── goal_validator.py
│       ├── reflection/            # Reflection nodes
│       │   ├── progress_analyzer.py
│       │   ├── strategy_adapter.py
│       │   ├── quality_evaluator.py
│       │   └── self_corrector.py
│       └── special/               # Special nodes
│           ├── human_in_loop.py
│           ├── progress_reporter.py
│           └── memory_manager.py
├── ui/                    # User Interface
│   └── cli.py            # Rich-based CLI with interrupt handling
└── utils/                # Utilities
    ├── config.py         # Pydantic configuration
    └── logger.py         # Logging setup
```

### Поток выполнения

1. **User** вводит задачу в CLI
2. **CLI** создает `BrowserAgentState` с начальными значениями
3. **LangGraph Agent** начинает с узла `agent`
4. **Agent Node** использует LLM для рассуждения и принимает решение через `Command(goto=...)`
5. В зависимости от решения агента:
   - Критическое действие → `critical_action_validator` → опционально `human_in_loop`
   - Обычное действие → `tools` → выполнение инструментов браузера
   - Проверка завершения → `goal_validator`
   - Ошибки обрабатываются через ToolNode error handling и self_corrector для stale_ref
6. **MCP Client** отправляет команды в @playwright/mcp (запускается автоматически)
7. **@playwright/mcp** подключается к Edge/Chrome через CDP (Chrome DevTools Protocol)
8. **Browser** выполняет команды
9. Результаты возвращаются и анализируются нодами (reflection, validation)
10. Цикл продолжается до достижения цели или ошибки

**Важно:**

- Агент работает в вашем обычном браузере с вашими авторизациями и расширениями через CDP подключение
- MCP сервер @playwright/mcp запускается автоматически при старте приложения
- Используется **Command API** - каждая нода явно указывает следующую через `Command(goto="next_node")`
- Нет conditional edges - весь контроль потока в руках нод

## Development Commands

### Установка зависимостей

```bash
# Main dependencies
uv add langchain langgraph langchain-openai langchain-mcp-adapters

# Additional dependencies
uv add pydantic python-dotenv rich

# Dev dependencies
uv add ruff --group dev
```

**ВАЖНО:** Используйте ТОЛЬКО `uv add` для добавления зависимостей, НЕ редактируйте `pyproject.toml` вручную.

### Запуск

#### Предварительная настройка (один раз)

**Создать ярлык браузера с CDP:**

Создайте ярлык на рабочем столе с путем:

```text
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222
```

Или для Chrome:

```text
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

#### Рабочий процесс

```bash
# 1. Запустить браузер через созданный ярлык (просто двойной клик)

# 2. Запустить агента
uv run python main.py
```

MCP сервер @playwright/mcp запустится автоматически при старте приложения.

### Линтинг

```bash
# Проверка кода
uv run ruff check src/

# Автоматическое исправление
uv run ruff check src/ --fix

# Форматирование
uv run ruff format src/
```

## Ключевые концепции

### 1. Command API Architecture

**Файл:** [src/agent/graph.py](src/agent/graph.py)

Используется **LangGraph Command API** для явного управления потоком:

```python
workflow = StateGraph(BrowserAgentState)

# Add all 11 nodes
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tools_node)
workflow.add_node("critical_action_validator", critical_action_validator)
# ... 9 more nodes

# Only entry point - rest via Command
workflow.add_edge(START, "agent")

# Nodes return Command to control flow
def agent_node(state: BrowserAgentState) -> Command:
    if needs_memory_management:
        return Command(update={...}, goto="memory_manager")
    elif is_critical_action:
        return Command(update={...}, goto="critical_action_validator")
    else:
        return Command(update={...}, goto="tools")
```

**Архитектура (простая задача):**

```text
START → agent → tools → agent → goal_validator → END
```

**Архитектура (сложная задача с валидацией):**

```text
START → agent → critical_action_validator → human_in_loop →
tools → progress_analyzer → agent → quality_evaluator →
goal_validator → END
```

**Преимущества:**

- **Явный контроль потока** - каждая нода решает куда идти дальше
- **Легко отлаживать** - видно все переходы в логах
- **Гибкий routing** - можно пропускать ненужные ноды для простых задач
- **Модульность** - каждая нода в отдельном файле

### 2. Browser Tool через MCP

Агент использует **ТОЛЬКО ОДИН инструмент** из @playwright/mcp для всех операций с браузером.

**browser_run_code:**

- Выполнение Playwright кода в браузере
- Формат: `async (page) => { ... }` где `page` - Playwright Page object
- Доступ к полному Playwright Page API

**Фильтрация MCP tools в main.py:**

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

mcp_client = MultiServerMCPClient({
    "browsermcp": {
        "transport": "stdio",
        "command": "npx",
        "args": [
            "-y",
            "@playwright/mcp@latest",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--snapshot-mode",
            "none",
            "--image-responses",
            "omit",
        ],
    }
})

# Получить все MCP tools
all_mcp_tools = await mcp_client.get_tools()

# ФИЛЬТР: Оставить ТОЛЬКО browser_run_code (остальные нестабильны)
mcp_tools = [tool for tool in all_mcp_tools if tool.name == "browser_run_code"]

# Добавить custom tools (HITL)
tools = mcp_tools + [request_user_confirmation]
```

**Playwright Page API включает:**

- Навигация: `page.goto()`, `page.goBack()`, `page.reload()`
- Локаторы: `page.getByRole()`, `page.getByText()`, `page.locator()`
- Действия: `click()`, `fill()`, `press()`, `check()`, `selectOption()`
- Извлечение: `textContent()`, `getAttribute()`, `title()`
- Вкладки: `page.context().pages()`, `newPage()`, `bringToFront()`
- Ожидание: `waitForSelector()`, `waitForLoadState()`, автоматическое ожидание

**Преимущества:**

- ТОЛЬКО ОДИН надежный инструмент вместо множества нестабильных
- Полный контроль через Playwright API
- Автоматическое ожидание элементов (до 30 сек)
- Современные локаторы (accessibility-first: getByRole, getByText)
- MCP сервер запускается автоматически при старте приложения

**Выполнение tools через встроенный ToolNode:**

Проект использует **встроенный `ToolNode`** из `langgraph.prebuilt` с интеллектуальной оберткой:

```python
from langgraph.prebuilt import ToolNode

# Создание ToolNode с автоматической обработкой ошибок
tool_executor = ToolNode(tools, handle_tool_errors=True)

# Выполнение tool calls из AIMessage
result = tool_executor.invoke(state)
```

**Файл:** [src/agent/nodes/tools_node.py](src/agent/nodes/tools_node.py)

**Что делает встроенный ToolNode:**

- Автоматически извлекает `tool_calls` из последнего `AIMessage`
- Выполняет все инструменты (параллельно, если возможно)
- Создает `ToolMessage` для каждого результата
- Обновляет `messages` в state
- С `handle_tool_errors=True` - автоматически ловит исключения и включает их в `ToolMessage`

**Кастомная обертка добавляет:**

- **Интеллектуальное определение ошибок** - анализирует все tool messages (не только последнее)
- **Smart routing** на основе типа ошибки:
  - `stale_ref` → `self_corrector` (автоматическое исправление)
- **Progress tracking** - периодическая проверка прогресса для сложных задач
- **Progress reporting** - автоматические обновления для пользователя

**Пример routing логики:**

```python
def tools_node(state: BrowserAgentState) -> Command:
    # Выполнить все tool calls
    result = tool_executor.invoke(state)
    tool_messages = result["messages"]

    # Проверить все сообщения на ошибки
    error_type, error_message = _detect_errors_in_results(tool_messages)

    if error_type == "stale_ref":
        # Автоматическое исправление
        return Command(update={...}, goto="self_corrector")
    elif error_type != "none":
        # Обработка ошибки с retry
    elif is_complex_task and step % 5 == 0:
        # Анализ прогресса
        return Command(update={...}, goto="progress_analyzer")
    else:
        # Обычный flow
        return Command(update={...}, goto="agent")
```

### 3. State Management

**Файл:** [src/agent/state.py](src/agent/state.py)

Определяет полное состояние агента через TypedDict:

```python
class BrowserAgentState(TypedDict):
    # Core messaging
    messages: Annotated[list[BaseMessage], add_messages]

    # Task metadata
    original_task: str
    current_step: int

    # Validation
    needs_validation: bool
    validation_passed: bool
    requires_human_approval: bool

    # Reflection
    progress_score: float
    error_count: int
    stuck_counter: int

    # Error tracking
    error_type: Optional[Literal["network", "element_not_found", "stale_ref", "auth", "unknown"]]

    # ... и еще 10+ полей
```

**Преимущества:**

- Type safety - все поля типизированы
- Полная картина состояния агента
- Легко добавлять новые поля при расширении

### 4. System Prompt - Modular Architecture

**Директория:** [src/agent/prompts/](src/agent/prompts/)

Проект использует **модульную систему промптов** для гибкости и эффективности.

**ВАЖНО:** Описания tools НЕ дублируются в промптах - они автоматически передаются через `bind_tools()` (OpenAI function calling). Промпты содержат только domain-specific правила и reasoning patterns.

#### Структура модулей

```text
src/agent/prompts/
├── __init__.py              # Экспорты и готовые промпт константы
├── base.py                  # Базовая роль и ReAct loop структура
├── browser_rules.py         # Браузер-специфичные правила (Playwright workflow)
├── playwright_patterns.py   # NEW: Comprehensive Playwright Page API guide
├── error_recovery.py        # Стратегии обработки ошибок (включая Playwright)
└── examples/                # Few-shot reasoning patterns (НЕ синтаксис tools)
    ├── simple.py            # Базовые reasoning паттерны
    └── complex.py           # Сложные decision-making паттерны
```

#### Готовые промпт константы

Файл [\_\_init\_\_.py](src/agent/prompts/__init__.py) экспортирует 3 готовых варианта:

```python
from src.agent.prompts import (
    SYSTEM_PROMPT,          # Стандартный: роль + правила + error recovery + примеры
    SYSTEM_PROMPT_MINIMAL,  # Минимальный: без примеров (экономия токенов)
    SYSTEM_PROMPT_COMPLEX,  # Расширенный: с дополнительными сложными примерами
)
```

**Композиция промптов** использует LangGraph-native подход с `"\n\n".join()`:

```python
# Стандартный промпт (по умолчанию)
# Tools описываются через bind_tools() - не дублируем в промпте
SYSTEM_PROMPT = "\n\n".join([
    BASE_PROMPT,
    BROWSER_RULES,
    PLAYWRIGHT_PATTERNS,  # NEW: Comprehensive Playwright Page API guide
    ERROR_RECOVERY_GUIDE,
])

# Минимальный промпт (25+ шагов) - без Playwright patterns для экономии
SYSTEM_PROMPT_MINIMAL = "\n\n".join([
    BASE_PROMPT,
    BROWSER_RULES,
    ERROR_RECOVERY_GUIDE,
])
```

#### Адаптивный выбор промпта

[agent_node.py](src/agent/nodes/agent_node.py) автоматически выбирает оптимальный промпт на основе состояния:

```python
current_step = state.get("current_step", 0)

if current_step > 25:
    # После 25+ шагов - убрать примеры для экономии токенов
    prompt = SYSTEM_PROMPT_MINIMAL
else:
    # Стандартный полный промпт (с error recovery guide)
    prompt = SYSTEM_PROMPT
```

#### Ключевые элементы

**ReAct Pattern (base.py):**

- Четкое разделение фаз: Reasoning → Acting → Observing
- Критические правила в начале промпта
- Инструкции по завершению задачи

**Tools через bind_tools() - НЕ в промптах:**

- Все tools (MCP и custom) автоматически описываются через `llm.bind_tools(tools)`
- OpenAI function calling передаёт LLM: имя, описание, параметры, схему
- Docstrings функций используются как описания (например, `request_user_confirmation`)
- Промпты НЕ дублируют эту информацию - экономия токенов и гибкость при смене MCP серверов

**Browser Rules (browser_rules.py):**

- Политика управления вкладками с обязательным HITL подтверждением
- Workflow: проверка существующих вкладок → создание новой при необходимости
- Использование `page.context().pages()` для работы с вкладками (0-based индексация)
- Правила использования browser_run_code с Playwright Page API
- Современные локаторы (getByRole, getByText) вместо CSS селекторов

**Playwright Patterns (playwright_patterns.py):**

- Comprehensive справочник по Playwright Page API
- Категории: Навигация, Локаторы, Действия, Извлечение данных, Вкладки
- Ожидание и обработка ошибок
- Best practices и типичные ошибки
- Few-shot примеры для каждой категории операций

**Error Recovery (error_recovery.py):**

- Частые ошибки браузера: network timeout, element not interactive, auth required
- Playwright API ошибки: TimeoutError, Element not visible, Execution context destroyed
- Общий паттерн восстановления после ошибок
- Критерии когда сдаться (3 попытки)

**Few-shot Examples (reasoning-focused):**

- simple.py: Базовые reasoning паттерны (КАК думать, а не КАК вызывать tools)
- complex.py: Сложные decision-making процессы, итеративная логика, error recovery
- Фокус на "Key patterns" вместо конкретного синтаксиса

#### Расширение системы

**Добавление новых MCP tools:**

1. Добавить/обновить MCP сервер - tools автоматически доступны через `bind_tools()`
2. Убедиться что у tool есть хороший docstring (используется для описания)
3. Если нужны domain-specific правила → добавить в `browser_rules.py`
4. Если нужен пример reasoning паттерна → добавить в `examples/`

**Добавление custom tools:**

1. Создать функцию с подробным docstring (What/When/Args/Returns)
2. Декорировать `@tool` из LangChain
3. Добавить в список tools в main.py
4. Промпты обновлять НЕ НУЖНО - docstring используется автоматически

**Создание нового варианта промпта:**

```python
# В prompts/__init__.py
SYSTEM_PROMPT_CUSTOM = "\n\n".join([
    BASE_PROMPT,
    BROWSER_RULES,
    ERROR_RECOVERY_GUIDE,
    # Ваши дополнительные модули (НЕ tools - они через bind_tools)
])
```

**Изменение адаптивной логики:**
Отредактируйте условия в [agent_node.py](src/agent/nodes/agent_node.py) для других триггеров смены промпта.

#### Преимущества подхода "Tools через bind_tools()"

- ✅ **Maintainability** - смена MCP сервера не требует изменений промптов
- ✅ **Token efficiency** - экономия ~800 токенов на каждом запросе (100% сокращение дублирования tools)
- ✅ **Auto-sync** - обновления tools в MCP автоматически доступны агенту
- ✅ **Flexibility** - легко переключаться между различными MCP серверами
- ✅ **Clarity** - промпты фокусируются на domain logic, не на API синтаксисе
- ✅ **Standard** - использует нативный OpenAI function calling механизм

### 5. Node Types

Агент состоит из 11 нод, разделенных по типам:

**Core Nodes (2):**

- `agent` - основное рассуждение и принятие решений
- `tools` - выполнение browser tools через MCP

**Validation Nodes (2):**

- `critical_action_validator` - проверка критических действий перед выполнением
- `goal_validator` - проверка достижения цели задачи

**Reflection Nodes (4):**

- `progress_analyzer` - анализ прогресса выполнения
- `strategy_adapter` - смена стратегии при застревании
- `quality_evaluator` - оценка качества результата
- `self_corrector` - автоматическое исправление типичных ошибок

**Special Nodes (4):**

- `human_in_loop` - запрос подтверждения от пользователя
- `progress_reporter` - логирование progress updates для UI (не добавляет в messages)
- `memory_manager` - сжатие истории сообщений

#### Управление контекстом messages

Не все ноды добавляют сообщения в `messages`. Только те сообщения, которые нужны для LLM reasoning:

**Добавляют в messages (нужны для LLM):**

- `agent` - AIMessage с tool_calls
- `tools` - ToolMessage с результатами выполнения
- `human_in_loop` - HumanMessage с обратной связью пользователя
- `self_corrector` - AIMessage с инструкциями по исправлению
- `strategy_adapter` - AIMessage с новой стратегией
- `quality_evaluator` - AIMessage с feedback (только при низком качестве)
- `goal_validator` - AIMessage с feedback (только если цель не достигнута)
- `memory_manager` - обновленные messages после суммаризации

**НЕ добавляют в messages (только UI):**

- `progress_reporter` - прогресс доступен через state/logs, не засоряет контекст

Это критично для эффективного использования токенов и предотвращения преждевременной суммаризации.

**Пример взаимодействия:**

```python
# Agent node решает что делать
def agent_node(state):
    response = llm.invoke(state["messages"])

    if is_critical(response):
        return Command(goto="critical_action_validator")
    return Command(goto="tools")

# Tools node выполняет и проверяет ошибки
def tools_node(state):
    result = execute_tools(state)

    if error_type == "stale_ref":
        return Command(goto="self_corrector")
    elif error_type:
    return Command(goto="agent")
```

### 6. LLM Client

Используется `langchain-openai.ChatOpenAI` напрямую в [main.py](main.py) с настраиваемым `base_url`.

Работает с любым OpenAI-compatible API:

- OpenAI
- OpenRouter
- Ollama
- LM Studio

**Переключение провайдера:** Измените `LLM_BASE_URL` в `.env`.

### 7. MCP Integration

**Используется официальная библиотека:** `langchain-mcp-adapters`

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

# Подключение к @playwright/mcp через stdio
mcp_client = MultiServerMCPClient({
    "browsermcp": {
        "transport": "stdio",
        "command": "npx",
        "args": [
            "-y",
            "@playwright/mcp@latest",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--snapshot-mode",
            "none",
            "--image-responses",
            "omit",
        ],
    }
})

# Автоматическое получение всех tools
tools = await mcp_client.get_tools()
```

**Особенности:**

- **Автоматический запуск** - MCP сервер запускается при старте приложения через stdio транспорт
- Поддержка **множественных транспортов**: HTTP, stdio
- Поддержка **множественных серверов** одновременно
- Автоматическая конвертация MCP tools в LangChain tools

### 8. CDP Подключение к существующему браузеру

**Как это работает:**

1. Браузер (Edge/Chrome) запускается с флагом `--remote-debugging-port=9222`
2. Это открывает Chrome DevTools Protocol endpoint на порту 9222
3. @playwright/mcp подключается к этому endpoint через `--cdp-endpoint http://127.0.0.1:9222`
4. MCP может управлять уже открытым браузером с вашим профилем

**Преимущества CDP подхода:**

- Работает с вашим обычным браузером и профилем
- Все авторизации и cookies доступны
- Расширения браузера работают
- Можно вручную взаимодействовать с браузером во время работы агента (human-in-the-loop)
- MCP сервер запускается автоматически - не нужно управлять им вручную

**Проверка CDP:**

Откройте `http://localhost:9222/json` - должен вернуться JSON с информацией о браузере.

### 9. Memory Management через LangMem

**Используется официальная библиотека:** `langmem` от LangChain

Проект использует `SummarizationNode` из `langmem.short_term` для автоматической суммаризации истории сообщений.

**Конфигурация в [memory_manager.py](src/agent/nodes/special/memory_manager.py):**

```python
from langmem.short_term import SummarizationNode
from langchain_core.messages.utils import count_tokens_approximately

# Создание модели для суммаризации
summarization_model = llm.bind(max_tokens=256)

# Инициализация SummarizationNode
summarization_node_impl = SummarizationNode(
    token_counter=count_tokens_approximately,
    model=summarization_model,
    max_tokens=4000,                    # Макс. размер истории
    max_tokens_before_summary=3000,     # Порог для суммаризации
    max_summary_tokens=512,             # Макс. размер суммари
    output_messages_key="messages",     # Вывод в messages
)
```

**Особенности:**

- **Токен-ориентированный подход** - суммаризация на основе реального размера, а не количества сообщений
- **Прогрессивная суммаризация** - не пересуммаризирует уже суммированное
- **RunningSummary** - отслеживание состояния между вызовами через `context` в state
- **Автоматический контроль** - SummarizationNode сам решает когда суммаризировать
- **Персистентность** - состояние сохраняется через checkpointer

**Как это работает:**

1. Agent node в [agent_node.py](src/agent/nodes/agent_node.py:45-53) подсчитывает токены в истории через `count_tokens_approximately`
2. При превышении ~2800 токенов роутинг на `memory_manager` ноду
3. Memory manager использует `SummarizationNode` для умной суммаризации:
   - Проверяет порог `max_tokens_before_summary` (3000)
   - Если превышено - суммаризирует старые сообщения, сохраняет свежие
   - Обновляет `context` для отслеживания прогрессивной суммаризации
4. Возвращается в agent node с сжатой историей

**Преимущества LangMem подхода:**

- Сохраняет больше контекста при меньшем размере
- Интеллектуальное объединение похожих сообщений
- Не теряет важную информацию (system prompts, недавние сообщения)
- Адаптивно к разным размерам сообщений

**Настройка параметров:**

Для изменения поведения суммаризации отредактируйте параметры в [memory_manager.py](src/agent/nodes/special/memory_manager.py:32-40):

- `max_tokens` - увеличьте для более длинной истории перед суммаризацией
- `max_tokens_before_summary` - порог когда начинать суммаризацию
- `max_summary_tokens` - размер суммари (больше = больше деталей)

Порог в [agent_node.py](src/agent/nodes/agent_node.py:49) (`2800` токенов) должен быть меньше `max_tokens_before_summary` для своевременного роутинга.

## Расширение функциональности

### Добавление новых нод

Для добавления новой ноды:

1. **Создайте файл ноды:**

   ```python
   # src/agent/nodes/my_new_node.py
   from langgraph.types import Command
   from src.agent.state import BrowserAgentState

   def create_my_new_node(llm):
       def my_new_node(state: BrowserAgentState) -> Command:
           # Ваша логика
           result = process(state)

           # Решите куда идти дальше
           if should_continue:
               return Command(update={"my_field": result}, goto="agent")
           else:

       return my_new_node
   ```

2. **Добавьте экспорт в nodes/**init**.py:**

   ```python
   from src.agent.nodes.my_new_node import create_my_new_node

   __all__ = [..., "create_my_new_node"]
   ```

3. **Зарегистрируйте в graph.py:**

   ```python
   my_new_node = create_my_new_node(llm)
   workflow.add_node("my_new_node", my_new_node)
   ```

4. **Обновите routing в других нодах:**

   ```python
   # В agent_node.py или другой ноде
   if condition:
       return Command(goto="my_new_node")
   ```

5. **Добавьте поля в state.py если нужно:**

   ```python
   class BrowserAgentState(TypedDict):
       # ... existing fields
       my_field: Optional[str]  # Новое поле
   ```

### Модификация существующих нод

Все ноды используют factory pattern - это позволяет легко изменять логику:

**Пример - изменение критериев критических действий:**

```python
# src/agent/nodes/agent_node.py

def _detect_critical_action(message) -> bool:
    """Detect critical/irreversible actions."""
    if not hasattr(message, "tool_calls") or not message.tool_calls:
        return False

    # Добавьте свои критерии
    critical_tools = {
        "delete_element",
        "submit_form",
        "confirm_payment",
        "send_email",        # Новое
        "make_purchase"      # Новое
    }

    return any(tc.get("name") in critical_tools for tc in message.tool_calls)
```

**Пример - изменение логики error detection:**

```python
# src/agent/nodes/tools_node.py

def _detect_errors_in_results(tool_messages: list) -> tuple[str, str | None]:
    """Detect errors in all tool result messages."""
    if not tool_messages:
        return "none", None

    # Проверяем ВСЕ сообщения, не только последнее
    for message in tool_messages:
        if not hasattr(message, "content"):
            continue

        content = str(message.content).lower()

        # Добавьте свои шаблоны ошибок
        if "rate limit" in content:
            return "rate_limit", str(message.content)  # Новый тип
        elif "captcha" in content:
            return "captcha", str(message.content)     # Новый тип
        elif "ref not found" in content or "stale" in content:
            return "stale_ref", str(message.content)
        # ... rest of checks

    return "none", None
```

**Важно:** Функция теперь проверяет **все** tool messages (не только последнее), что важно при параллельном выполнении нескольких инструментов.

### Работа с Browser Operations

**ВАЖНО:** Агент использует **ТОЛЬКО browser_run_code** для всех операций с браузером.

Все операции выполняются через Playwright Page API внутри `browser_run_code`:

```javascript
browser_run_code(code=`async (page) => {
  // Playwright Page API
  await page.goto('https://example.com');
  await page.getByRole('button', { name: 'Submit' }).click();
  return await page.title();
}`)
```

**Доступные операции через Playwright Page API:**

**Навигация:**

- `await page.goto(url)` - переход на URL
- `await page.goBack()` - назад
- `await page.reload()` - перезагрузка

**Локаторы (современные, accessibility-first):**

- `page.getByRole('button', { name: 'Submit' })` - по ARIA роли
- `page.getByText('Click here')` - по видимому тексту
- `page.getByPlaceholder('Email')` - по placeholder
- `page.getByLabel('Username')` - по label
- `page.locator('.selector')` - CSS/XPath (если необходимо)

**Взаимодействие:**

- `await locator.click()` - клик
- `await locator.fill('text')` - ввод текста
- `await locator.press('Enter')` - нажатие клавиши
- `await locator.check()` / `uncheck()` - checkbox
- `await locator.selectOption('value')` - select dropdown

**Извлечение данных:**

- `await locator.textContent()` - текст элемента
- `await locator.getAttribute('href')` - атрибут
- `await page.title()` - заголовок страницы
- `await locator.count()` - количество элементов

**Вкладки:**

- `page.context().pages()` - список всех вкладок (0-based)
- `await context.newPage()` - создать новую
- `await targetPage.bringToFront()` - переключиться

**Для добавления дополнительных возможностей:**

1. Создайте дополнительный MCP сервер с custom tools
2. Подключите его через `MultiServerMCPClient`:

```python
mcp_client = MultiServerMCPClient({
    "browsermcp": {
        "transport": "stdio",
        "command": "npx",
        "args": [
            "-y",
            "@playwright/mcp@latest",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--snapshot-mode",
            "none",
            "--image-responses",
            "omit",
        ],
    },
    "custom": {
        "transport": "stdio",
        "command": "python",
        "args": ["./custom_mcp_server.py"]
    }
})
```

### Human-in-the-Loop уже встроен

Human-in-the-loop реализован через [nodes/special/human_in_loop.py](src/agent/nodes/special/human_in_loop.py) и поддерживает два типа взаимодействий:

**1. Интеллектуальный выбор вкладок (новое):**

Агент автоматически проверяет открытые вкладки и спрашивает пользователя:

```python
# Агент вызывает специальный tool
request_user_confirmation(
    question="Нашел открытую вкладку #2 с Gmail. Использовать её или открыть новую?",
    options=["использовать существующую", "открыть новую"]
)

# tools_node детектирует HITL запрос и роутит на human_in_loop
# human_in_loop показывает вопрос пользователю через interrupt()
# Ответ возвращается агенту для продолжения работы
```

**Преимущества:**

- Защита закрепленных вкладок от случайных изменений
- Пользователь контролирует использование существующих вкладок
- Автоматическое создание новых вкладок когда подходящих нет

**2. Подтверждение критических действий:**

```python
# Нода автоматически вызывается для критических действий
def human_in_loop(state: BrowserAgentState) -> Command:
    action = state.get("pending_action")

    # interrupt() приостанавливает выполнение
    user_response = interrupt({
        "type": "confirmation",
        "message": f"About to execute: {action}. Proceed?",
        "options": ["yes", "no"]
    })

    if user_response == "yes":
        return Command(update={"validation_passed": True}, goto="tools")

    return Command(
        update={"messages": [feedback]},
        goto="agent"
    )
```

**CLI автоматически обрабатывает interrupts:**

```python
# src/ui/cli.py
async for chunk in agent.astream(initial_state, config):
    if "__interrupt__" in chunk:
        interrupt_data = chunk["__interrupt__"][0]
        _handle_interrupt(interrupt_data, agent, config)
```

## Отладка

### Логирование нод

Каждая нода логирует свои решения через `src.utils.logger`:

```python
# src/agent/nodes/agent_node.py
logger = setup_logger(__name__)

def agent_node(state: BrowserAgentState) -> Command:
    logger.info(f"Agent reasoning at step {state.get('current_step')}")

    if is_critical:
        logger.warning("Detected critical action - routing to validator")
        return Command(goto="critical_action_validator")
```

**Смотрите логи для отладки:**

- Какая нода куда роутит
- Почему принято то или иное решение
- Какие ошибки обнаружены

### Debug mode для LLM

```python
# main.py
llm = ChatOpenAI(
    api_key=config.llm_api_key,
    base_url=config.llm_base_url,
    model=config.llm_model,
    temperature=config.llm_temperature,
    streaming=False,
    verbose=True,  # Добавить для логирования всех запросов
)
```

### Визуализация потока

LangGraph автоматически логирует переходы между нодами:

```text
2026-01-15 - src.agent.graph - INFO - Agent created with 11 nodes
2026-01-15 - src.agent.nodes.agent_node - INFO - Agent reasoning at step 0
2026-01-15 - src.agent.nodes.agent_node - INFO - Routing to: tools
2026-01-15 - src.agent.nodes.tools_node - INFO - Executing tools
2026-01-15 - src.agent.nodes.tools_node - INFO - Tools succeeded - routing to: agent
2026-01-15 - src.agent.nodes.agent_node - INFO - No more tool calls - routing to: goal_validator
2026-01-15 - src.agent.nodes.validation.goal_validator - INFO - Goal achieved - routing to: END
```

### Инспекция MCP команд

```python
# main.py - добавить после создания mcp_client
import logging

mcp_logger = logging.getLogger("langchain_mcp_adapters")
mcp_logger.setLevel(logging.DEBUG)
```

## Известные проблемы

### 1. CDP подключение теряется

**Проблема:** Если закрыть браузер или перезапустить его, MCP теряет подключение.

**Решение:**

- Перезапустите приложение (MCP сервер перезапустится автоматически)
- Убедитесь что браузер запущен с `--remote-debugging-port=9222`
- Проверьте что порт 9222 доступен: `http://localhost:9222/json`

### 2. LLM теряет контекст на длинных задачах

**Проблема:** История сообщений становится слишком длинной.

**Решение:**

- Встроенная нода `memory_manager` использует LangMem `SummarizationNode` для автоматической суммаризации
- Токен-ориентированный подход: триггер при ~2800 токенов в [agent_node.py](src/agent/nodes/agent_node.py:49)
- Настройка порогов в [memory_manager.py](src/agent/nodes/special/memory_manager.py:32-40)
- Прогрессивная суммаризация сохраняет важный контекст

### 3. Браузер не запускается с debugging портом

**Проблема:** Браузер уже запущен и занимает профиль.

**Решение:**

- Закройте ВСЕ окна браузера
- Запустите через ярлык с CDP флагом
- Если не помогает - завершите процесс через Task Manager

## Conventions

### Code Style

- Python 3.11+ features
- Type hints везде где возможно
- Async/await для I/O операций
- Docstrings в Google style

### Naming

- `snake_case` для функций и переменных
- `PascalCase` для классов
- `UPPER_CASE` для констант
- Префикс `_` для private members

### Error Handling

- Логировать все ошибки
- Возвращать понятные сообщения пользователю
- Не падать на первой ошибке - пробовать альтернативы

## Contribution Guidelines

1. Создайте feature branch
2. Убедитесь что линтер проходит (`uv run ruff check src/`)
3. Обновите документацию
4. Создайте PR с описанием изменений

## Roadmap

### Завершено ✅

- [x] CDP подключение к существующему браузеру
- [x] Работа с пользовательским профилем Edge
- [x] Command API architecture с модульными нодами
- [x] Validation нод (critical actions, goal validation)
- [x] Reflection нод (progress analysis, strategy adaptation, quality evaluation, self-correction)
- [x] Special нод (human-in-the-loop, error recovery, progress reporting, memory management)
- [x] Type-safe state management
- [x] Interrupt handling в CLI

### Ближайшие улучшения

- [ ] Streaming поддержка для LLM ответов
- [ ] Metrics и мониторинг производительности
- [ ] Подключение дополнительных MCP серверов (файлы, база данных)
- [ ] Graceful reconnection при потере CDP подключения

### Долгосрочные цели

- [ ] Multi-tab/multi-window поддержка
- [ ] Vision capabilities (анализ скриншотов)
- [ ] Персистентная память задач
- [ ] Web UI вместо CLI
- [ ] Distributed execution для параллельных задач
