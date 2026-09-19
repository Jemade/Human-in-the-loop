import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.engine.workflow_engine import WorkflowEngine
from app.models.workflow import Workflow, WorkflowState
from app.models.outbox import OutboxMessage


def test_process_restart_and_resume(tmp_path):
    """
    Simulates a true backend crash/restart while a workflow is waiting for approval:
    1. Workflow runs and reaches WAITING_FOR_APPROVAL, persisted to disk.
    2. Process terminates (engine and session closed, memory cleared).
    3. New process starts, connects to the existing database on disk, loads state, and resumes.
    """
    db_file = tmp_path / "restart_test.db"
    db_url = f"sqlite:///{db_file}"

    engine1_db = create_engine(db_url)
    Base.metadata.create_all(bind=engine1_db)
    Session1 = sessionmaker(bind=engine1_db)

    # Phase 1: Process 1 executes until approval gate
    session1 = Session1()
    engine1 = WorkflowEngine(db=session1)
    workflow = engine1.create_workflow(task="Research Acme Corp and prepare an outreach email.")
    engine1.run_until_checkpoint(workflow.id)

    workflow_id = workflow.id
    approval_id = workflow.approvals[0].id
    original_plan = workflow.plan
    original_research = workflow.research_data
    original_draft = workflow.draft_action

    # Simulate hard process crash: close session, dispose engine, delete objects
    session1.close()
    engine1_db.dispose()
    del engine1
    del session1

    # Phase 2: Process 2 boots up from cold start
    engine2_db = create_engine(db_url)
    Session2 = sessionmaker(bind=engine2_db)
    session2 = Session2()

    try:
        engine2 = WorkflowEngine(db=session2)

        # Retrieve workflow from database
        recovered_wf = session2.query(Workflow).filter(Workflow.id == workflow_id).first()
        assert recovered_wf is not None
        assert recovered_wf.current_state == WorkflowState.WAITING_FOR_APPROVAL.value

        # Verify all state survived process death
        assert recovered_wf.plan == original_plan
        assert recovered_wf.research_data == original_research
        assert recovered_wf.draft_action == original_draft

        # Resume workflow by approving the pending approval request
        resumed_wf = engine2.approve(
            approval_id=approval_id,
            actor="human:resumed_operator",
            reason="Resumed after system reboot",
        )

        # Verify workflow continued to completion
        assert resumed_wf.current_state == WorkflowState.COMPLETED.value
        assert resumed_wf.execution_result is not None

        # Verify external action dispatched in outbox
        outbox = session2.query(OutboxMessage).filter(OutboxMessage.workflow_id == workflow_id).first()
        assert outbox is not None
        assert outbox.status == "DELIVERED_TO_SANDBOX"

    finally:
        session2.close()
        engine2_db.dispose()
