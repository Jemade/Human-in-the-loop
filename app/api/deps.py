from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.engine.workflow_engine import WorkflowEngine
from app.core.security import verify_api_key, get_current_actor


def get_workflow_engine(db: Session = Depends(get_db)) -> WorkflowEngine:
    """Dependency providing a WorkflowEngine bound to the active database session."""
    return WorkflowEngine(db=db)
