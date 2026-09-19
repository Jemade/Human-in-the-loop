from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class OutboxMessageResponse(BaseModel):
    id: str
    workflow_id: str
    idempotency_key: str
    recipient: str
    subject: str
    body: str
    status: str
    sent_at: datetime
    metadata: Optional[Any] = None

    model_config = ConfigDict(from_attributes=True)
