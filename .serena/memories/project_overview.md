# Browser Copilot - Project Overview

## Purpose
AI-агент для автономного управления веб-браузером на базе LangGraph и chrome-devtools-mcp. Агент может выполнять сложные многошаговые задачи в браузере, такие как работа с почтой, заказ еды, поиск вакансий.

## Tech Stack
- **Python**: 3.11+
- **LangChain/LangGraph**: Агентный framework с custom ReAct циклом
- **OpenAI API**: Работает с любым OpenAI-compatible API (OpenRouter, Ollama, etc.)
- **MCP (Model Context Protocol)**: Интеграция через langchain-mcp-adapters
- **chrome-devtools-mcp**: Браузерная автоматизация через CDP (автозапуск)
- **Rich**: CLI interface
- **Pydantic**: Configuration management

## Architecture
```
User CLI → LangGraph Agent → LLM → Browser Tools → MCP Client → chrome-devtools-mcp (auto) → Browser (CDP)
```

### Key Components
1. **LangGraph ReAct Agent** (src/agent/graph.py) - custom StateGraph с явным Thought-Action-Observation циклом
2. **Planning Prompt** (src/agent/prompts.py) - system prompt требующий планирования перед выполнением
3. **MCP Integration** - автоматическое получение tools из MCP сервера
4. **CDP Connection** - подключение к существующему Edge браузеру с пользовательским профилем
