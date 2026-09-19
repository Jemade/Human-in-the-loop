from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    event_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    
    actor = Column(String(255), nullable=False)
    event_type = Column(String(100), nullable=False, index=True)
    from_state = Column(String(50), nullable=True)
    to_state = Column(String(50), nullable=True)
    
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    event_metadata = Column("metadata", JSON, nullable=True)

    # Relationships
    workflow = relationship("Workflow", back_populates="audit_events")

    def __repr__(self) -> str:
        return f"<AuditEvent id={self.event_id} type={self.event_type} actor={self.actor}>"
