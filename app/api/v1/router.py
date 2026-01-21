from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, departments, documents, files, notifications, dashboard

# Create main API router
api_router = APIRouter()

# Include authentication endpoints
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

# Include user management endpoints
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
)

# Include department endpoints
api_router.include_router(
    departments.router,
    prefix="/departments",
    tags=["Departments"],
)

# Include document endpoints
api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["Documents"],
)

# Include file endpoints
api_router.include_router(
    files.router,
    prefix="/files",
    tags=["Files"],
)

# Include notification endpoints
api_router.include_router(
    notifications.router,
    prefix="/notifications",
    tags=["Notifications"],
)

# Include dashboard endpoints
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"],
)
