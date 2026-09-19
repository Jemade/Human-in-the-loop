from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.outbox import OutboxMessage
from app.schemas.outbox import OutboxMessageResponse

router = APIRouter(prefix="/v1/outbox", tags=["Outbox / Sandbox"])


@router.get("", response_model=List[OutboxMessageResponse])
def list_outbox(db: Session = Depends(get_db)):
    """Lists all outgoing messages captured in the sandbox outbox."""
    messages = db.query(OutboxMessage).order_by(OutboxMessage.sent_at.desc()).all()
    return [
        OutboxMessageResponse(
            id=m.id,
            workflow_id=m.workflow_id,
            idempotency_key=m.idempotency_key,
            recipient=m.recipient,
            subject=m.subject,
            body=m.body,
            status=m.status,
            sent_at=m.sent_at,
            metadata=m.metadata_json,
        )
        for m in messages
    ]


@router.get("/{id}", response_model=OutboxMessageResponse)
def get_outbox_message(id: str, db: Session = Depends(get_db)):
    """Retrieves details of a captured sandbox message."""
    message = db.query(OutboxMessage).filter(OutboxMessage.id == id).first()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Outbox message '{id}' not found.")
    return OutboxMessageResponse(
        id=message.id,
        workflow_id=message.workflow_id,
        idempotency_key=message.idempotency_key,
        recipient=message.recipient,
        subject=message.subject,
        body=message.body,
        status=message.status,
        sent_at=message.sent_at,
        metadata=message.metadata_json,
    )
