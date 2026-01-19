# Browser Copilot - Project Overview

## Purpose
AI-агент для автономного управления веб-браузером на базе LangGraph и @playwright/mcp. Агент может выполнять сложные многошаговые задачи в браузере, такие как работа с почтой, заказ еды, поиск вакансий.

## Tech Stack
- **Python**: 3.11+
- **LangChain/LangGraph**: Агентный framework с Command API
- **OpenAI API**: Работает с любым OpenAI-compatible API (OpenRouter, Ollama, etc.)
- **MCP (Model Context Protocol)**: Интеграция через langchain-mcp-adapters
- **@playwright/mcp**: Браузерная автоматизация через CDP (автозапуск)
- **Rich**: CLI interface
- **Pydantic**: Configuration management

## Architecture
```
User CLI → LangGraph Agent → LLM → High-Level Browser Tools → BrowserExecutor → MCP → Browser (CDP)
```

### Key Components

1. **High-Level Browser Tools** (src/agent/tools/)
   - 20 tools с инкапсулированным Playwright кодом
   - LLM только выбирает tool и параметры, НЕ пишет код
   - Smart Target Format: CSS, role:name, text:, placeholder:, label:, testid:
   - Tab Selection Workflow встроен в browser_navigate
   - BrowserExecutor singleton хранит ссылку на MCP tool

2. **LangGraph Agent** (src/agent/graph.py)
   - Command API для явного управления потоком
   - Модульные ноды (agent, tools, validation, reflection, special)

3. **Minimal System Prompts** (src/agent/prompts/)
   - playwright_patterns.py УДАЛЁН (~1800 строк)
   - browser_rules.py упрощён до ~55 строк
   - Tools описываются через bind_tools()

4. **CDP Connection**
   - Подключение к существующему браузеру с профилем пользователя
   - Все авторизации и cookies сохранены

## Browser Tools (20 + 1 HITL)

| Категория | Tools |
|-----------|-------|
| Навигация | browser_navigate |
| Вкладки | browser_list_tabs, browser_switch_tab |
| Взаимодействие | browser_click, browser_fill, browser_press_key, browser_select, browser_hover, browser_check |
| Извлечение | browser_get_text, browser_get_attribute, browser_get_page_info |
| Ожидание | browser_wait_for, browser_wait_for_load |
| Специальные | browser_close_modal, browser_scroll, browser_screenshot, browser_go_back, browser_reload |
| Fallback | browser_run_custom |
| HITL | request_user_confirmation |
