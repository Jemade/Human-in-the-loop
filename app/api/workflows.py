from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.workflow import Workflow
from app.models.audit import AuditEvent
from app.schemas.workflow import WorkflowCreate, WorkflowResponse, WorkflowSummary
from app.schemas.audit import AuditEventResponse
from app.engine.workflow_engine import WorkflowEngine
from app.api.deps import get_workflow_engine
from app.core.exceptions import WorkflowNotFoundError

router = APIRouter(prefix="/v1/workflows", tags=["Workflows"])


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_and_run_workflow(
    payload: WorkflowCreate,
    engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """
    Creates a new workflow and advances it through Planning, Research,
    and Drafting until it reaches an approval gate or completion.
    """
    workflow = engine.create_workflow(task=payload.task, title=payload.title)
    # Run synchronously to initial checkpoint (approval gate)
    checkpointed = engine.run_until_checkpoint(workflow.id)
    return checkpointed


@router.get("", response_model=List[WorkflowSummary])
def list_workflows(
    state: Optional[str] = Query(None, description="Filter by workflow state"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Lists workflows with optional state filtering and pagination."""
    query = db.query(Workflow)
    if state:
        query = query.filter(Workflow.current_state == state.upper())
    workflows = query.order_by(Workflow.created_at.desc()).offset(offset).limit(limit).all()
    return workflows


@router.get("/{id}", response_model=WorkflowResponse)
def get_workflow(
    id: str,
    db: Session = Depends(get_db),
):
    """Retrieves full details of a specific workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == id).first()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Workflow '{id}' not found.")
    return workflow


@router.get("/{id}/events", response_model=List[AuditEventResponse])
def get_workflow_events(
    id: str,
    db: Session = Depends(get_db),
):
    """Retrieves the complete, chronological audit trail for a workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == id).first()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Workflow '{id}' not found.")
    
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.workflow_id == id)
        .order_by(AuditEvent.timestamp.asc())
        .all()
    )
    
    # Map model attribute event_metadata to response field metadata
    return [
        AuditEventResponse(
            event_id=e.event_id,
            workflow_id=e.workflow_id,
            actor=e.actor,
            event_type=e.event_type,
            from_state=e.from_state,
            to_state=e.to_state,
            timestamp=e.timestamp,
            metadata=e.event_metadata,
        )
        for e in events
    ]
