from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class AuditEventResponse(BaseModel):
    event_id: str
    workflow_id: str
    actor: str
    event_type: str
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    timestamp: datetime
    metadata: Optional[Any] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
