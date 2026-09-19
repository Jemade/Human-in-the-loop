from app.models.workflow import WorkflowState
from app.models.approval import ApprovalStatus
from app.models.outbox import OutboxMessage


def test_workflow_edit_and_approve(engine, db):
    """
    Tests human modification of proposed action:
    Agent proposes action -> Human modifies parameters -> Workflow executes edited version.
    Verifies that both original and edited versions are preserved.
    """
    workflow = engine.create_workflow(task="Research Acme Corp and prepare an outreach email.")
    checkpointed = engine.run_until_checkpoint(workflow.id)
    assert checkpointed.current_state == WorkflowState.WAITING_FOR_APPROVAL.value

    approval = checkpointed.approvals[0]
    original_action = approval.proposed_action

    # Human edits recipient, subject, and body
    edited_action = {
        "tool": "send_email",
        "parameters": {
            "recipient": "custom.director@acme.com",
            "subject": "Customized Partnership Discussion - AI Governance",
            "body": "Hi Director, this is a hand-crafted custom message addressing your specific roadmap.",
        }
    }

    # Execute human edit & immediate approval
    completed_workflow = engine.edit(
        approval_id=approval.id,
        edited_action=edited_action,
        actor="human:vp_growth",
        reason="Targeting custom director instead of general inbox",
        approve_immediately=True,
    )

    # Verify workflow completed
    assert completed_workflow.current_state == WorkflowState.COMPLETED.value

    # Verify approval record preserves BOTH versions
    assert approval.status == ApprovalStatus.EDITED.value
    assert approval.proposed_action == original_action
    assert approval.edited_action == edited_action
    assert approval.actor == "human:vp_growth"

    # Verify that the external action in the outbox used the EDITED parameters!
    outbox = db.query(OutboxMessage).filter(OutboxMessage.workflow_id == workflow.id).first()
    assert outbox is not None
    assert outbox.recipient == "custom.director@acme.com"
    assert outbox.subject == "Customized Partnership Discussion - AI Governance"
    assert "hand-crafted custom message" in outbox.body
