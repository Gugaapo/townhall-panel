# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Townhall Document Management System - A cloud-based FastAPI application to digitize city hall operations. The system manages document workflows between departments with role-based access control, complete audit trails, and notification systems.

**Current Status**: Phase 4 complete (50% of MVP). 41 operational API endpoints with full documentation.

## Development Commands

### Running the Application

```bash
# Start all services (MongoDB, API, Mongo Express)
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down
```

**Access Points**:
- API: http://localhost:8002
- Swagger UI: http://localhost:8002/docs
- ReDoc: http://localhost:8002/redoc
- Mongo Express: http://localhost:8082 (requires `--profile dev`)

**Default Credentials**: admin@townhall.com / admin123

### Database Operations

```bash
# Seed initial data (admin user, departments)
poetry run python -m app.db.migrations.seed_data

# Create database indexes
poetry run python -m app.db.migrations.create_indexes
```

### Testing & Quality

```bash
# Run tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_auth_api.py

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Code formatting
poetry run black app tests

# Linting
poetry run ruff check app tests

# Type checking
poetry run mypy app
```

### Local Development (without Docker)

```bash
# Install dependencies
poetry install

# Run development server with hot reload
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Architecture Overview

### Three-Tier Architecture

**1. API Layer** (`app/api/v1/endpoints/`): FastAPI routers with inline business logic
- Authentication in endpoints (JWT via `require_authenticated` dependency)
- Minimal service layer (only for cross-cutting concerns like notifications)
- Direct repository calls from endpoints

**2. Repository Layer** (`app/db/repositories/`): Data access with BaseRepository pattern
- All repositories extend `BaseRepository` (generic CRUD operations)
- Collection names centralized in `app/db/mongodb.py::Collections`
- Async operations using Motor (MongoDB async driver)

**3. Schema Layer** (`app/schemas/`): Pydantic v2 models
- Three-tier pattern: Base → Create → Response
- Base: Common fields
- Create: Fields required for creation (inherits Base)
- Response: Fields returned from API (includes id, timestamps)

### Key Patterns

**Repository Pattern**:
```python
class DocumentRepository(BaseRepository):
    def __init__(self):
        super().__init__(Collections.DOCUMENTS)

    async def custom_query(self, ...):
        # Specialized query methods
```

**Schema Pattern**:
```python
class DocumentBase(BaseModel):
    title: str
    description: str

class DocumentCreate(DocumentBase):
    creator_id: str

class DocumentResponse(DocumentBase):
    id: str = Field(alias="_id")
    created_at: datetime
```

**Permission Decorators**:
```python
@router.get("/endpoint")
async def endpoint(current_user: dict = Depends(require_admin)):
    # Admin only

async def endpoint(current_user: dict = Depends(require_department_head)):
    # Admin or Department Head

async def endpoint(current_user: dict = Depends(require_authenticated)):
    # Any authenticated user
```

## MongoDB Collections

**Core Collections**:
- `users` - User accounts with role-based permissions
- `departments` - Organizational units (main/regular types)
- `documents` - Document records with embedded file references
- `document_history` - Audit trail (denormalized user names for integrity)
- `notifications` - In-app notifications with email tracking

**GridFS Collections** (automatic):
- `fs.files` - File metadata
- `fs.chunks` - File content chunks

## Document Number Generation

Format: `{YEAR}-{DEPT_CODE}-{SEQUENCE}`

Example: `2025-EDU-00123`

Auto-generated in `DocumentRepository.generate_document_number()` with atomic counters per department/year.

## Role-Based Access Control

**Admin** (`UserRole.ADMIN`):
- Full system access
- View/manage all departments and documents
- User management across all departments

**Department Head** (`UserRole.DEPARTMENT_HEAD`):
- Manage users in own department
- View/manage all department documents
- Forward documents to other departments

**Employee** (`UserRole.EMPLOYEE`):
- View documents assigned to department
- Create new documents
- Respond to assigned documents

## Document Lifecycle

**Status Flow**:
```
draft → pending → in_progress → completed → archived
```

**Key Operations**:
- **Create**: Creator can assign to department/user
- **Forward**: Transfer document between departments (triggers notifications)
- **Respond**: Add responses tracked in document history
- **Status Change**: Requires reason/comment
- **Archive**: Makes document read-only

## Notification System

**Trigger Points** (5 locations in `documents.py`):
1. Document creation → Notify assigned user
2. Document forwarding → Notify target department users
3. Status change → Notify creator + assigned user
4. Assignment change → Notify new assignee
5. (Optional) Archival

**Email Handling**:
- Async via FastAPI `BackgroundTasks`
- Graceful degradation if SMTP not configured
- HTML templates with inline CSS in `EmailService`

**Error Isolation**: Notification failures NEVER block document operations (try-except with logging).

## ObjectId Handling

MongoDB uses `ObjectId` for IDs. Always convert before API responses:

```python
def convert_ids(doc: dict) -> dict:
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    if "user_id" in doc and isinstance(doc["user_id"], ObjectId):
        doc["user_id"] = str(doc["user_id"])
    return doc
```

## Configuration

All settings in `app/config.py` using Pydantic Settings:
- Loaded from `.env` file or environment variables
- Includes MongoDB, JWT, SMTP, CORS, file upload limits
- Access via `from app.config import settings`

**Docker Port Mappings**:
- MongoDB: Host 27018 → Container 27017
- API: Host 8002 → Container 8000
- Mongo Express: Host 8082 → Container 8081

## Database Indexes

28 indexes across 5 collections for performance (see `app/db/migrations/create_indexes.py`):
- Users: email (unique), department_id
- Documents: document_number (unique), status, creator_id, department IDs, created_at
- Document History: document_id + timestamp (compound), performed_by
- Notifications: user_id + is_read (compound), created_at, document_id

## API Documentation

FastAPI auto-generates OpenAPI documentation:
- Endpoints organized by tags (Authentication, Users, Departments, Documents, Files, Notifications, Dashboard)
- Request/response schemas with examples
- OAuth2 password flow for testing authenticated endpoints
- Click "Authorize" button in Swagger UI after login

## Common Gotchas

1. **Poetry --no-dev deprecated**: Use `poetry install --without dev --no-root` in Dockerfile
2. **libmagic1 required**: python-magic package needs system library (added in Dockerfile)
3. **Port conflicts**: This project uses non-standard ports (8002, 27018) to avoid conflicts
4. **ObjectId serialization**: Always convert ObjectIds to strings before JSON responses
5. **Notification errors**: Must be caught and logged, never crash document operations
6. **UTC timestamps**: All datetime fields use UTC (`datetime.utcnow()`)

## Project Structure Highlights

```
app/
├── api/v1/
│   ├── router.py              # Main router (includes all endpoint routers)
│   └── endpoints/             # API endpoints (auth, users, departments, etc.)
├── core/
│   ├── security.py            # JWT token generation/verification
│   └── permissions.py         # RBAC decorators and checkers
├── db/
│   ├── mongodb.py             # Connection manager + Collections enum
│   ├── repositories/          # Data access layer (extends BaseRepository)
│   └── migrations/            # Seed data and index creation scripts
├── schemas/                   # Pydantic models (3-tier: Base/Create/Response)
├── services/                  # Cross-cutting services (notification, email)
├── utils/
│   └── constants.py           # Enums (UserRole, DocumentStatus, etc.)
├── config.py                  # Settings (Pydantic Settings)
└── main.py                    # FastAPI app initialization
```

## Adding New Features

**New Endpoint Checklist**:
1. Create Pydantic schemas (Base/Create/Response) in `app/schemas/`
2. Add repository methods in `app/db/repositories/` (extend BaseRepository)
3. Add collection name to `Collections` class if new collection
4. Create router in `app/api/v1/endpoints/`
5. Include router in `app/api/v1/router.py` with prefix and tags
6. Add permissions using `Depends(require_*)` decorators
7. Convert ObjectIds to strings before returning responses
8. Update database indexes if needed

**Testing Pattern**:
- Integration tests in `tests/` directory
- Test via Swagger UI for manual verification
- Default test credentials: admin@townhall.com / admin123

## Implementation Roadmap

**Completed** (Phases 1-4):
- ✅ Authentication & JWT
- ✅ User & Department Management
- ✅ Document Core Functionality
- ✅ File Management (GridFS)
- ✅ Document Forwarding & Status
- ✅ Audit Trail (Document History)
- ✅ Notifications & Dashboard

**Remaining** (see IMPLEMENTATION_PLAN.md):
- Phase 5: Advanced Analytics & Reporting
- Phase 6: Testing & Security Hardening
- Phase 7: Documentation & Deployment
- Phase 8: Post-MVP Enhancements

## Current Phase Status

**Phase 4 Complete**: 41 API endpoints operational
- 5 notification endpoints
- 4 dashboard endpoints (stats, recent activity, pending actions, deadline reminders)
- Notifications integrated at 5 document operation points
- Email service with graceful degradation (works without SMTP config)
