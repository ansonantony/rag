import logging, time, uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError
from app.routes.query import router as query_router
from app.api.v1 import auth, chat, documents
from app.core.config import get_settings

app = FastAPI(
    title="RAG API",
    description="This is a RAG API ",
    version="0.1.0",
)

app.include_router(query_router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in get_settings().cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id, started = str(uuid.uuid4()), time.perf_counter()
    try: response = await call_next(request)
    except OperationalError:
        logging.exception("database_unavailable request_id=%s path=%s", request_id, request.url.path)
        return JSONResponse(status_code=503, content={"error": {"code": "DATABASE_UNAVAILABLE", "message": "Database is unavailable. Start PostgreSQL and apply migrations."}})
    except Exception:
        logging.exception("request_failed request_id=%s path=%s", request_id, request.url.path)
        return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": "Internal server error."}})
    response.headers["X-Request-ID"] = request_id
    logging.info("request_id=%s path=%s status=%s latency_ms=%s", request_id, request.url.path, response.status_code, round((time.perf_counter()-started)*1000))
    return response
