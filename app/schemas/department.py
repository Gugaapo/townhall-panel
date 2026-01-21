from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.utils.constants import DepartmentType


class DepartmentBase(BaseModel):
    """Base department schema"""
    name: str = Field(..., min_length=2, max_length=100, description="Department name")
    code: str = Field(..., min_length=2, max_length=10, description="Department code (e.g., EDU, ADM)")
    description: Optional[str] = Field(None, max_length=500, description="Department description")


class DepartmentCreate(DepartmentBase):
    """Schema for creating a new department"""
    type: DepartmentType = Field(DepartmentType.REGULAR, description="Department type")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Human Resources",
                "code": "HR",
                "description": "Human resources department",
                "type": "regular"
            }
        }


class DepartmentUpdate(BaseModel):
    """Schema for updating a department"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    code: Optional[str] = Field(None, min_length=2, max_length=10)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "description": "Updated description",
                "is_active": True
            }
        }


class DepartmentResponse(DepartmentBase):
    """Schema for department response"""
    id: str = Field(..., alias="_id", description="Department ID")
    type: DepartmentType = Field(..., description="Department type")
    is_active: bool = Field(True, description="Whether department is active")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "name": "Education",
                "code": "EDU",
                "type": "regular",
                "description": "Education department",
                "is_active": True,
                "created_at": "2025-01-01T00:00:00"
            }
        }
