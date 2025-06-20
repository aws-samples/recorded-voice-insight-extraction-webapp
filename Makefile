# Run unit tests
test:
	pytest -m "unit"

# Run both linting and formatting in one command
lint: 
	ruff-lint format
# Run linting checks and fix issues automatically
ruff-lint: 
	ruff check --fix --exclude=notebooks
# Format code according to project standards
format: 
	ruff format