from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class OutboxMessage(Base):
    __tablename__ = "outbox_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)
    
    recipient = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="SENT")
    
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    metadata_json = Column("metadata", JSON, nullable=True)

    # Relationships
    workflow = relationship("Workflow", back_populates="outbox_messages")

    def __repr__(self) -> str:
        return f"<OutboxMessage id={self.id} recipient={self.recipient} status={self.status}>"
