# Project Structure

```
browser-copilot/
├── main.py                      # Entry point
├── pyproject.toml               # Dependencies (managed by uv)
├── uv.lock                      # Lock file
├── .env                         # Environment variables (not in git)
├── config/
│   └── .env.example             # Example configuration
├── README.md                    # User documentation
├── CLAUDE.md                    # Development guide
├── src/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py             # LangGraph agent creation (Command API)
│   │   ├── state.py             # BrowserAgentState definition
│   │   ├── tools/               # High-level browser tools (NEW)
│   │   │   ├── __init__.py          # get_browser_tools() export
│   │   │   ├── _executor.py         # BrowserExecutor singleton
│   │   │   ├── _templates.py        # JS helpers (cleanText, async wrapper)
│   │   │   ├── _selectors.py        # Smart target parsing
│   │   │   ├── navigation.py        # browser_navigate
│   │   │   ├── tabs.py              # browser_list_tabs, browser_switch_tab
│   │   │   ├── extraction.py        # browser_get_text, browser_get_attribute, browser_get_page_info
│   │   │   ├── interaction.py       # browser_click, browser_fill, etc.
│   │   │   ├── waiting.py           # browser_wait_for, browser_wait_for_load
│   │   │   ├── special.py           # browser_close_modal, browser_scroll, etc.
│   │   │   ├── fallback.py          # browser_run_custom
│   │   │   └── user_confirmation.py # request_user_confirmation (HITL)
│   │   ├── prompts/             # System prompts (modular)
│   │   │   ├── __init__.py          # SYSTEM_PROMPT export
│   │   │   ├── base.py              # Base role and ReAct structure
│   │   │   ├── browser_rules.py     # Minimal browser rules (~55 lines)
│   │   │   └── error_recovery.py    # Error handling strategies
│   │   └── nodes/               # Modular nodes (Command-based routing)
│   │       ├── agent_node.py        # Core reasoning
│   │       ├── tools_node.py        # Tool execution
│   │       ├── validation/
│   │       ├── reflection/
│   │       └── special/
│   ├── ui/
│   │   └── cli.py               # Rich-based CLI interface
│   └── utils/
│       ├── config.py            # Pydantic configuration loader
│       └── logger.py            # Logging setup

## Key Files

### main.py
- Application entry point
- Initializes LLM, MCP client, BrowserExecutor, and agent
- Gets browser_run_code from MCP for internal use (LLM doesn't see it)
- Uses get_browser_tools() for high-level tools

### src/agent/tools/
- **NEW: High-level browser tools** that encapsulate Playwright code
- LLM only selects tool and parameters, doesn't write code
- 20 browser tools + 1 HITL tool
- BrowserExecutor singleton holds MCP tool reference
- Smart target format: CSS, role:name, text:, placeholder:, label:, testid:

### src/agent/graph.py
- Uses StateGraph with BrowserAgentState
- Command API for explicit flow control
- Nodes return Command(goto="next_node")

### src/agent/prompts/
- Modular prompt system
- playwright_patterns.py REMOVED - code now in tools
- browser_rules.py simplified to ~55 lines
- Tools described via bind_tools(), not in prompts
```
