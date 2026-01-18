# Project Structure

```
browser-copilot/
├── main.py                      # Entry point
├── pyproject.toml               # Dependencies (managed by uv)
├── uv.lock                      # Lock file
├── .env                         # Environment variables (not in git)
├── .env.example                 # Example env file
├── README.md                    # User documentation
├── CLAUDE.md                    # Development guide
├── config/
│   └── .env.example             # Example configuration
├── src/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py             # LangGraph agent creation (custom ReAct)
│   │   └── prompts.py           # System prompt with planning requirements
│   ├── ui/
│   │   ├── __init__.py
│   │   └── cli.py               # Rich-based CLI interface
│   └── utils/
│       ├── __init__.py
│       ├── config.py            # Pydantic configuration loader
│       └── logger.py            # Logging setup
## Key Files

### main.py
- Application entry point
- Initializes LLM, MCP client, and agent
- Handles top-level error handling
- Starts CLI loop

### src/agent/graph.py
- **Critical file**: Contains custom ReAct agent implementation
- Uses StateGraph with MessagesState
- Defines nodes: agent (reasoning), tools (action execution)
- Defines edges: START → agent → [conditional] → tools → agent → END
- Uses conditional_edges with should_continue function

### src/agent/prompts.py
- System prompt for LLM
- **Critical**: Enforces planning before execution
- Contains examples of planning for simple and complex tasks
- Instructions for tool usage and error handling

### src/ui/cli.py
- Rich-based interactive CLI
- Input loop for user queries
- Result formatting and display
- Help command with examples

### src/utils/config.py
- Pydantic-based configuration
- Loads from .env file
- Validates required fields (LLM API key, MCP URL, etc.)

### src/utils/logger.py
- Centralized logging setup
- Configurable log level via .env
- Formatted output for debugging
