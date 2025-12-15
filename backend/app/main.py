"""FastAPI application entry point"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import get_settings
from app.database import init_db
from app.api.routes import router
from app.api.auth import router as auth_router
from app.api.payments import router as payments_router

settings = get_settings()

# Ensure reports directory exists
os.makedirs(settings.reports_dir, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events"""
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


# Create FastAPI app
app = FastAPI(
    title="LLM Audit Engine",
    description="Internal tool for LLM Traffic / GEO audit of websites",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(payments_router, prefix="/api")

# Mount reports directory for file serving
app.mount("/reports", StaticFiles(directory=settings.reports_dir), name="reports")


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "LLM Audit Engine API", "version": "0.1.0"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

