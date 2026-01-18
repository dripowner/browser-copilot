# Task Completion Checklist

When a coding task is completed, perform these checks:

## 1. Code Quality
- [ ] All functions have type hints
- [ ] All functions have docstrings
- [ ] Code follows naming conventions (snake_case, PascalCase, UPPER_CASE)
- [ ] Imports are organized correctly (stdlib, third-party, local)
- [ ] No unused imports
- [ ] All python imports are at the top of the file

## 2. Linting and Formatting
- [ ] Run `uv run ruff check src/` - should pass
- [ ] Run `uv run ruff format src/` - should format correctly
- [ ] Fix any linting errors

## 3. Documentation
- [ ] Update CLAUDE.md if architecture or commands changed
- [ ] Update README.md if user-facing features changed
- [ ] Add code examples in docstrings for complex functions

## 4. Integration Testing
- [ ] Test the agent end-to-end with a simple task
- [ ] Ensure MCP server connection works
- [ ] Verify LLM integration works
- [ ] Check that browser tools execute correctly

## 5. Git Commit
- [ ] Use Conventional Commits format: `type(scope): description`
- [ ] Types: feat, fix, docs, refactor, test, chore
- [ ] Example: `feat(agent): add validation nodes for critical actions`

## 6. Known Issues to Check
- [ ] Accessibility tree not too large (filter if needed)
- [ ] CDP connection stable
- [ ] No memory leaks in long conversations
- [ ] Error handling for "Ref not found" errors
