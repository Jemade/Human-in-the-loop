from app.models.workflow import WorkflowState
from app.models.approval import ApprovalStatus
from app.models.outbox import OutboxMessage


def test_workflow_rejection_path(engine, db):
    """
    Tests rejection flow:
    WAITING_FOR_APPROVAL -> REJECTED -> COMPLETED (graceful termination).
    Ensures external action is NEVER executed.
    """
    workflow = engine.create_workflow(task="Research Stripe and prepare an outreach email.")
    checkpointed = engine.run_until_checkpoint(workflow.id)
    assert checkpointed.current_state == WorkflowState.WAITING_FOR_APPROVAL.value

    approval = checkpointed.approvals[0]
    rejection_reason = "Outreach timing is bad; partner team is already in contact."

    # Execute human rejection
    rejected_workflow = engine.reject(
        approval_id=approval.id,
        actor="human:sales_lead",
        reason=rejection_reason,
    )

    # Verify workflow terminated gracefully
    assert rejected_workflow.current_state == WorkflowState.COMPLETED.value
    assert approval.status == ApprovalStatus.REJECTED.value
    assert approval.actor == "human:sales_lead"
    assert approval.decision_reason == rejection_reason
    assert approval.decided_at is not None

    # CRITICAL: Verify that NO external action was executed in outbox
    outbox = db.query(OutboxMessage).filter(OutboxMessage.workflow_id == workflow.id).first()
    assert outbox is None
