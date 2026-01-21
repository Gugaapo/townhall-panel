# Townhall Document Management System - Implementation Plan

## Project Overview
A cloud-based document management system to digitize city hall operations, eliminating paper use. Departments can send, receive, and track documents with full audit trails.

## Technical Stack
- **Backend**: FastAPI (Python)
- **Database**: MongoDB (early dev: GridFS for files, later: Cloud storage)
- **Package Manager**: Poetry
- **Database Tool**: DBeaver
- **Containerization**: Docker/Docker Compose
- **Authentication**: JWT-based with role-based access control (RBAC)
- **Notifications**: In-app + Email
- **API Documentation**: Swagger UI (FastAPI built-in) + ReDoc

## System Architecture

### High-Level Architecture
```
┌─────────────────┐
│   Frontend      │
│   (Future)      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│      FastAPI Backend                │
│  ┌──────────────────────────────┐   │
│  │  Auth & RBAC Middleware      │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  REST API Endpoints          │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  Business Logic Layer        │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  Notification Service        │   │
│  └──────────────────────────────┘   │
└─────────┬───────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│         MongoDB                     │
│  ┌──────────────────────────────┐   │
│  │  Collections:                │   │
│  │  - users                     │   │
│  │  - departments               │   │
│  │  - documents                 │   │
│  │  - document_history          │   │
│  │  - notifications             │   │
│  │  - fs.files (GridFS)         │   │
│  │  - fs.chunks (GridFS)        │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

## Database Schema Design

### 1. Users Collection
```json
{
  "_id": "ObjectId",
  "email": "string (unique)",
  "password_hash": "string",
  "full_name": "string",
  "department_id": "ObjectId (ref: departments)",
  "role": "string (enum: admin, department_head, employee)",
  "is_active": "boolean",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### 2. Departments Collection
```json
{
  "_id": "ObjectId",
  "name": "string (unique)",
  "code": "string (unique, e.g., 'EDU', 'ADM', 'SPO')",
  "type": "string (enum: main, regular)",
  "description": "string",
  "created_at": "datetime",
  "is_active": "boolean"
}
```

### 3. Documents Collection
```json
{
  "_id": "ObjectId",
  "document_number": "string (auto-generated, unique)",
  "title": "string",
  "description": "string",
  "document_type": "string (e.g., 'request', 'response', 'memo')",
  "status": "string (enum: draft, pending, in_progress, completed, archived)",
  "priority": "string (enum: low, medium, high, urgent)",

  "creator_id": "ObjectId (ref: users)",
  "creator_department_id": "ObjectId (ref: departments)",

  "current_holder_department_id": "ObjectId (ref: departments)",
  "assigned_to_user_id": "ObjectId (ref: users, optional)",

  "files": [
    {
      "file_id": "ObjectId (GridFS reference)",
      "filename": "string",
      "content_type": "string",
      "size": "number",
      "uploaded_at": "datetime",
      "uploaded_by": "ObjectId (ref: users)"
    }
  ],

  "metadata": {
    "deadline": "datetime (optional)",
    "tags": ["string"],
    "custom_fields": "object (flexible key-value pairs)"
  },

  "created_at": "datetime",
  "updated_at": "datetime",
  "archived_at": "datetime (optional)"
}
```

### 4. Document History Collection (Audit Trail)
```json
{
  "_id": "ObjectId",
  "document_id": "ObjectId (ref: documents)",
  "action": "string (enum: created, forwarded, viewed, responded, status_changed, modified, archived)",
  "performed_by": "ObjectId (ref: users)",
  "performed_by_name": "string (denormalized for audit)",
  "performed_by_department": "ObjectId (ref: departments)",

  "from_department_id": "ObjectId (optional)",
  "to_department_id": "ObjectId (optional)",

  "old_status": "string (optional)",
  "new_status": "string (optional)",
  "status_reason": "string (optional)",

  "changes": {
    "field": "string",
    "old_value": "any",
    "new_value": "any"
  },

  "comment": "string (optional)",
  "metadata": "object (flexible)",
  "timestamp": "datetime"
}
```

### 5. Notifications Collection
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId (ref: users)",
  "document_id": "ObjectId (ref: documents)",
  "type": "string (enum: document_received, document_forwarded, response_received, status_changed)",
  "title": "string",
  "message": "string",
  "is_read": "boolean",
  "email_sent": "boolean",
  "email_sent_at": "datetime (optional)",
  "created_at": "datetime",
  "read_at": "datetime (optional)"
}
```

## API Endpoints Structure

### Authentication & Users
```
POST   /api/v1/auth/register          # Register new user (admin only)
POST   /api/v1/auth/login             # Login and get JWT token
POST   /api/v1/auth/refresh           # Refresh JWT token
POST   /api/v1/auth/logout            # Logout (invalidate token)
GET    /api/v1/auth/me                # Get current user info

GET    /api/v1/users                  # List users (filtered by department for non-admins)
GET    /api/v1/users/{user_id}        # Get user details
PUT    /api/v1/users/{user_id}        # Update user
DELETE /api/v1/users/{user_id}        # Deactivate user
```

### Departments
```
GET    /api/v1/departments            # List all departments
GET    /api/v1/departments/{dept_id}  # Get department details
POST   /api/v1/departments            # Create department (admin only)
PUT    /api/v1/departments/{dept_id}  # Update department (admin only)
GET    /api/v1/departments/{dept_id}/users  # List users in department
GET    /api/v1/departments/{dept_id}/documents  # List documents for department
```

### Documents
```
POST   /api/v1/documents              # Create new document
GET    /api/v1/documents              # List documents (filtered by department/user)
GET    /api/v1/documents/{doc_id}     # Get document details
PUT    /api/v1/documents/{doc_id}     # Update document
DELETE /api/v1/documents/{doc_id}     # Soft delete document

POST   /api/v1/documents/{doc_id}/forward     # Forward document to another dept
POST   /api/v1/documents/{doc_id}/respond     # Add response to document
POST   /api/v1/documents/{doc_id}/archive     # Archive document
PUT    /api/v1/documents/{doc_id}/status      # Update document status

GET    /api/v1/documents/{doc_id}/history     # Get document audit trail
GET    /api/v1/documents/{doc_id}/timeline    # Get document timeline view
```

### Files
```
POST   /api/v1/documents/{doc_id}/files       # Upload file to document
GET    /api/v1/documents/{doc_id}/files       # List files for document
GET    /api/v1/files/{file_id}                # Download file
DELETE /api/v1/files/{file_id}                # Delete file
```

### Notifications
```
GET    /api/v1/notifications          # Get user's notifications
GET    /api/v1/notifications/unread   # Get unread notifications count
PUT    /api/v1/notifications/{notif_id}/read  # Mark as read
PUT    /api/v1/notifications/read-all # Mark all as read
DELETE /api/v1/notifications/{notif_id}  # Delete notification
```

### Dashboard & Analytics
```
GET    /api/v1/dashboard/stats        # Get user/department statistics
GET    /api/v1/dashboard/recent       # Recent documents
GET    /api/v1/dashboard/pending      # Pending actions
GET    /api/v1/reports/department     # Department activity report
```

## Authentication & Authorization Strategy

### JWT Token Structure
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "department_id": "dept_id",
  "role": "employee|department_head|admin",
  "exp": "expiration_timestamp",
  "iat": "issued_at_timestamp"
}
```

### Role-Based Permissions

#### Admin Role
- Full system access
- Manage all departments
- Manage all users
- View all documents
- System configuration

#### Department Head Role
- Manage users in their department
- View/manage all documents for their department
- Forward documents to other departments
- Generate department reports

#### Employee Role
- View documents assigned to their department
- Create new documents
- Respond to documents
- Forward documents (with approval)
- View their own document history

### Permission Middleware
- Implement decorator-based permissions: `@require_role("admin")`, `@require_department_access`
- Document access check: User can only access documents if:
  - Creator of the document
  - Document is assigned to their department
  - Admin role
  - Document history includes their department

## Notification System Design

### In-App Notifications
- Store in MongoDB notifications collection
- Real-time updates via polling (simple) or WebSocket (future enhancement)
- Notification types:
  - Document received
  - Document forwarded
  - Response added
  - Status changed
  - Deadline approaching

### Email Notifications
- Use SMTP configuration (Gmail, SendGrid, or custom SMTP)
- Email templates for each notification type
- Async email sending using background tasks (FastAPI BackgroundTasks)
- Email queue for reliability

### Notification Service Implementation
```python
# Pseudo-code structure
class NotificationService:
    async def notify_document_received(document, user):
        # Create in-app notification
        # Send email if user preferences allow

    async def notify_document_forwarded(document, from_dept, to_dept):
        # Notify all users in target department

    async def notify_status_changed(document, old_status, new_status):
        # Notify relevant stakeholders
```

## Project Structure

```
townhall-panel/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── poetry.lock
├── README.md
├── .env.example
├── .gitignore
│
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration and settings
│   ├── dependencies.py         # Dependency injection
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py       # Main API router
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── auth.py
│   │           ├── users.py
│   │           ├── departments.py
│   │           ├── documents.py
│   │           ├── files.py
│   │           ├── notifications.py
│   │           └── dashboard.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py         # JWT, password hashing
│   │   ├── permissions.py      # RBAC decorators and checks
│   │   └── exceptions.py       # Custom exceptions
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── department.py
│   │   ├── document.py
│   │   ├── document_history.py
│   │   └── notification.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py             # Pydantic schemas for users
│   │   ├── department.py
│   │   ├── document.py
│   │   ├── notification.py
│   │   └── common.py           # Shared schemas
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   ├── department_service.py
│   │   ├── document_service.py
│   │   ├── file_service.py
│   │   ├── notification_service.py
│   │   └── email_service.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── mongodb.py          # MongoDB connection
│   │   ├── repositories/       # Data access layer
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── user_repository.py
│   │   │   ├── department_repository.py
│   │   │   ├── document_repository.py
│   │   │   └── notification_repository.py
│   │   └── migrations/         # Database migrations/seeds
│   │       └── seed_data.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── constants.py        # Enums and constants
│       ├── helpers.py          # Helper functions
│       └── validators.py       # Custom validators
│
└── tests/
    ├── __init__.py
    ├── conftest.py             # Pytest configuration
    ├── test_auth.py
    ├── test_documents.py
    ├── test_departments.py
    └── test_notifications.py
```

## Development Roadmap

### Phase 1: Project Setup & Core Infrastructure (Week 1-2)
1. **Initialize Project**
   - Set up Poetry project with dependencies
   - Create Docker/Docker Compose configuration
   - Set up MongoDB container
   - Configure environment variables
   - Configure FastAPI with Swagger UI and ReDoc

2. **Database Setup**
   - Create MongoDB connection manager
   - Implement base repository pattern
   - Create database indexes for performance
   - Seed initial data (departments, admin user)

3. **Authentication Foundation**
   - Implement JWT token generation/validation
   - Password hashing with bcrypt
   - Create auth endpoints (login, register, refresh)
   - Implement permission decorators
   - Document all endpoints in Swagger UI with examples

### Phase 2: User & Department Management (Week 2-3)
1. **User Management**
   - User CRUD operations
   - User repository and service layer
   - Role-based access control
   - User schemas and validation

2. **Department Management**
   - Department CRUD operations
   - Department repository and service layer
   - Main department designation
   - Department-user associations

### Phase 3: Document Core Functionality (Week 3-5)
1. **Document Management**
   - Document creation and retrieval
   - Document repository and service layer
   - Document status management
   - Document search and filtering

2. **File Management**
   - GridFS integration for file storage
   - File upload/download endpoints
   - File attachment to documents
   - File validation (size, type)

3. **Document Forwarding**
   - Forward document between departments
   - Automatic notification on forwarding
   - Track document flow in history
   - Main department routing logic

### Phase 4: Audit Trail & History (Week 5-6)
1. **Document History**
   - Track all document actions
   - Create document_history records
   - Version tracking for document modifications
   - Status change logging with reasons

2. **Timeline View**
   - Generate document timeline
   - Visualize document journey
   - Show all interactions and users involved

### Phase 5: Notification System (Week 6-7)
1. **In-App Notifications**
   - Create notification service
   - Notification CRUD operations
   - Real-time notification retrieval
   - Mark as read/unread functionality

2. **Email Notifications**
   - Configure SMTP settings
   - Create email templates
   - Implement async email sending
   - Handle email failures gracefully

### Phase 6: Dashboard & Analytics (Week 7-8)
1. **User Dashboard**
   - Recent documents
   - Pending actions
   - Personal statistics
   - Quick actions

2. **Department Dashboard**
   - Department statistics
   - Document flow metrics
   - Employee activity
   - Performance indicators

### Phase 7: Testing & Security (Week 8-9)
1. **Unit Tests**
   - Service layer tests
   - Repository tests
   - Utility function tests

2. **Integration Tests**
   - API endpoint tests
   - Authentication flow tests
   - Document lifecycle tests

3. **Security Hardening**
   - Input validation
   - SQL injection prevention (MongoDB)
   - Rate limiting
   - CORS configuration
   - Security headers

### Phase 8: Documentation & Deployment (Week 9-10)
1. **API Documentation**
   - Complete Swagger UI documentation with all endpoints
   - Add request/response examples for all endpoints
   - Document authentication flow in Swagger
   - Add schema descriptions and field validations
   - Configure Swagger UI tags and grouping
   - Test all endpoints via Swagger UI

2. **Additional Documentation**
   - User manual
   - Admin guide
   - Deployment guide

3. **Deployment Preparation**
   - Production Docker configuration
   - Environment configuration
   - Backup strategy
   - Monitoring setup

## API Documentation with Swagger UI

FastAPI includes automatic interactive API documentation out of the box:

### Swagger UI Configuration
- **Access URL**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc URL**: `http://localhost:8000/redoc` (Alternative documentation)
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

### Features to Implement
1. **Endpoint Documentation**
   - Clear descriptions for all endpoints
   - Request body examples
   - Response examples (success and error cases)
   - Query parameter descriptions

2. **Schema Documentation**
   - Pydantic model descriptions
   - Field-level documentation with examples
   - Validation rules clearly stated

3. **Authentication in Swagger**
   - Configure OAuth2 password flow for testing
   - "Authorize" button to set JWT token
   - Test authenticated endpoints directly from Swagger UI

4. **Organized Endpoints**
   - Group endpoints by tags (Auth, Users, Departments, Documents, etc.)
   - Logical ordering of operations
   - Deprecation warnings for old endpoints

5. **Example Configuration in FastAPI**
```python
from fastapi import FastAPI

app = FastAPI(
    title="Townhall Document Management API",
    description="API for managing city hall documents digitally",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
    openapi_url="/openapi.json",
    contact={
        "name": "Your Name",
        "email": "contact@townhall.com",
    },
    license_info={
        "name": "Proprietary",
    }
)

# Example endpoint with full documentation
@app.post(
    "/api/v1/documents",
    tags=["Documents"],
    summary="Create a new document",
    description="Create a new document and assign it to a department",
    response_description="The created document with all metadata",
    responses={
        201: {"description": "Document created successfully"},
        400: {"description": "Invalid request data"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to create documents"}
    }
)
async def create_document(document: DocumentCreate):
    # Implementation
    pass
```

### Benefits for Manual Testing
- Test all endpoints without writing code
- Validate request/response schemas
- Test authentication and authorization
- Share API documentation with frontend developers
- Debug API issues quickly
- Generate client SDKs from OpenAPI spec

## Key Technical Decisions

### 1. MongoDB Document Design
- Denormalize user names in history for audit integrity
- Use references (ObjectId) for relationships
- Embed files array in documents for easier querying
- Separate collection for history to prevent document bloat

### 2. File Storage Strategy
- **Phase 1**: GridFS for simplicity
- **Phase 2**: Migrate to cloud storage (S3/GCS)
- Store file metadata in documents collection
- Implement file versioning for modifications

### 3. Document Number Generation
- Format: `{YEAR}-{DEPT_CODE}-{SEQUENCE}`
- Example: `2025-EDU-00123`
- Auto-increment sequence per department per year
- Unique index on document_number

### 4. Status Workflow
```
draft → pending → in_progress → completed → archived
```
- Only certain roles can change to specific statuses
- Status changes require reason/comment
- Archived documents are read-only

### 5. Department Routing
- Administration Department (main) acts as router
- All inter-department documents can go through main dept (optional)
- Direct department-to-department forwarding also allowed
- Configurable routing rules

## Security Considerations

1. **Authentication**
   - JWT tokens with short expiration (15 min access, 7 days refresh)
   - Secure password hashing (bcrypt with cost factor 12)
   - Token blacklist for logout

2. **Authorization**
   - Role-based access control (RBAC)
   - Department-level data isolation
   - Document-level permissions
   - API endpoint protection

3. **Data Protection**
   - Encrypt sensitive data at rest
   - HTTPS only in production
   - Input validation and sanitization
   - File upload restrictions

4. **Audit & Compliance**
   - Complete audit trail
   - Non-repudiation (who did what)
   - Data retention policies
   - GDPR considerations (if applicable)

## Performance Optimization

1. **Database Indexes**
   ```javascript
   // Users
   db.users.createIndex({ "email": 1 }, { unique: true })
   db.users.createIndex({ "department_id": 1 })

   // Documents
   db.documents.createIndex({ "document_number": 1 }, { unique: true })
   db.documents.createIndex({ "current_holder_department_id": 1 })
   db.documents.createIndex({ "creator_id": 1 })
   db.documents.createIndex({ "status": 1 })
   db.documents.createIndex({ "created_at": -1 })

   // Document History
   db.document_history.createIndex({ "document_id": 1, "timestamp": -1 })
   db.document_history.createIndex({ "performed_by": 1 })

   // Notifications
   db.notifications.createIndex({ "user_id": 1, "is_read": 1 })
   db.notifications.createIndex({ "created_at": -1 })
   ```

2. **Caching Strategy**
   - Cache department list (rarely changes)
   - Cache user permissions
   - Redis for session storage (future)

3. **Pagination**
   - Implement cursor-based pagination for large lists
   - Default page size: 20 items
   - Max page size: 100 items

## Future Enhancements (Post-MVP)

1. **Multi-tenancy**
   - Add organization/city_hall collection
   - Isolate data per tenant
   - Tenant-specific customization

2. **Cloud Storage Migration**
   - Migrate from GridFS to S3/GCS
   - Implement signed URLs for file access
   - CDN for file delivery

3. **Real-time Features**
   - WebSocket support for live notifications
   - Real-time document collaboration
   - Live status updates

4. **Advanced Features**
   - Document templates
   - E-signatures
   - OCR for scanned documents
   - Full-text search (Elasticsearch)
   - Mobile app

5. **Analytics & Reporting**
   - Advanced reporting dashboard
   - Export to PDF/Excel
   - Custom report builder
   - Performance metrics

## Estimated Development Timeline

- **Total Development Time**: 10-12 weeks (for MVP)
- **Team Size**: 1 developer (you)
- **Deployment**: Week 10+
- **Testing & Bug Fixes**: Ongoing

## Success Metrics

1. **Functional**
   - All departments can send/receive documents
   - Complete audit trail for all actions
   - Zero paper usage

2. **Performance**
   - API response time < 200ms (95th percentile)
   - File upload < 5 seconds (for 10MB files)
   - Support 50+ concurrent users

3. **Security**
   - No unauthorized data access
   - All actions properly logged
   - Secure authentication

## Next Steps

1. Review and approve this plan
2. Set up development environment
3. Initialize Poetry project with dependencies
4. Create Docker Compose configuration
5. Begin Phase 1 implementation

---

**Questions or modifications needed?** Let me know and I'll update the plan accordingly!
