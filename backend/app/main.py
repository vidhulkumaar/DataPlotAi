"""
DataPilot AI — FastAPI Backend Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.api import auth, ingest, connect, pipeline, dashboard, chat
from app.db.session import init_db

app = FastAPI(
    title="DataPilot AI",
    description="AI-powered plug-and-play analytics dashboard platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router,      prefix="/api/auth",     tags=["Authentication"])
app.include_router(ingest.router,    prefix="/api/ingest",   tags=["Data Ingestion"])
app.include_router(connect.router,   prefix="/api/connect",  tags=["Database Connect"])
app.include_router(pipeline.router,  prefix="/api/pipeline", tags=["AI Pipeline"])
app.include_router(dashboard.router, prefix="/api/dashboard",tags=["Dashboards"])
app.include_router(chat.router,      prefix="/api/chat",     tags=["RAG Chatbot"])


@app.on_event("startup")
async def on_startup():
    await init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
