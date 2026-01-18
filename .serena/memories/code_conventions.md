# Code Style and Conventions

## General Python Style
- Follow PEP 8
- Python 3.11+ features
- Type hints everywhere (required for function signatures)
- Docstrings in Google style
- Use `pathlib.Path` instead of `os.path`

## Naming Conventions
- `snake_case` for functions and variables
- `PascalCase` for classes
- `UPPER_CASE` for constants
- Prefix `_` for private members

## Import Order
All imports MUST be at the top of the file:
1. Standard library imports
2. Third-party imports
3. Local application imports

## Async/Await
Use async/await for all I/O operations (LLM calls, MCP calls, file operations)

## Error Handling
- Log all errors with logger
- Return user-friendly messages
- Don't crash on first error - try alternatives
- Use specific exception types

## Type Hints
Required for all function signatures:
```python
def create_agent(llm: ChatOpenAI, tools: list) -> CompiledGraph:
    """..."""
```

## Docstrings
Use Google style:
```python
def function(arg1: str, arg2: int) -> bool:
    """
    Short description.

    Longer description if needed.

    Args:
        arg1: Description
        arg2: Description

    Returns:
        Description

    Example:
        >>> function("test", 1)
        True
    """
```
