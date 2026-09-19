from datetime import datetime, timezone
import enum
import uuid
from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class WorkflowState(str, enum.Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    RESEARCHING = "RESEARCHING"
    DRAFTING = "DRAFTING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EDIT_REQUIRED = "EDIT_REQUIRED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    task = Column(Text, nullable=False)
    current_state = Column(String(50), nullable=False, default=WorkflowState.CREATED.value)
    
    # Checkpointed state components
    plan = Column(JSON, nullable=True)
    research_data = Column(JSON, nullable=True)
    draft_action = Column(JSON, nullable=True)
    execution_result = Column(JSON, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # Idempotency token for external actions
    idempotency_key = Column(String(128), unique=True, nullable=True, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    approvals = relationship("ApprovalRequest", back_populates="workflow", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="workflow", cascade="all, delete-orphan")
    outbox_messages = relationship("OutboxMessage", back_populates="workflow", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Workflow id={self.id} state={self.current_state}>"
