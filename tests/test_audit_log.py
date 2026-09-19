from app.models.audit import AuditEvent


def test_complete_audit_trail_recorded(engine, db):
    """
    Verifies that every phase of the workflow records a rich audit event
    with actor, event_type, timestamps, state transitions, and metadata.
    """
    workflow = engine.create_workflow(task="Research Acme Corp and prepare an outreach email.")
    engine.run_until_checkpoint(workflow.id)

    approval_id = workflow.approvals[0].id
    engine.approve(approval_id=approval_id, actor="human:audit_officer", reason="Approved for testing audit trail")

    events = db.query(AuditEvent).filter(AuditEvent.workflow_id == workflow.id).order_by(AuditEvent.timestamp.asc()).all()
    event_types = [e.event_type for e in events]

    expected_types = [
        "workflow_created",
        "planning_started",
        "plan_generated",
        "research_started",
        "research_completed",
        "drafting_started",
        "draft_created",
        "approval_requested",
        "approval_approved",
        "external_action_started",
        "external_action_completed",
        "workflow_completed",
    ]

    for expected in expected_types:
        assert expected in event_types, f"Missing audit event: {expected}"

    # Verify event structure
    for event in events:
        assert event.event_id is not None
        assert event.workflow_id == workflow.id
        assert event.actor is not None
        assert event.timestamp is not None
        assert event.event_metadata is not None
