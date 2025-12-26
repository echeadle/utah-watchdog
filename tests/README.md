# Tests

This directory contains test files for the utah-watchdog project.

## Running Tests

Run all tests:
```bash
uv run pytest
```

Run a specific test file:
```bash
uv run pytest tests/test_congress_members.py
```

Run a specific test:
```bash
uv run pytest tests/test_congress_members.py::TestCongressMembersIngester::test_transform_senate_member
```

Run with verbose output:
```bash
uv run pytest -v
```

Run with coverage report:
```bash
uv run pytest --cov=src --cov-report=html
```

## Test Structure

- `test_congress_members.py` - Tests for the CongressMembersIngester class

## Writing Tests

- Use `pytest` for all new tests
- Use `pytest-asyncio` for testing async code
- Mock external dependencies (HTTP requests, database calls) to avoid requiring API keys or database connections
- Follow the existing test patterns in the test files

## Test Coverage

The tests for `congress_members.py` cover:
- Initialization with and without filters
- Chamber extraction from member data
- Transformation of Senate and House members
- Party mapping (Republican, Democrat, Independent)
- Contact information extraction from detailed data
- Error handling (missing bioguide_id, HTTP errors, 404 responses)
- Database operations (insert, update, marking old members out of office)
- State and chamber filtering during data fetching
- Full sync pipeline execution
