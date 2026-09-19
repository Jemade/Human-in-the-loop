from datetime import datetime, timezone
import enum
import uuid
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EDITED = "EDITED"


class ApprovalRequest(Base):
    __tablename__ = "approvals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    
    status = Column(String(50), nullable=False, default=ApprovalStatus.PENDING.value, index=True)
    
    # Details required by the human approval gate
    proposed_action = Column(JSON, nullable=False)   # What the agent wants to do
    edited_action = Column(JSON, nullable=True)      # Human-modified action (if edited)
    reason = Column(Text, nullable=False)            # Why it wants to do it
    evidence = Column(JSON, nullable=True)           # Information & sources used
    consequences = Column(Text, nullable=False)      # What will happen if approved
    risk_level = Column(String(50), nullable=False)  # Risk classification (e.g. REQUIRES_APPROVAL / HIGH)
    
    # Audit information for decision
    actor = Column(String(255), nullable=True)       # Identity of human or system reviewer
    decision_reason = Column(Text, nullable=True)    # Justification provided by reviewer
    
    requested_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    decided_at = Column(DateTime, nullable=True)

    # Relationships
    workflow = relationship("Workflow", back_populates="approvals")

    def __repr__(self) -> str:
        return f"<ApprovalRequest id={self.id} workflow_id={self.workflow_id} status={self.status}>"
