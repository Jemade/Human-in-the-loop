from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.tools.base import ToolDefinition, RiskLevel, registry
from app.providers.email_provider import get_email_provider


class SendEmailInput(BaseModel):
    recipient: str = Field(..., description="Destination email address")
    subject: str = Field(..., description="Subject line of the email")
    body: str = Field(..., description="Body content of the email")
    workflow_id: str = Field(..., description="Workflow ID that initiated the action")
    idempotency_key: str = Field(..., description="Unique key preventing duplicate delivery")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Contextual metadata")
    db: Optional[Any] = Field(None, description="Active database session")

    model_config = ConfigDict(arbitrary_types_allowed=True)


def handle_send_email(
    recipient: str,
    subject: str,
    body: str,
    workflow_id: str,
    idempotency_key: str,
    metadata: Optional[Dict[str, Any]] = None,
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """Dispatches the email through the configured provider (Sandbox or SMTP)."""
    provider = get_email_provider()
    return provider.send_email(
        workflow_id=workflow_id,
        idempotency_key=idempotency_key,
        recipient=recipient,
        subject=subject,
        body=body,
        metadata=metadata,
        db=db,
    )


send_email_tool = ToolDefinition(
    name="send_email",
    description="Dispatches an external communication email to a recipient. Consequential action.",
    risk_level=RiskLevel.REQUIRES_APPROVAL,
    input_schema=SendEmailInput,
    handler=handle_send_email,
    requires_approval=True,
)

# Register high-risk external action tool
registry.register(send_email_tool)
