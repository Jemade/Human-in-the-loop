from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class ApprovalResponse(BaseModel):
    id: str
    workflow_id: str
    status: str
    proposed_action: Dict[str, Any]
    edited_action: Optional[Dict[str, Any]] = None
    reason: str
    evidence: Optional[Any] = None
    consequences: str
    risk_level: str
    actor: Optional[str] = None
    decision_reason: Optional[str] = None
    requested_at: datetime
    decided_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ApproveRequest(BaseModel):
    actor: Optional[str] = Field(None, description="Identifier of the human reviewer (defaults to current user/header)")
    reason: Optional[str] = Field(None, description="Optional notes on why the action was approved")


class RejectRequest(BaseModel):
    actor: Optional[str] = Field(None, description="Identifier of the human reviewer")
    reason: str = Field(..., description="Mandatory reason explaining why the action was rejected", min_length=2)


class EditRequest(BaseModel):
    actor: Optional[str] = Field(None, description="Identifier of the human reviewer")
    edited_action: Dict[str, Any] = Field(..., description="Human-modified parameters for the action")
    reason: Optional[str] = Field(None, description="Notes on why the edit was made")
    approve_immediately: bool = Field(
        True,
        description="If True, marks as approved with edited parameters and resumes workflow; if False, leaves in EDIT_REQUIRED state"
    )
