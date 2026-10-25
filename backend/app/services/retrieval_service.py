import uuid
from qdrant_client import QdrantClient, models
from app.core.config import get_settings
from app.db.models import Document
from app.routes.query import HuggingFaceEmbeddings
def retrieve(question: str, user_id: uuid.UUID, document_id: uuid.UUID = None, limit: int = 4, db: Session = None) -> list[dict]:
    settings = get_settings(); vector = HuggingFaceEmbeddings().embed_query(question); client = QdrantClient(url=settings.qdrant_url)

    # Determine which collection to use
    if document_id:
        # Get the document to find its specific Qdrant collection
        # If db session is provided, use it; otherwise create a temporary one
        if db is None:
            # This creates a DB call, but ensures we use the right collection
            # For better performance, we could consider caching or passing collection name directly
            from app.db.database import get_db
            db_gen = get_db()
            db = next(db_gen)
            should_close_db = True
        else:
            should_close_db = False

        try:
            document = db.scalar(select(Document).where(Document.id == document_id, Document.user_id == user_id))
            collection_name = document.qdrant_collection if document and document.qdrant_collection else settings.qdrant_collection_name
        finally:
            if should_close_db:
                db.close()
    else:
        collection_name = settings.qdrant_collection_name

    # Build filter - if we have a specific document, filter by document_id as well
    if document_id:
        query_filter = models.Filter(must=[
            models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
            models.FieldCondition(key="document_id", match=models.MatchValue(value=str(document_id)))
        ])
    else:
        query_filter = models.Filter(must=[models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id)))])

    result = client.query_points(collection_name=collection_name, query=vector, query_filter=query_filter, limit=limit, with_payload=True).points
    return [{**p.payload, "similarity_score": p.score} for p in result]
