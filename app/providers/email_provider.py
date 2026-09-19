from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.outbox import OutboxMessage

settings = get_settings()


class EmailProvider(ABC):
    """Abstract interface for external communication."""

    @abstractmethod
    def send_email(
        self,
        workflow_id: str,
        idempotency_key: str,
        recipient: str,
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Dispatch email and return execution summary."""
        pass


class SandboxEmailProvider(EmailProvider):
    """
    Safe test sandbox provider.
    
    Instead of delivering real emails across the internet, this provider:
    1. Persists the outgoing email to the `outbox_messages` database table.
    2. Enforces unique idempotency_key constraint.
    3. Returns a complete execution receipt.
    
    This ensures 100% safe local development and demo testing.
    """

    def send_email(
        self,
        workflow_id: str,
        idempotency_key: str,
        recipient: str,
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        if db is None:
            from app.database import SessionLocal
            session = SessionLocal()
            close_session = True
        else:
            session = db
            close_session = False

        try:
            # Check if an outbox message with this idempotency_key already exists
            existing = session.query(OutboxMessage).filter(OutboxMessage.idempotency_key == idempotency_key).first()
            if existing:
                return {
                    "status": "ALREADY_SENT",
                    "idempotent": True,
                    "message_id": existing.id,
                    "recipient": existing.recipient,
                    "subject": existing.subject,
                    "sent_at": existing.sent_at.isoformat(),
                    "provider": "sandbox",
                }

            outbox_entry = OutboxMessage(
                workflow_id=workflow_id,
                idempotency_key=idempotency_key,
                recipient=recipient,
                subject=subject,
                body=body,
                status="DELIVERED_TO_SANDBOX",
                metadata_json=metadata or {},
                sent_at=datetime.now(timezone.utc),
            )
            session.add(outbox_entry)
            session.commit()
            session.refresh(outbox_entry)

            return {
                "status": "SUCCESS",
                "message_id": outbox_entry.id,
                "recipient": recipient,
                "subject": subject,
                "sent_at": outbox_entry.sent_at.isoformat(),
                "provider": "sandbox",
                "note": "Delivered to local sandbox outbox (no real email transmitted)",
            }
        finally:
            if close_session:
                session.close()


class SmtpEmailProvider(EmailProvider):
    """Real SMTP email provider (for staging/production)."""

    def send_email(
        self,
        workflow_id: str,
        idempotency_key: str,
        recipient: str,
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        # Also record in outbox for auditability
        sandbox_backup = SandboxEmailProvider()
        sandbox_receipt = sandbox_backup.send_email(
            workflow_id=workflow_id,
            idempotency_key=idempotency_key,
            recipient=recipient,
            subject=subject,
            body=body,
            metadata=metadata,
            db=db,
        )

        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            sandbox_receipt["smtp_status"] = "SENT_VIA_SMTP"
            return sandbox_receipt
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
                "sandbox_receipt": sandbox_receipt,
            }


def get_email_provider() -> EmailProvider:
    """Factory returning configured email provider."""
    if settings.EMAIL_PROVIDER.lower() == "smtp":
        return SmtpEmailProvider()
    return SandboxEmailProvider()
