# Just file for common development tasks

# List all available commands
default:
    @just --list

# Install development dependencies
install:
    uv pip install -e ".[dev]"

# Run tests
test:
    pytest tests/ -v

# Run the development server
dev:
    uvicorn app.main:app --reload

# Create initial migration
init-db:
    python -c "from app.main import create_db_and_tables; create_db_and_tables()"
