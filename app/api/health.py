from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.config import get_settings

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint verifying database connectivity and runtime config."""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        db_error = str(e)
    else:
        db_error = None

    return {
        "status": "healthy" if db_ok else "unhealthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database_connected": db_ok,
        "database_error": db_error,
        "email_provider": settings.EMAIL_PROVIDER,
        "llm_provider": settings.LLM_PROVIDER,
        "auth_required": settings.REQUIRE_AUTH,
    }
