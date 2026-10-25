import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from qdrant_client import QdrantClient, models
from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.database import get_db
from app.db.models import Document, User
from app.schemas.document import DocumentResponse
from app.services.ingestion_service import ingest, validate_upload
router = APIRouter(prefix="/documents", tags=["Documents"])
def owned(db, doc_id, user_id): return db.scalar(select(Document).where(Document.id == doc_id, Document.user_id == user_id))
@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED, summary="Upload and ingest a document")
def upload(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    content=file.file.read()
    try: ext=validate_upload(file, content)
    except OverflowError as exc: raise HTTPException(413, str(exc)) from exc
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc

    # Generate a unique Qdrant collection name for this document
    import uuid
    collection_name = f"doc_{current_user.id}_{uuid.uuid4().hex[:8]}"

    doc=Document(user_id=current_user.id, filename=file.filename or "upload", original_name=file.filename or "upload", file_type=ext.lstrip("."), file_size=len(content), status="PROCESSING", qdrant_collection=collection_name); db.add(doc); db.commit(); db.refresh(doc)

    # Create the Qdrant collection for this document
    try:
        from qdrant_client import QdrantClient, models
        settings = get_settings()
        client = QdrantClient(url=settings.qdrant_url)

        # Create collection with appropriate vector size (based on embedding model)
        # Using default vector size of 384 for sentence-transformers/all-MiniLM-L6-v2
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
        )
    except Exception as e:
        # If collection creation fails, we should still proceed but log the error
        # In production, you might want to handle this more carefully
        print(f"Warning: Failed to create Qdrant collection {collection_name}: {e}")

    try:
        doc.chunk_count=ingest(doc.id, current_user.id, doc.filename, content, ext); doc.status="COMPLETED"; db.commit(); db.refresh(doc)
    except Exception:
        doc.status="FAILED"; db.commit(); raise HTTPException(502, "Document ingestion failed. Check server logs.")
    return doc
@router.get("", response_model=list[DocumentResponse], summary="List your documents")
def list_documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.scalars(select(Document).where(Document.user_id == current_user.id).order_by(Document.created_at.desc())).all()
@router.get("/{document_id}", response_model=DocumentResponse, summary="Get one of your documents")
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not (doc:=owned(db, document_id, current_user.id)): raise HTTPException(404, "Document not found.")
    return doc
@router.delete("/{document_id}", status_code=204, summary="Delete one of your documents")
def delete_document(document_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not (doc:=owned(db, document_id, current_user.id)): raise HTTPException(404, "Document not found.")

    # Delete the document's specific Qdrant collection
    if doc.qdrant_collection:
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(url=get_settings().qdrant_url)
            client.delete_collection(collection_name=doc.qdrant_collection)
        except Exception as e:
            # Log the error but continue with document deletion
            print(f"Warning: Failed to delete Qdrant collection {doc.qdrant_collection}: {e}")

    db.delete(doc); db.commit()
