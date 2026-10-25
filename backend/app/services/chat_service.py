import time, uuid
from sqlalchemy import select
from sqlalchemy.orm import Session
from huggingface_hub import InferenceClient
from app.core.config import get_settings
from app.db.models import ChatMessage, ChatSession, Document, MessageCitation
from app.services.retrieval_service import retrieve
def get_owned_session(db: Session, session_id: uuid.UUID, user_id: uuid.UUID) -> ChatSession | None:
    return db.scalar(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id))
def respond(db: Session, session: ChatSession, question: str) -> tuple[ChatMessage, list[MessageCitation]]:
    settings = get_settings(); user_message = ChatMessage(session_id=session.id, role="user", content=question); db.add(user_message); db.flush()
    # Retrieve from the specific document associated with this session
    chunks = retrieve(question, session.user_id, session.document_id, db=db); context = "\n\n".join(f"[Source {i + 1}: {c['filename']}, page {c.get('page_number', 'unknown')}] {c['source_text']}" for i, c in enumerate(chunks))
    history = db.scalars(select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.desc()).limit(settings.max_chat_history)).all()[::-1]
    messages = [{"role": "system", "content": "You are a document question-answering assistant. Answer ONLY from the provided context. If absent, say the information was not found in the provided documents. Do not invent facts. Cite source numbers for factual claims.\n\nContext:\n" + context}]
    messages += [{"role": m.role, "content": m.content} for m in history if m.role in {"user", "assistant"}]
    started = time.perf_counter()
    if not settings.hf_token: raise RuntimeError("HF_TOKEN is not configured.")
    answer = InferenceClient(token=settings.hf_token, provider=settings.hf_provider).chat_completion(model=settings.hf_chat_model, messages=messages, max_tokens=512).choices[0].message.content
    assistant = ChatMessage(session_id=session.id, role="assistant", content=answer, latency_ms=round((time.perf_counter()-started)*1000)); db.add(assistant); db.flush()
    citations=[]
    for chunk in chunks:
        citation=MessageCitation(message_id=assistant.id, document_id=uuid.UUID(chunk["document_id"]), chunk_id=chunk["chunk_id"], page_number=chunk.get("page_number"), source_text=chunk["source_text"], similarity_score=chunk.get("similarity_score")); db.add(citation); citations.append(citation)
    db.commit(); db.refresh(assistant); return assistant, citations
