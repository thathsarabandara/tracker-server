from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.schemas.item_schemas import ItemCreate, ItemResponse, ItemUpdate


class ItemService:
    """In-memory service managing item domain logic and state."""

    def __init__(self):
        self._items: Dict[int, ItemResponse] = {}
        self._counter: int = 1
        self._seed_data()

    def _seed_data(self):
        now = datetime.now(timezone.utc)
        sample_items = [
            ItemCreate(title="Setup FastAPI project structure", description="Modular architecture with config, routes, models, and service layers", is_completed=True),
            ItemCreate(title="Dockerize application", description="Add Dockerfile and docker-compose.yml for containerized execution", is_completed=True),
            ItemCreate(title="Connect to Database", description="Integrate PostgreSQL/SQLAlchemy ORM into service layer", is_completed=False),
        ]
        for item in sample_items:
            self.create_item(item, created_at=now)

    def get_all(self) -> List[ItemResponse]:
        return list(self._items.values())

    def get_by_id(self, item_id: int) -> Optional[ItemResponse]:
        return self._items.get(item_id)

    def create_item(self, item_data: ItemCreate, created_at: Optional[datetime] = None) -> ItemResponse:
        now = created_at or datetime.now(timezone.utc)
        new_item = ItemResponse(
            id=self._counter,
            title=item_data.title,
            description=item_data.description,
            is_completed=item_data.is_completed,
            created_at=now,
            updated_at=now,
        )
        self._items[self._counter] = new_item
        self._counter += 1
        return new_item

    def update_item(self, item_id: int, item_data: ItemUpdate) -> Optional[ItemResponse]:
        existing = self._items.get(item_id)
        if not existing:
            return None
        
        updated_dict = existing.model_dump()
        update_fields = item_data.model_dump(exclude_unset=True)
        
        for key, value in update_fields.items():
            updated_dict[key] = value
        
        updated_dict["updated_at"] = datetime.now(timezone.utc)
        updated_item = ItemResponse(**updated_dict)
        self._items[item_id] = updated_item
        return updated_item

    def delete_item(self, item_id: int) -> bool:
        if item_id in self._items:
            del self._items[item_id]
            return True
        return False


item_service = ItemService()
