Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

# IReVIEW Tests

This directory contains tests for the ReVIEW application, organized into unit tests and integration tests.

## Testing Requirements for Developers

**Important:** All new features must include appropriate unit tests. This is a mandatory requirement for code contributions.

### Why Tests Are Required
- Ensures code quality and reliability
- Prevents regressions when making changes
- Serves as documentation for how components should work
- Enables safe refactoring and optimization
- Validates that features meet requirements

### Using AI Coding Agents for Test Generation

You can use AI Coding Agents like Amazon Q to help generate tests for your code:

1. **Reference the AmazonQ.md file**: Ensure the AI agent has access to the `AmazonQ.md` file in the project `.amazonq/rules` directory, which contains specific guidelines for test creation in this project.

2. **Test Generation Best Practices**:
   - Provide the AI with the code you want to test
   - Specify whether you need unit or integration tests
   - Ask the AI to follow the project's test structure and conventions
   - Review and validate the generated tests before committing

3. **Example Prompt for Amazon Q**:
   ```
   Generate unit tests for this file: relate/path/to/your/file.py.
   ```

4. **Always Verify AI-Generated Tests**: While AI can help create test scaffolding, always review and verify that:
   - Tests actually validate the expected behavior
   - Edge cases are properly covered
   - Tests follow project conventions
   - Tests are properly marked with the correct decorators


### Before Creating a Pull Request
1. Write appropriate unit tests for your new code (manually or with AI assistance)
2. Run tests locally to verify they pass:
   ```bash
   cd {REPO_BASE_DIR}
   make test
   ```
3. Fix any failing tests before submitting your PR
4. Ensure your code meets the coverage requirements

## Test Structure

- `unit/`: Contains unit tests that don't require external services
- `integration/`: Contains integration tests that may require external services or resources
- `conftest.py`: Shared pytest fixtures for all tests

## Running Tests

### Default Behavior

By default, running `pytest` will execute all tests **except** integration tests. This is configured in the `pytest.ini` file with the `addopts = -m "not integration"` setting.

### Running All Tests

To run all tests (both unit and integration):

```bash
cd {REPO_BASE_DIR}
pytest -m ""  # Override the default filter
```

### Running Only Unit Tests

To run only unit tests (this is the default):

```bash
cd {REPO_BASE_DIR}
pytest
```

Or explicitly:

```bash
cd {REPO_BASE_DIR}
pytest -m "unit"
```

Or by directory:

```bash
cd {REPO_BASE_DIR}
pytest tests/unit
```

### Running Only Integration Tests

To run only integration tests:

```bash
cd {REPO_BASE_DIR}
pytest -m "integration"
```

Or by directory:

```bash
cd {REPO_BASE_DIR}
pytest tests/integration
```

## Adding New Tests

### Unit Tests

Add new unit tests to the `tests/unit` directory. Unit tests should:
- Be marked with the `@pytest.mark.unit` decorator
- Be fast and not depend on external services
- Test individual components in isolation
- Use mocks for external dependencies

Example:

```python
# tests/unit/test_example.py
import pytest

@pytest.mark.unit
def test_my_function():
    # Test implementation here
    assert True
```

### Integration Tests

Add new integration tests to the `tests/integration` directory. Integration tests should:
- Be marked with the `@pytest.mark.integration` decorator
- Test interactions between components or with external services
- Include proper setup and teardown of test resources

Example:

```python
# tests/integration/test_example.py
import pytest

@pytest.mark.integration
def test_my_integration():
    # Integration test implementation here
    assert True
```

## Test Configuration

The `pytest.ini` file in the root directory defines:
- Markers for categorizing tests:
  - `unit`: For unit tests
  - `integration`: For integration tests
- Default options to exclude integration tests

## Fixtures

Shared test fixtures are defined in `conftest.py`. These fixtures are available to all tests.

To add a new fixture:

```python
# conftest.py
import pytest

@pytest.fixture
def my_fixture():
    # Setup code
    data = {"key": "value"}
    yield data
    # Teardown code (if needed)
```