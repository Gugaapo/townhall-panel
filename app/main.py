from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.admin.admin_app import create_admin_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()


# Create FastAPI application with comprehensive Swagger UI configuration
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## Townhall Document Management System API

    A comprehensive API for managing city hall documents digitally, eliminating paper use.

    ### Features

    * **Authentication & Authorization** - JWT-based authentication with role-based access control
    * **Document Management** - Create, forward, respond to, and archive documents
    * **Department Management** - Manage departments and their users
    * **File Attachments** - Upload and download files attached to documents
    * **Audit Trail** - Complete history of all document actions
    * **Notifications** - In-app and email notifications for document events
    * **Dashboard & Analytics** - Statistics and insights for users and departments

    ### Authentication

    Most endpoints require authentication. To authenticate:
    1. Use the `/api/v1/auth/login` endpoint to get an access token
    2. Click the "Authorize" button (🔒) at the top of this page
    3. Enter your token in the format: `Bearer <your-token>`
    4. Click "Authorize" and close the dialog
    5. You can now test authenticated endpoints

    ### Roles & Permissions

    * **Admin** - Full system access, manage all departments and users
    * **Department Head** - Manage their department, users, and documents
    * **Employee** - Create and manage documents for their department
    """,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Townhall Support",
        "email": "support@townhall.com",
    },
    license_info={
        "name": "Proprietary",
    },
    lifespan=lifespan,
    swagger_ui_parameters={
        "defaultModelsExpandDepth": 1,
        "defaultModelExpandDepth": 2,
        "displayRequestDuration": True,
        "filter": True,
        "showExtensions": True,
        "tryItOutEnabled": True,
    }
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware (required for admin panel authentication)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="admin_session",
    max_age=3600 * 8,  # 8 hours
)

# Create and mount admin panel
admin = create_admin_app()
admin.mount_to(app)


# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Check if the API is running and healthy",
    response_description="API health status"
)
async def health_check():
    """
    Health check endpoint to verify the API is running.

    Returns basic status information about the application.
    """
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV
    }


# Root endpoint
@app.get(
    "/",
    tags=["Root"],
    summary="API Root",
    description="Root endpoint with API information",
)
async def root():
    """
    Root endpoint providing basic API information and links to documentation.
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "admin": "/admin"
    }


# Include API router
from app.api.v1.router import api_router
app.include_router(api_router, prefix="/api/v1")
