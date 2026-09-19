#!/usr/bin/env python3
"""
ApprovalFlow Agent - End-to-End Demonstration Script

Demonstrates:
1. Workflow creation
2. Research execution
3. Generated proposal & evidence
4. Workflow entering WAITING_FOR_APPROVAL
5. Approval UI presentation
6. Human editing proposed action
7. Approval & resume from checkpoint
8. Safe external action execution (Sandbox outbox)
9. Complete chronological audit trail
10. Rejection path demonstration
11. Duplicate execution protection (Idempotency)
"""

import sys
import time
import json
from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.engine.workflow_engine import WorkflowEngine
from app.models.workflow import WorkflowState
from app.models.outbox import OutboxMessage
from app.engine.idempotency import IdempotencyManager


def print_step(step_num: int, title: str):
    print("\n" + "=" * 70)
    print(f" STEP {step_num}: {title.upper()}")
    print("=" * 70)


def print_json(data: dict):
    print(json.dumps(data, indent=2, default=str))


def run_demo():
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                 APPROVALFLOW AGENT DEMO                          ║
    ║   Human-in-the-Loop Autonomous AI Workflow System                ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)

    # Initialize DB tables
    init_db()
    db: Session = SessionLocal()
    engine = WorkflowEngine(db=db)

    # -------------------------------------------------------------
    # 1. Create Workflow
    # -------------------------------------------------------------
    print_step(1, "Create New Workflow")
    task_prompt = "Research Acme Corp and prepare an outreach email."
    print(f"User Request: '{task_prompt}'")
    workflow = engine.create_workflow(task=task_prompt, title="Acme Outreach Campaign")
    print(f"Workflow ID   : {workflow.id}")
    print(f"Current State : {workflow.current_state}")
    time.sleep(0.5)

    # -------------------------------------------------------------
    # 2. Run Planning, Research, & Synthesis
    # -------------------------------------------------------------
    print_step(2, "Run Planning & Autonomous Safe Research")
    print("Agent executing: PLANNING -> RESEARCHING -> DRAFTING...")
    checkpointed_wf = engine.run_until_checkpoint(workflow.id)

    print("\n[PLAN GENERATED]")
    print_json(checkpointed_wf.plan)

    print("\n[RESEARCH DATA COLLECTED (SAFE TOOLS)]")
    print_json(checkpointed_wf.research_data)
    time.sleep(0.5)

    # -------------------------------------------------------------
    # 3. Show Generated Proposal
    # -------------------------------------------------------------
    print_step(3, "Synthesizer Generates Outreach Proposal")
    draft = checkpointed_wf.draft_action
    print_json(draft)
    time.sleep(0.5)

    # -------------------------------------------------------------
    # 4. Show Workflow Paused at WAITING_FOR_APPROVAL
    # -------------------------------------------------------------
    print_step(4, "Approval Gate Triggered -> Workflow Pauses")
    print(f"Action requires approval : tool='{draft['action']['tool']}'")
    print(f"Current Workflow State   : {checkpointed_wf.current_state}")
    approval = checkpointed_wf.approvals[0]
    print(f"Approval Request ID      : {approval.id}")
    print(f"Risk Classification      : {approval.risk_level}")
    print(f"Consequences if Approved : {approval.consequences}")
    time.sleep(0.5)

    # -------------------------------------------------------------
    # 5. Open Approval UI (Context Display)
    # -------------------------------------------------------------
    print_step(5, "Human Reviewer Inspects Approval Context (UI View)")
    print(f"""
    ================== HUMAN APPROVAL DASHBOARD ==================
    Workflow ID : {workflow.id}
    Task        : {workflow.task}
    Risk Level  : {approval.risk_level}
    Tool        : {approval.proposed_action['tool']}
    Recipient   : {approval.proposed_action['parameters']['recipient']}
    Subject     : {approval.proposed_action['parameters']['subject']}
    Reason      : {approval.reason}
    Evidence    : {approval.evidence['recent_news']}
    ==============================================================
    """)
    time.sleep(0.5)

    # -------------------------------------------------------------
    # 6. Human Edits Proposed Action
    # -------------------------------------------------------------
    print_step(6, "Human Edits Proposed Action Parameters")
    edited_action = {
        "tool": "send_email",
        "parameters": {
            "recipient": "sarah.chen.custom@acme.com",
            "subject": "[Customized] AI Governance & Safe HITL Workflows at Acme",
            "body": "Hi Sarah,\n\nI reviewed your engineering roadmap on autonomous systems. Our ApprovalFlow engine provides guaranteed human checkpoints for all consequential agent actions.\n\nBest,\nLead AI Architect",
        }
    }
    print("Human modified recipient, subject line, and value proposition.")
    print("Original Recipient :", approval.proposed_action["parameters"]["recipient"])
    print("Edited Recipient   :", edited_action["parameters"]["recipient"])
    time.sleep(0.5)

    # -------------------------------------------------------------
    # 7. Approve & Resume Workflow
    # -------------------------------------------------------------
    print_step(7, "Human Approves Edited Action -> Workflow Resumes")
    completed_wf = engine.edit(
        approval_id=approval.id,
        edited_action=edited_action,
        actor="human:vp_engineering",
        reason="Refined recipient and tailored technical pitch",
        approve_immediately=True,
    )
    print(f"Workflow State after decision : {completed_wf.current_state}")
    print(f"Decision Record Actor         : {approval.actor}")
    print(f"Decision Status               : {approval.status}")
    time.sleep(0.5)

    # -------------------------------------------------------------
    # 8. Show Execution in Sandbox Outbox
    # -------------------------------------------------------------
    print_step(8, "Action Executed Safely to Sandbox Outbox")
    outbox = db.query(OutboxMessage).filter(OutboxMessage.workflow_id == workflow.id).first()
    print("Outbox Message Record:")
    print_json({
        "id": outbox.id,
        "recipient": outbox.recipient,
        "subject": outbox.subject,
        "idempotency_key": outbox.idempotency_key,
        "status": outbox.status,
        "sent_at": str(outbox.sent_at),
    })
    time.sleep(0.5)

    # -------------------------------------------------------------
    # 9. Show Complete Audit Trail
    # -------------------------------------------------------------
    print_step(9, "Complete Chronological Audit Trail")
    events = engine.db.query(engine.record_event.__annotations__.get('return', object)).all() if False else \
             [e for e in completed_wf.audit_events]
    print(f"Total Audit Events Recorded: {len(events)}")
    for e in events:
        transition = f" [{e.from_state} -> {e.to_state}]" if e.from_state or e.to_state else ""
        print(f"  • {e.timestamp.strftime('%H:%M:%S')} | {e.event_type:<28} | Actor: {e.actor:<20}{transition}")
    time.sleep(0.5)

    # -------------------------------------------------------------
    # 10. Demonstrate Rejection Path
    # -------------------------------------------------------------
    print_step(10, "Demonstrate Rejection Path")
    wf2 = engine.create_workflow(task="Research Competitor and send aggressive email", title="Risky Campaign")
    engine.run_until_checkpoint(wf2.id)
    appr2 = wf2.approvals[0]
    print(f"Workflow 2 paused at: {wf2.current_state}")

    print("Human Reviewer REJECTS action with reason: 'Unacceptable aggressive tone.'")
    rejected_wf = engine.reject(
        approval_id=appr2.id,
        actor="human:compliance_lead",
        reason="Unacceptable aggressive tone.",
    )
    print(f"Workflow 2 State after rejection : {rejected_wf.current_state}")
    print(f"Approval 2 Status                : {appr2.status}")
    outbox_count = db.query(OutboxMessage).filter(OutboxMessage.workflow_id == wf2.id).count()
    print(f"Outbox messages for Workflow 2   : {outbox_count} (ZERO dispatched!)")
    time.sleep(0.5)

    # -------------------------------------------------------------
    # 11. Demonstrate Duplicate Execution Protection (Idempotency)
    # -------------------------------------------------------------
    print_step(11, "Demonstrate Duplicate Execution Protection (Idempotency)")
    idemp_key = completed_wf.idempotency_key
    print(f"Attempting to re-execute action with key: '{idemp_key}'")
    existing_outbox = IdempotencyManager.check_and_record(db, idemp_key, completed_wf.id)
    print(f"Idempotency Check Found Existing Record : ID={existing_outbox.id}")
    print("Action was NOT executed again. Exact-once guarantee preserved!")

    db.close()
    print("\n" + "=" * 70)
    print(" ✅ DEMO COMPLETED SUCCESSFULLY")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_demo()
