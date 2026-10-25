from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
class SessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    document_id: UUID
class SessionResponse(BaseModel):
    id: UUID; title: str | None; created_at: datetime; updated_at: datetime
    model_config = {"from_attributes": True}
class MessageCreate(BaseModel): message: str = Field(min_length=1, max_length=10000)
class CitationResponse(BaseModel):
    document_id: UUID; filename: str; page_number: int | None; chunk_id: str; similarity_score: float | None
class MessageResponse(BaseModel):
    id: UUID; role: str; content: str; created_at: datetime; latency_ms: int | None = None; citations: list[CitationResponse] = []
class ChatHistoryResponse(BaseModel): session_id: UUID; messages: list[MessageResponse]
class ChatAnswerResponse(BaseModel): session_id: UUID; message_id: UUID; answer: str; citations: list[CitationResponse]
