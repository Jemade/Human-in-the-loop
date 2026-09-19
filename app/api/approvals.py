from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.approval import ApprovalRequest
from app.schemas.approval import (
    ApprovalResponse,
    ApproveRequest,
    RejectRequest,
    EditRequest,
)
from app.schemas.workflow import WorkflowResponse
from app.engine.workflow_engine import WorkflowEngine
from app.api.deps import get_workflow_engine
from app.core.security import verify_api_key, get_current_actor
from app.core.exceptions import ApprovalNotFoundError, InvalidStateTransitionError

router = APIRouter(prefix="/v1/approvals", tags=["Approvals"])


@router.get("", response_model=List[ApprovalResponse])
def list_approvals(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (PENDING, APPROVED, REJECTED, EDITED)"),
    db: Session = Depends(get_db),
):
    """Lists all approval requests, optionally filtered by status."""
    query = db.query(ApprovalRequest)
    if status_filter:
        query = query.filter(ApprovalRequest.status == status_filter.upper())
    approvals = query.order_by(ApprovalRequest.requested_at.desc()).all()
    return approvals


@router.get("/{id}", response_model=ApprovalResponse)
def get_approval(
    id: str,
    db: Session = Depends(get_db),
):
    """Retrieves specific approval request details."""
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == id).first()
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval '{id}' not found.")
    return approval


@router.post("/{id}/approve", response_model=WorkflowResponse)
def approve_action(
    id: str,
    payload: ApproveRequest = ApproveRequest(),
    engine: WorkflowEngine = Depends(get_workflow_engine),
    _authorized: bool = Depends(verify_api_key),
    current_actor: str = Depends(get_current_actor),
):
    """
    Approves the proposed action and resumes the workflow to execute it.
    """
    actor = payload.actor or current_actor
    try:
        workflow = engine.approve(approval_id=id, actor=actor, reason=payload.reason)
        return workflow
    except ApprovalNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval '{id}' not found.")
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{id}/reject", response_model=WorkflowResponse)
def reject_action(
    id: str,
    payload: RejectRequest,
    engine: WorkflowEngine = Depends(get_workflow_engine),
    _authorized: bool = Depends(verify_api_key),
    current_actor: str = Depends(get_current_actor),
):
    """
    Rejects the proposed action, recording the reason and actor, and terminates the workflow.
    """
    actor = payload.actor or current_actor
    try:
        workflow = engine.reject(approval_id=id, actor=actor, reason=payload.reason)
        return workflow
    except ApprovalNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval '{id}' not found.")
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{id}/edit", response_model=WorkflowResponse)
def edit_action(
    id: str,
    payload: EditRequest,
    engine: WorkflowEngine = Depends(get_workflow_engine),
    _authorized: bool = Depends(verify_api_key),
    current_actor: str = Depends(get_current_actor),
):
    """
    Modifies proposed action parameters, recording both original and edited versions,
    and resumes execution if approve_immediately is True.
    """
    actor = payload.actor or current_actor
    try:
        workflow = engine.edit(
            approval_id=id,
            edited_action=payload.edited_action,
            actor=actor,
            reason=payload.reason,
            approve_immediately=payload.approve_immediately,
        )
        return workflow
    except ApprovalNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval '{id}' not found.")
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
