from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PyObjectId(str):
    """Custom type for MongoDB ObjectId"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        from bson import ObjectId
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)


class ResponseModel(BaseModel):
    """Standard API response model"""
    success: bool = True
    message: str
    data: Optional[dict] = None


class PaginationParams(BaseModel):
    """Pagination parameters"""
    skip: int = Field(0, ge=0, description="Number of items to skip")
    limit: int = Field(20, ge=1, le=100, description="Number of items to return")


class PaginatedResponse(BaseModel):
    """Paginated response model"""
    total: int = Field(..., description="Total number of items")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Number of items per page")
    items: list = Field(..., description="List of items")
