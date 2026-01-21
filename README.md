# Townhall Document Management System

A cloud-based document management system to digitize city hall operations, eliminating paper use.

## Features

- Digital document management across departments
- Role-based access control (Admin, Department Head, Employee)
- Document forwarding and routing between departments
- Complete audit trail for compliance
- In-app and email notifications
- File attachment support with GridFS
- RESTful API with Swagger UI documentation

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Authentication**: JWT with bcrypt
- **API Documentation**: Swagger UI + ReDoc
- **Package Manager**: Poetry
- **Containerization**: Docker/Docker Compose

## Installation

### Prerequisites

- Python 3.11+
- Poetry
- Docker & Docker Compose
- MongoDB

### Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   poetry install
   ```

3. Copy environment variables:
   ```bash
   cp .env.example .env
   ```

4. Start services with Docker:
   ```bash
   docker-compose up -d
   ```

5. Run database migrations/seeds:
   ```bash
   poetry run python -m app.db.migrations.seed_data
   ```

6. Start the development server:
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

## API Documentation

Once the server is running, access the interactive API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Project Structure

```
townhall-panel/
├── app/
│   ├── api/              # API endpoints
│   ├── core/             # Security, permissions, config
│   ├── db/               # Database connections and repositories
│   ├── models/           # Data models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   └── utils/            # Utilities and helpers
├── tests/                # Test suite
├── docker-compose.yml    # Docker configuration
├── Dockerfile            # Application container
└── pyproject.toml        # Python dependencies
```

## Development

### Running Tests

```bash
poetry run pytest
```

### Code Formatting

```bash
poetry run black app tests
poetry run ruff check app tests
```

### Type Checking

```bash
poetry run mypy app
```

## License

Proprietary - All rights reserved
