from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.config import settings
from app.routers import auth, sessions, companies, contacts, instagram, outreach, jobs, chat, export

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BeautyProspector API",
    description="B2B prospecting platform for the medspa/aesthetics industry",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Register routers
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(companies.router)
app.include_router(contacts.router)
app.include_router(instagram.router)
app.include_router(outreach.router)
app.include_router(jobs.router)
app.include_router(chat.router)
app.include_router(export.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "BeautyProspector API"}


@app.get("/")
async def root():
    return {"message": "BeautyProspector API", "docs": "/docs"}
