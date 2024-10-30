set dotenv-load

run:
    uvicorn app.main:app --reload

migrate:
    python -m app.database migrate

new-migration name:
    #!/usr/bin/env bash
    timestamp=$(date +%Y%m%d_%H%M%S)
    touch "migrations/${timestamp}_${name}.sql"

