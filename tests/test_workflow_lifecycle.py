from app.models.workflow import WorkflowState
from app.models.approval import ApprovalStatus
from app.models.outbox import OutboxMessage


def test_full_workflow_happy_path(engine, db):
    """
    Tests complete workflow lifecycle:
    CREATED -> PLANNING -> RESEARCHING -> DRAFTING -> WAITING_FOR_APPROVAL
    -> APPROVED -> EXECUTING -> COMPLETED
    """
    task = "Research Acme Corp and prepare an outreach email."
    
    # 1. Create workflow
    workflow = engine.create_workflow(task=task, title="Acme Outreach")
    assert workflow.current_state == WorkflowState.CREATED.value
    assert workflow.task == task

    # 2. Advance to approval gate checkpoint
    checkpointed = engine.run_until_checkpoint(workflow.id)
    assert checkpointed.current_state == WorkflowState.WAITING_FOR_APPROVAL.value
    assert checkpointed.plan is not None
    assert checkpointed.research_data is not None
    assert checkpointed.draft_action is not None

    # Verify an approval request was created
    approvals = checkpointed.approvals
    assert len(approvals) == 1
    approval = approvals[0]
    assert approval.status == ApprovalStatus.PENDING.value
    assert approval.proposed_action["tool"] == "send_email"
    assert "recipient" in approval.proposed_action["parameters"]
    assert "subject" in approval.proposed_action["parameters"]
    assert "body" in approval.proposed_action["parameters"]
    assert approval.risk_level == "REQUIRES_APPROVAL"
    assert len(approval.reason) > 0
    assert len(approval.consequences) > 0

    # 3. Human decision: Approve
    completed_workflow = engine.approve(
        approval_id=approval.id,
        actor="human:chief_risk_officer",
        reason="Target and messaging look great."
    )

    # 4. Verify completion
    assert completed_workflow.current_state == WorkflowState.COMPLETED.value
    assert completed_workflow.execution_result is not None
    assert completed_workflow.execution_result["status"] in ("SUCCESS", "ALREADY_SENT")

    # Verify external action in outbox
    outbox = db.query(OutboxMessage).filter(OutboxMessage.workflow_id == workflow.id).first()
    assert outbox is not None
    assert outbox.recipient == approval.proposed_action["parameters"]["recipient"]
    assert outbox.status == "DELIVERED_TO_SANDBOX"
