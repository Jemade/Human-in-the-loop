from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class WorkflowCreate(BaseModel):
    task: str = Field(..., description="The high-level prompt or goal for the agent workflow", min_length=3)
    title: Optional[str] = Field(None, description="Optional title; auto-generated if omitted")


class WorkflowResponse(BaseModel):
    id: str
    title: str
    task: str
    current_state: str
    plan: Optional[Any] = None
    research_data: Optional[Any] = None
    draft_action: Optional[Any] = None
    execution_result: Optional[Any] = None
    error_details: Optional[Any] = None
    idempotency_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowSummary(BaseModel):
    id: str
    title: str
    task: str
    current_state: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
