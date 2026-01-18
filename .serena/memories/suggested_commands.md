# Suggested Commands

## Development Commands

### Installation
```bash
# Install dependencies (uses uv)
uv sync

# Add new dependency (DO NOT edit pyproject.toml manually)
uv add <package-name>

# Add dev dependency
uv add <package-name> --group dev
```

### Running the Application

**Prerequisites:**
1. Start browser with CDP:
   - Use shortcut with: `--remote-debugging-port=9222`

**Run the agent:**
```bash
uv run python main.py
```

### Linting and Formatting
```bash
# Check code style
uv run ruff check src/

# Auto-fix issues
uv run ruff check --fix src/

# Format code
uv run ruff format src/
```

### Debugging
```bash
# Enable debug logging (in .env file)
LOG_LEVEL=DEBUG

# MCP server logs are automatically shown in application console

# Check CDP endpoint
# Open in browser: http://localhost:9222/json
```

## System Commands (Windows)

### File Operations
```powershell
# List directory
dir
ls  # if PowerShell

# Find files
Get-ChildItem -Recurse -Filter "*.py"

# Search in files
Select-String -Path "*.py" -Pattern "pattern"
```

### Process Management
```powershell
# Check if port is in use
netstat -ano | findstr :3000
netstat -ano | findstr :9222

# Kill process by port
# Find PID from netstat, then:
taskkill /PID <pid> /F
```

### Git Commands
```bash
git status
git add .
git commit -m "feat: description"
git push
```
