from app.engine.idempotency import IdempotencyManager
from app.providers.email_provider import SandboxEmailProvider
from app.models.outbox import OutboxMessage


def test_idempotency_key_generation():
    action = {"tool": "send_email", "parameters": {"recipient": "test@test.com", "subject": "Test"}}
    key1 = IdempotencyManager.generate_key("wf-123", action)
    key2 = IdempotencyManager.generate_key("wf-123", action)
    assert key1 == key2
    assert key1.startswith("wf-123-act-")


def test_duplicate_external_action_prevention(db):
    """
    Verifies that calling the email provider with the same idempotency key
    does NOT produce a duplicate outbox record and safely returns ALREADY_SENT.
    """
    provider = SandboxEmailProvider()
    idempotency_key = "idemp-test-unique-key-456"

    # First dispatch
    result1 = provider.send_email(
        workflow_id="wf-test-1",
        idempotency_key=idempotency_key,
        recipient="user@example.com",
        subject="Hello",
        body="Message content",
        db=db,
    )
    assert result1["status"] == "SUCCESS"
    assert "message_id" in result1

    # Verify 1 record exists in outbox
    messages = db.query(OutboxMessage).filter(OutboxMessage.idempotency_key == idempotency_key).all()
    assert len(messages) == 1

    # Second dispatch with identical idempotency key (simulating network retry or duplicate approve)
    result2 = provider.send_email(
        workflow_id="wf-test-1",
        idempotency_key=idempotency_key,
        recipient="user@example.com",
        subject="Hello",
        body="Message content",
        db=db,
    )
    assert result2["status"] == "ALREADY_SENT"
    assert result2["idempotent"] is True
    assert result2["message_id"] == result1["message_id"]

    # Verify STILL only 1 record exists in outbox!
    messages_after = db.query(OutboxMessage).filter(OutboxMessage.idempotency_key == idempotency_key).all()
    assert len(messages_after) == 1
