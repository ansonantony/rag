from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
class DocumentResponse(BaseModel):
    id: UUID; filename: str; original_name: str; file_type: str | None; file_size: int | None
    status: str; qdrant_collection: str | None; chunk_count: int; created_at: datetime; updated_at: datetime
    model_config = {"from_attributes": True}
