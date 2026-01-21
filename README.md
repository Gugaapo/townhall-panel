# Townhall Document Management System

A FastAPI-based document management system for city hall operations with MongoDB, role-based access control, and admin panel.

## Requirements

- Docker & Docker Compose

## Installation & Running

```bash
# Clone the repository
git clone https://github.com/Gugaapo/townhall-panel.git
cd townhall-panel

# Copy environment variables
cp .env.example .env

# Start all services
docker compose up -d

# Seed the database (first time only)
docker compose exec api poetry run python -m app.db.migrations.seed_data
```

## Access

| Service | URL |
|---------|-----|
| API | http://localhost:8002 |
| Swagger UI | http://localhost:8002/docs |
| Admin Panel | http://localhost:8002/admin |
| Mongo Express | http://localhost:8082 |

**Default admin credentials:** admin@townhall.com / admin123

## Development (without Docker)

```bash
# Install Poetry
pip install poetry

# Install dependencies
poetry install

# Run development server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Requires a running MongoDB instance configured in `.env`.
