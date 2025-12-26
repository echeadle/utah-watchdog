# Manual Tests & Investigation Scripts

This directory contains manual test scripts and investigation utilities for debugging and exploring the utah-watchdog system.

## Manual Test Scripts

These scripts are for manual/integration testing and are **not** part of the automated pytest suite:

### Agent Testing

- **test_agent.py** - Comprehensive test suite for the research agent
  ```bash
  # Run all predefined test queries
  uv run python scripts/manual_tests/test_agent.py

  # Interactive mode
  uv run python scripts/manual_tests/test_agent.py --interactive

  # Test a single query
  uv run python scripts/manual_tests/test_agent.py --query "Who is Mike Lee?"
  ```

- **test_tool_calling.py** - Verify Pydantic AI tool calling works
  ```bash
  uv run python scripts/manual_tests/test_tool_calling.py
  ```

- **test_research_direct.py** - Direct testing of research functionality
  ```bash
  uv run python scripts/manual_tests/test_research_direct.py
  ```

- **test_force_tools.py** - Test forcing tool usage in agent
  ```bash
  uv run python scripts/manual_tests/test_force_tools.py
  ```

## Investigation Scripts

These scripts were used to investigate and debug specific issues:

- **investigate_member_list.py** - Debug Congress member API responses
- **investigate_senators.py** - Investigate senator data fetching
- **investigate_without_filter.py** - Test fetching without filters

## Difference from Automated Tests

The scripts in this directory differ from the automated test suite in `tests/`:

| Manual Tests (this directory) | Automated Tests (`tests/`) |
|-------------------------------|----------------------------|
| Run manually as standalone scripts | Run via pytest framework |
| Interactive and exploratory | Automated assertions |
| Print output for human review | Pass/fail via assertions |
| Integration testing | Unit testing with mocks |
| Useful for debugging | Useful for CI/CD |

## When to Use

Use these manual test scripts when you need to:
- Debug agent behavior interactively
- Explore API responses manually
- Test end-to-end functionality with real data
- Investigate specific issues or edge cases

For automated testing and CI/CD, use the pytest suite in the `tests/` directory instead.
