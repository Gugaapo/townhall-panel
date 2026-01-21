from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

from app.utils.constants import UserRole
from app.schemas.common import PyObjectId


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=2, max_length=100, description="User full name")


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=6, max_length=100, description="User password")
    department_id: str = Field(..., description="Department ID")
    role: UserRole = Field(UserRole.EMPLOYEE, description="User role")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@townhall.com",
                "full_name": "John Doe",
                "password": "securepassword123",
                "department_id": "507f1f77bcf86cd799439011",
                "role": "employee"
            }
        }


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    department_id: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John D. Smith",
                "is_active": True
            }
        }


class UserResponse(UserBase):
    """Schema for user response"""
    id: str = Field(..., alias="_id", description="User ID")
    department_id: str = Field(..., description="Department ID")
    role: UserRole = Field(..., description="User role")
    is_active: bool = Field(True, description="Whether user is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "email": "john.doe@townhall.com",
                "full_name": "John Doe",
                "department_id": "507f1f77bcf86cd799439012",
                "role": "employee",
                "is_active": True,
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00"
            }
        }


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "admin@townhall.com",
                "password": "admin123"
            }
        }


class Token(BaseModel):
    """Schema for authentication token response"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }


class TokenRefresh(BaseModel):
    """Schema for token refresh request"""
    refresh_token: str = Field(..., description="Refresh token")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
