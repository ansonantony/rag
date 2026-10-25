import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import ChatMessage, ChatSession, MessageCitation, User
from app.schemas.chat import ChatAnswerResponse, ChatHistoryResponse, CitationResponse, MessageCreate, MessageResponse, SessionCreate, SessionResponse
from app.services.chat_service import get_owned_session, respond
router=APIRouter(prefix="/chat/sessions", tags=["Chat"])
def cite(c): return CitationResponse(document_id=c.document_id, filename=c.document.filename, page_number=c.page_number, chunk_id=c.chunk_id, similarity_score=c.similarity_score)
@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED, summary="Create chat session")
def create(body: SessionCreate, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    # Verify that the document belongs to the current user
    document = db.scalar(select(Document).where(Document.id == body.document_id, Document.user_id == current_user.id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found or access denied")

    session=ChatSession(user_id=current_user.id, title=body.title, document_id=body.document_id); db.add(session); db.commit(); db.refresh(session); return session
@router.get("", response_model=list[SessionResponse], summary="List your chat sessions")
def sessions(db: Session=Depends(get_db), current_user: User=Depends(get_current_user)): return db.scalars(select(ChatSession).where(ChatSession.user_id==current_user.id).order_by(ChatSession.updated_at.desc())).all()
@router.get("/{session_id}", response_model=ChatHistoryResponse, summary="Get session history")
def get_session(session_id: uuid.UUID, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    session=db.scalar(select(ChatSession).options(selectinload(ChatSession.messages).selectinload(ChatMessage.citations).selectinload(MessageCitation.document), selectinload(ChatSession.document)).where(ChatSession.id==session_id, ChatSession.user_id==current_user.id))
    if not session: raise HTTPException(404,"Chat session not found.")
    return ChatHistoryResponse(session_id=session.id,messages=[MessageResponse(id=m.id,role=m.role,content=m.content,created_at=m.created_at,latency_ms=m.latency_ms,citations=[cite(c) for c in m.citations]) for m in session.messages])
@router.delete("/{session_id}", status_code=204, summary="Delete your chat session")
def delete_session(session_id: uuid.UUID, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    session=get_owned_session(db,session_id,current_user.id)
    if not session: raise HTTPException(404,"Chat session not found.")
    db.delete(session);db.commit()
@router.post("/{session_id}/messages", response_model=ChatAnswerResponse, summary="Ask a question")
def message(session_id: uuid.UUID, body: MessageCreate, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    session=get_owned_session(db,session_id,current_user.id)
    if not session: raise HTTPException(404,"Chat session not found.")
    try: assistant,citations=respond(db,session,body.message)
    except RuntimeError as exc: raise HTTPException(503,str(exc)) from exc
    except Exception: raise HTTPException(502,"Chat generation failed.")
    db.refresh(assistant)
    return ChatAnswerResponse(session_id=session.id,message_id=assistant.id,answer=assistant.content,citations=[cite(c) for c in citations])
@router.get("/{session_id}/messages", response_model=ChatHistoryResponse, summary="Get session messages")
def messages(session_id: uuid.UUID, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)): return get_session(session_id,db,current_user)
