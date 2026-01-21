"""
Base Motor Model View for Starlette-Admin.

Provides CRUD operations for MongoDB collections using the existing repository pattern.
"""

from typing import Any, Dict, List, Optional, Sequence, Type, Union
from datetime import datetime

from bson import ObjectId
from starlette.requests import Request
from starlette_admin import (
    BaseModelView,
    StringField,
    DateTimeField,
    BooleanField,
    IntegerField,
    TextAreaField,
    EnumField,
    HasOne,
)
from starlette_admin.fields import BaseField

from app.db.repositories.base import BaseRepository


class DictObject:
    """
    Wrapper class that makes a dictionary accessible via attributes.

    Starlette-Admin uses getattr to access field values, so we need
    to convert dictionaries to objects that support attribute access.
    """

    def __init__(self, data: Dict[str, Any]):
        # Store original dict for reference
        object.__setattr__(self, '_data', data)
        # Set all dict keys as attributes
        for key, value in data.items():
            object.__setattr__(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-like get method for compatibility."""
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        """Dict-like indexing for compatibility."""
        return getattr(self, key, None)

    def __setitem__(self, key: str, value: Any) -> None:
        """Dict-like item assignment for compatibility."""
        setattr(self, key, value)
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator."""
        return hasattr(self, key) and key != '_data'

    def __repr__(self) -> str:
        return f"DictObject({self._data})"


def convert_objectid_to_str(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert all ObjectId fields in a document to strings."""
    if doc is None:
        return doc

    result = dict(doc)

    for key, value in result.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, dict):
            result[key] = convert_objectid_to_str(value)
        elif isinstance(value, list):
            result[key] = [
                convert_objectid_to_str(item) if isinstance(item, dict)
                else str(item) if isinstance(item, ObjectId)
                else item
                for item in value
            ]

    return result


def dict_to_object(doc: Dict[str, Any]) -> DictObject:
    """Convert a dictionary to a DictObject for attribute access."""
    if doc is None:
        return None
    # First convert ObjectIds to strings
    converted = convert_objectid_to_str(doc)
    return DictObject(converted)


def convert_str_to_objectid(value: str, field_name: str = None) -> ObjectId:
    """Convert string to ObjectId."""
    try:
        return ObjectId(value)
    except Exception:
        return value


class BaseMotorModelView(BaseModelView):
    """
    Base model view for Motor (async MongoDB).

    Maps Starlette-Admin CRUD operations to repository methods.
    Subclasses should define:
    - repository: The repository instance to use
    - collection_name: Name of the MongoDB collection
    - fields: List of field definitions
    """

    # Repository instance - subclasses must set this
    repository: BaseRepository = None

    # Collection name for display
    collection_name: str = ""

    # Primary key field name (MongoDB uses _id)
    pk_attr: str = "_id"

    # Fields that contain ObjectId references to other collections
    objectid_fields: List[str] = []

    # CRUD permissions - use these to control access
    # (these are config values, the actual can_* methods are below)
    _allow_create: bool = True
    _allow_edit: bool = True
    _allow_delete: bool = True

    # Pagination
    page_size: int = 25
    page_size_options: List[int] = [10, 25, 50, 100]

    # Sorting
    fields_default_sort: List[tuple] = [("created_at", True)]  # True = descending

    def __init__(self, repository: BaseRepository = None, **kwargs):
        """Initialize with optional repository override."""
        super().__init__(**kwargs)
        if repository is not None:
            self.repository = repository

    def can_create(self, request: Request) -> bool:
        """Check if user can create new records."""
        return self._allow_create

    def can_edit(self, request: Request) -> bool:
        """Check if user can edit records."""
        return self._allow_edit

    def can_delete(self, request: Request) -> bool:
        """Check if user can delete records."""
        return self._allow_delete

    async def find_all(
        self,
        request: Request,
        skip: int = 0,
        limit: int = 100,
        where: Union[Dict[str, Any], str, None] = None,
        order_by: Optional[List[str]] = None,
    ) -> Sequence[Any]:
        """
        Find all documents with pagination, filtering, and sorting.

        Args:
            request: Starlette request
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            where: Filter criteria (dict or string)
            order_by: List of field names to sort by (prefix with - for descending)

        Returns:
            List of documents converted to have string IDs
        """
        # Parse filter
        filter_dict = self._parse_where(where)

        # Parse sorting
        sort_list = self._parse_order_by(order_by)

        # Query the repository
        documents = await self.repository.find_many(
            filter=filter_dict,
            skip=skip,
            limit=limit,
            sort=sort_list,
        )

        # Convert documents to objects for attribute access
        return [dict_to_object(doc) for doc in documents]

    async def count(
        self,
        request: Request,
        where: Union[Dict[str, Any], str, None] = None,
    ) -> int:
        """
        Count documents matching the filter.

        Args:
            request: Starlette request
            where: Filter criteria

        Returns:
            Count of matching documents
        """
        filter_dict = self._parse_where(where)
        return await self.repository.count(filter_dict)

    async def find_by_pk(
        self,
        request: Request,
        pk: Any,
    ) -> Optional[Any]:
        """
        Find a document by primary key.

        Args:
            request: Starlette request
            pk: Primary key value (string ID)

        Returns:
            Document if found, None otherwise
        """
        document = await self.repository.find_by_id(str(pk))
        return dict_to_object(document) if document else None

    async def find_by_pks(
        self,
        request: Request,
        pks: List[Any],
    ) -> Sequence[Any]:
        """
        Find multiple documents by their primary keys.

        Args:
            request: Starlette request
            pks: List of primary key values

        Returns:
            List of documents
        """
        documents = []
        for pk in pks:
            doc = await self.repository.find_by_id(str(pk))
            if doc:
                documents.append(dict_to_object(doc))
        return documents

    async def create(
        self,
        request: Request,
        data: Dict[str, Any],
    ) -> Any:
        """
        Create a new document.

        Args:
            request: Starlette request
            data: Document data

        Returns:
            Created document with string ID
        """
        # Process data before creation
        processed_data = await self._process_create_data(request, data)

        # Create via repository
        document = await self.repository.create(processed_data)

        return dict_to_object(document)

    async def edit(
        self,
        request: Request,
        pk: Any,
        data: Dict[str, Any],
    ) -> Any:
        """
        Update an existing document.

        Args:
            request: Starlette request
            pk: Primary key of document to update
            data: Updated data

        Returns:
            Updated document with string ID
        """
        # Process data before update
        processed_data = await self._process_edit_data(request, data)

        # Remove _id from update data if present
        processed_data.pop("_id", None)

        # Update via repository
        document = await self.repository.update_by_id(str(pk), processed_data)

        return dict_to_object(document) if document else None

    async def delete(
        self,
        request: Request,
        pks: List[Any],
    ) -> Optional[int]:
        """
        Delete documents by primary keys.

        Args:
            request: Starlette request
            pks: List of primary keys to delete

        Returns:
            Number of deleted documents
        """
        deleted_count = 0
        for pk in pks:
            if await self.repository.delete_by_id(str(pk)):
                deleted_count += 1
        return deleted_count

    def _parse_where(
        self,
        where: Union[Dict[str, Any], str, None]
    ) -> Dict[str, Any]:
        """
        Parse where clause into MongoDB filter.

        Args:
            where: Filter criteria (dict or string search term)

        Returns:
            MongoDB filter dictionary
        """
        if where is None:
            return {}

        if isinstance(where, dict):
            return where

        # If it's a string, use it as a search term
        if isinstance(where, str) and where.strip():
            # This should be overridden by subclasses to define searchable fields
            return self._build_search_filter(where)

        return {}

    def _build_search_filter(self, search_term: str) -> Dict[str, Any]:
        """
        Build a search filter from a search term.

        Override this in subclasses to define searchable fields.

        Args:
            search_term: Term to search for

        Returns:
            MongoDB filter for searching
        """
        # Default: no search
        return {}

    def _parse_order_by(
        self,
        order_by: Optional[List[str]]
    ) -> Optional[List[tuple]]:
        """
        Parse order_by strings into MongoDB sort tuples.

        Args:
            order_by: List of field names (prefix with - for descending)

        Returns:
            List of (field, direction) tuples for MongoDB sort
        """
        if not order_by:
            # Use default sorting
            return [(f, -1 if desc else 1)
                    for f, desc in self.fields_default_sort]

        sort_list = []
        for field in order_by:
            if field.startswith("-"):
                sort_list.append((field[1:], -1))  # Descending
            else:
                sort_list.append((field, 1))  # Ascending

        return sort_list if sort_list else None

    async def _process_create_data(
        self,
        request: Request,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process data before creation.

        Override in subclasses for custom processing (e.g., password hashing).

        Args:
            request: Starlette request
            data: Raw form data

        Returns:
            Processed data ready for database insertion
        """
        return data

    async def _process_edit_data(
        self,
        request: Request,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process data before update.

        Override in subclasses for custom processing.

        Args:
            request: Starlette request
            data: Raw form data

        Returns:
            Processed data ready for database update
        """
        return data

    async def get_model_objects(
        self,
        request: Request,
        limit: int = 0
    ) -> Sequence[Any]:
        """
        Get model objects for select dropdowns.

        Args:
            request: Starlette request
            limit: Maximum number to return (0 = all)

        Returns:
            List of documents for selection
        """
        documents = await self.repository.find_many(
            filter={},
            skip=0,
            limit=limit if limit > 0 else 1000,
            sort=[("_id", -1)],
        )
        return [dict_to_object(doc) for doc in documents]

    def get_model_attr(self, obj: Any, name: str) -> Any:
        """
        Get an attribute from a model object.

        Args:
            obj: Model object (DictObject or dict)
            name: Attribute name

        Returns:
            Attribute value
        """
        if isinstance(obj, DictObject):
            return getattr(obj, name, None)
        if isinstance(obj, dict):
            return obj.get(name)
        return getattr(obj, name, None)

    async def get_pk_value(self, request: Request, obj: Any) -> Any:
        """
        Get the primary key value from an object.

        Overridden to support DictObjects and dictionaries (MongoDB documents).

        Args:
            request: Starlette request
            obj: Model object (DictObject or dict)

        Returns:
            Primary key value
        """
        if isinstance(obj, DictObject):
            return getattr(obj, self.pk_attr, None)
        if isinstance(obj, dict):
            return obj.get(self.pk_attr)
        return getattr(obj, self.pk_attr, None)

    async def serialize_field_value(
        self,
        value: Any,
        field: BaseField,
        action: str,
        request: Request,
    ) -> Any:
        """
        Serialize a field value for display.

        Args:
            value: Raw value from database
            field: Field definition
            action: Current action (list, detail, etc.)
            request: Starlette request

        Returns:
            Serialized value for display
        """
        if value is None:
            return None

        if isinstance(value, ObjectId):
            return str(value)

        if isinstance(value, datetime):
            return value.isoformat()

        return value
