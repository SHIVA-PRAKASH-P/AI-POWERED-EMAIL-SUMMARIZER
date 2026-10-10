import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database.session import get_db, init_db
from backend.app.database.seed_data import seed_database
from backend.app.models import Email, AIAnalysis, ActionItem, Meeting, Evidence, Entity
from backend.app.utils.security_logging import setup_security_logging

from backend.app.api.routes_emails import router as emails_router
from backend.app.api.routes_dashboard import router as dashboard_router
from backend.app.api.routes_actions import router as actions_router
from backend.app.api.routes_analysis import router as analysis_router
from backend.app.api.routes_provider import router as provider_router
from backend.app.api.routes_cross_intelligence import router as cross_intelligence_router
from backend.app.api.routes_preferences import router as preferences_router
from backend.app.api.routes_evaluation import router as evaluation_router
from backend.app.api.routes_auth import router as auth_router

# Initialize security logging and redaction filter
setup_security_logging()
logger = logging.getLogger("backend.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database tables exist and seed sample emails if empty upon startup."""
    init_db()
    from backend.app.database.session import SessionLocal
    db = SessionLocal()
    try:
        count = db.query(Email).count()
        if count == 0:
            seed_database(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version="0.3.0",
    description="Intelligent Email Summarization, Priority Analysis, and Action Extraction Agent for Faculty",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan
)

# 1. Payload Size Limiting Middleware
@app.middleware("http")
async def limit_payload_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.MAX_PAYLOAD_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={
                        "status": "error",
                        "message": f"Payload Too Large. Maximum allowed size is {settings.MAX_PAYLOAD_BYTES // (1024 * 1024)}MB."
                    }
                )
        except ValueError:
            pass
    return await call_next(request)

# 2. OWASP Security Headers & Global Error Containment Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    try:
        response = await call_next(request)
    except HTTPException as http_exc:
        response = JSONResponse(
            status_code=http_exc.status_code,
            content={"detail": http_exc.detail},
            headers=http_exc.headers
        )
    except Exception as exc:
        error_id = str(uuid.uuid4())
        logger.error(
            "Unhandled internal exception [error_id=%s] on %s %s: %s",
            error_id, request.method, request.url.path, exc,
            exc_info=True
        )
        response = JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "An unexpected internal server error occurred. Please contact the administrator.",
                "error_id": error_id
            }
        )

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'"
    )
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    return response

# 3. Hardened CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],
)

# 4. Global Safe Exception Handler (FastAPI Level)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers
        )

    error_id = str(uuid.uuid4())
    logger.error(
        "Unhandled internal exception [error_id=%s] on %s %s: %s",
        error_id, request.method, request.url.path, exc,
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An unexpected internal server error occurred. Please contact the administrator.",
            "error_id": error_id
        }
    )

# Register API Routers
app.include_router(auth_router)
app.include_router(emails_router)
app.include_router(dashboard_router)
app.include_router(actions_router)
app.include_router(analysis_router)
app.include_router(provider_router)
app.include_router(cross_intelligence_router)
app.include_router(preferences_router)
app.include_router(evaluation_router)

@app.get("/")
def root():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "stage": "STAGE 19B — MULTI-USER IDENTITY & DATA ISOLATION",
        "docs": "/docs" if not settings.is_production else None
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "ai_mode": settings.AI_MODE,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "llm_configured": bool(settings.LLM_API_KEY and settings.LLM_API_KEY.strip()),
        "email_provider": settings.EMAIL_PROVIDER,
        "stage": "STAGE 19B — MULTI-USER IDENTITY & DATA ISOLATION"
    }

@app.get("/api/llm-status")
def llm_status():
    """Inspection endpoint for LLM provider configuration with masked credentials."""
    return {
        "ai_mode": settings.AI_MODE,
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "masked_api_key": settings.masked_api_key,
        "temperature": settings.LLM_TEMPERATURE,
        "fallback_on_error": settings.LLM_FALLBACK_ON_ERROR,
        "is_ready": bool(settings.LLM_API_KEY) or settings.AI_MODE == "mock"
    }

@app.get("/api/db-status")
def database_status(db: Session = Depends(get_db)):
    """Inspection endpoint to verify model counts and database integrity."""
    return {
        "status": "connected",
        "counts": {
            "emails": db.query(Email).count(),
            "analyses": db.query(AIAnalysis).count(),
            "action_items": db.query(ActionItem).count(),
            "meetings": db.query(Meeting).count(),
            "evidences": db.query(Evidence).count(),
            "entities": db.query(Entity).count()
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
