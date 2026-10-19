# SecondRoute Backend

FastAPI backend for SecondRoute - Decision engine for returned electronics.

## Development

```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .
ruff format --check .

# Run type checking
mypy .

# Run database migrations
alembic upgrade head
```