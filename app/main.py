import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import get_settings
from app.database import init_db
from app.api.workflows import router as workflows_router
from app.api.approvals import router as approvals_router
from app.api.outbox import router as outbox_router
from app.api.health import router as health_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-grade Human-in-the-Loop AI Workflow System with Explicit Safety Gates and Audit Trails.",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health_router)
app.include_router(workflows_router)
app.include_router(approvals_router)
app.include_router(outbox_router)

# Mount Static UI
static_dir = os.path.join(os.path.dirname(__file__), "ui", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def serve_ui():
        return FileResponse(os.path.join(static_dir, "index.html"))
