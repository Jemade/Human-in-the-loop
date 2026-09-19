import hashlib
import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.outbox import OutboxMessage
from app.core.exceptions import DuplicateExecutionError


class IdempotencyManager:
    """
    Guarantees that external actions are executed exactly once, even across:
    - Process restarts
    - Retried approval API calls
    - Concurrent requests
    - Network timeouts and re-deliveries
    """

    @staticmethod
    def generate_key(workflow_id: str, action_data: Dict[str, Any]) -> str:
        """
        Generates a deterministic idempotency key based on workflow ID and action payload.
        Ensures identical actions within the same workflow resolve to the same key.
        """
        clean_wf = workflow_id.removeprefix("wf-")
        serialized = json.dumps(action_data, sort_keys=True)
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        return f"wf-{clean_wf}-act-{digest}"

    @classmethod
    def check_and_record(
        cls,
        db: Session,
        idempotency_key: str,
        workflow_id: str,
    ) -> Optional[OutboxMessage]:
        """
        Checks if an execution with the given idempotency key has already taken place.
        Returns the existing OutboxMessage if found, otherwise None.
        """
        existing = db.query(OutboxMessage).filter(
            OutboxMessage.idempotency_key == idempotency_key
        ).first()
        return existing

    @classmethod
    def assert_not_executed(
        cls,
        db: Session,
        idempotency_key: str,
    ) -> None:
        """
        Raises DuplicateExecutionError if the key has already been executed.
        """
        existing = db.query(OutboxMessage).filter(
            OutboxMessage.idempotency_key == idempotency_key
        ).first()
        if existing:
            raise DuplicateExecutionError(idempotency_key)
