from typing import Optional, Dict, Any
from app.db.repositories.base import BaseRepository
from app.db.mongodb import Collections
from app.utils.constants import DepartmentType


class DepartmentRepository(BaseRepository):
    """Repository for department operations"""

    def __init__(self):
        super().__init__(Collections.DEPARTMENTS)

    async def find_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Find a department by code

        Args:
            code: Department code (e.g., 'EDU', 'ADM')

        Returns:
            Department document if found, None otherwise
        """
        return await self.find_one({"code": code.upper()})

    async def find_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find a department by name

        Args:
            name: Department name

        Returns:
            Department document if found, None otherwise
        """
        return await self.find_one({"name": name})

    async def code_exists(self, code: str) -> bool:
        """
        Check if a department code already exists

        Args:
            code: Department code to check

        Returns:
            True if code exists, False otherwise
        """
        return await self.exists({"code": code.upper()})

    async def name_exists(self, name: str) -> bool:
        """
        Check if a department name already exists

        Args:
            name: Department name to check

        Returns:
            True if name exists, False otherwise
        """
        return await self.exists({"name": name})

    async def find_main_department(self) -> Optional[Dict[str, Any]]:
        """
        Find the main administration department

        Returns:
            Main department document if found, None otherwise
        """
        return await self.find_one({"type": DepartmentType.MAIN.value})

    async def find_active_departments(self) -> list:
        """
        Find all active departments

        Returns:
            List of active departments
        """
        return await self.find_many(
            {"is_active": True},
            sort=[("name", 1)]
        )
