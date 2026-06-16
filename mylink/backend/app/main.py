from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.api import auth, employers, vacancies, candidates, responses, chat
from app.api import ai as ai_router
from app.db.redis import close_redis
from app.services.ai.registry_setup import register_all_agents
from app.db.base import Base
from app.db.session import async_engine
from app import models as _models  # noqa: F401 ensure models are imported for metadata

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting SmartBot Backend...")
    logger.info(f"Debug mode: {settings.DEBUG}")
    # Ensure DB tables exist (safety for environments without migrations)
    try:
        from sqlalchemy.exc import SQLAlchemyError
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ensured (create_all)")
    except Exception as e:
        logger.exception("Failed ensuring DB schema: %s", e)
    # Register AI agents
    register_all_agents()
    logger.info("AI agents registered")
    
    yield
    
    # Shutdown
    logger.info("Shutting down SmartBot Backend...")
    await close_redis()
    logger.info("Redis connection closed")


# Create FastAPI application
app = FastAPI(
    title="SmartBot HR Platform API",
    description="Backend API for HR chatbot platform with candidate screening",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_origin_regex=settings.ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure preflight returns 204 even if route doesn't exist
@app.options("/{rest_of_path:path}")
async def options_handler(rest_of_path: str):
    return Response(status_code=204)

# Include routers
app.include_router(auth.router)
app.include_router(employers.router)
app.include_router(vacancies.router)
app.include_router(candidates.router)
app.include_router(responses.router)
app.include_router(chat.router)
app.include_router(ai_router.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SmartBot HR Platform API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )

