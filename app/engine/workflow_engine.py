from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.workflow import Workflow, WorkflowState
from app.models.approval import ApprovalRequest, ApprovalStatus
from app.models.audit import AuditEvent
from app.core.state_machine import StateMachine
from app.core.exceptions import (
    WorkflowNotFoundError,
    ApprovalNotFoundError,
    InvalidStateTransitionError,
)
from app.tools.base import registry
from app.providers.llm_provider import get_llm_provider
from app.engine.idempotency import IdempotencyManager


class WorkflowEngine:
    """
    Core execution engine for ApprovalFlow.
    
    Orchestrates the plan-act-observe loop:
    1. CREATED -> PLANNING (LLM plan generation)
    2. PLANNING -> RESEARCHING (Safe intelligence tools)
    3. RESEARCHING -> DRAFTING (Outreach synthesis)
    4. DRAFTING -> WAITING_FOR_APPROVAL (Approval Gate triggered for high-risk actions)
    5. WAITING_FOR_APPROVAL -> APPROVED / REJECTED / EDIT_REQUIRED (Human decision)
    6. APPROVED -> EXECUTING (Idempotent external dispatch)
    7. EXECUTING -> COMPLETED (Final observation)
    """

    def __init__(self, db: Session):
        self.db = db
        self.llm = get_llm_provider()

    # --- Audit Trail Helper ---
    def record_event(
        self,
        workflow_id: str,
        actor: str,
        event_type: str,
        from_state: Optional[str] = None,
        to_state: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Appends an immutable audit event to the audit trail."""
        event = AuditEvent(
            workflow_id=workflow_id,
            actor=actor,
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
            event_metadata=metadata or {},
            timestamp=datetime.now(timezone.utc),
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    # --- Transition Helper ---
    def transition(
        self,
        workflow: Workflow,
        to_state: WorkflowState,
        actor: str = "system:engine",
        event_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Validates and executes a state transition, logging it to the audit trail."""
        from_state_val = workflow.current_state
        to_state_val = to_state.value

        StateMachine.validate_transition(from_state_val, to_state_val)
        
        workflow.current_state = to_state_val
        workflow.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(workflow)

        evt_type = event_type or f"state_transition_{to_state_val.lower()}"
        self.record_event(
            workflow_id=workflow.id,
            actor=actor,
            event_type=evt_type,
            from_state=from_state_val,
            to_state=to_state_val,
            metadata=metadata,
        )

    # --- Workflow Lifecycle Methods ---

    def create_workflow(self, task: str, title: Optional[str] = None) -> Workflow:
        """Initializes a new workflow in CREATED state."""
        clean_title = title.strip() if title and title.strip() else f"Task: {task[:50]}..."
        workflow = Workflow(
            title=clean_title,
            task=task.strip(),
            current_state=WorkflowState.CREATED.value,
        )
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)

        self.record_event(
            workflow_id=workflow.id,
            actor="user:creator",
            event_type="workflow_created",
            to_state=WorkflowState.CREATED.value,
            metadata={"task": workflow.task, "title": workflow.title},
        )
        return workflow

    def run_until_checkpoint(self, workflow_id: str) -> Workflow:
        """
        Executes workflow from CREATED / PLANNING through to the approval gate.
        Pauses and persists state when a high-risk tool is encountered.
        """
        workflow = self.db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise WorkflowNotFoundError(workflow_id)

        try:
            # 1. CREATED -> PLANNING
            if workflow.current_state == WorkflowState.CREATED.value:
                self.transition(workflow, WorkflowState.PLANNING, actor="agent:planner", event_type="planning_started")
                plan = self.llm.generate_plan(workflow.task)
                workflow.plan = plan
                self.db.commit()
                self.record_event(
                    workflow_id=workflow.id,
                    actor="agent:planner",
                    event_type="plan_generated",
                    metadata={"plan": plan},
                )

            # 2. PLANNING -> RESEARCHING
            if workflow.current_state == WorkflowState.PLANNING.value:
                self.transition(workflow, WorkflowState.RESEARCHING, actor="agent:researcher", event_type="research_started")
                # Execute safe research tools
                company_target = workflow.plan.get("target", "Acme Corp") if workflow.plan else "Acme Corp"
                research_result = registry.execute("search_company_web", company_name=company_target)
                extracted = registry.execute(
                    "extract_company_profile",
                    company_name=company_target,
                    raw_notes=str(research_result)
                )
                combined_research = {**research_result, "extracted_profile": extracted}
                workflow.research_data = combined_research
                self.db.commit()
                self.record_event(
                    workflow_id=workflow.id,
                    actor="agent:researcher",
                    event_type="research_completed",
                    metadata={"research_summary": combined_research},
                )

            # 3. RESEARCHING -> DRAFTING
            if workflow.current_state == WorkflowState.RESEARCHING.value:
                self.transition(workflow, WorkflowState.DRAFTING, actor="agent:synthesizer", event_type="drafting_started")
                draft = self.llm.draft_outreach(workflow.task, workflow.research_data or {})
                workflow.draft_action = draft
                self.db.commit()
                self.record_event(
                    workflow_id=workflow.id,
                    actor="agent:synthesizer",
                    event_type="draft_created",
                    metadata={"draft_action": draft},
                )

            # 4. Action Risk Evaluation & Approval Gate Check
            if workflow.current_state == WorkflowState.DRAFTING.value:
                action_info = workflow.draft_action.get("action", {})
                tool_name = action_info.get("tool", "send_email")

                # Check safety classification via registry
                requires_approval = registry.requires_approval(tool_name)

                if requires_approval:
                    # HALT AT GATE: Transition to WAITING_FOR_APPROVAL
                    self.transition(
                        workflow,
                        WorkflowState.WAITING_FOR_APPROVAL,
                        actor="system:approval_gate",
                        event_type="approval_requested",
                        metadata={
                            "tool": tool_name,
                            "reason": workflow.draft_action.get("reason"),
                            "consequences": workflow.draft_action.get("consequences"),
                            "risk_level": workflow.draft_action.get("risk_level"),
                        },
                    )

                    # Persist ApprovalRequest in database
                    approval = ApprovalRequest(
                        workflow_id=workflow.id,
                        status=ApprovalStatus.PENDING.value,
                        proposed_action=action_info,
                        reason=workflow.draft_action.get("reason", "Outreach proposal based on research"),
                        evidence=workflow.draft_action.get("evidence", {}),
                        consequences=workflow.draft_action.get("consequences", "External message dispatch"),
                        risk_level=workflow.draft_action.get("risk_level", "REQUIRES_APPROVAL"),
                    )
                    self.db.add(approval)
                    self.db.commit()
                    self.db.refresh(approval)
                    return workflow
                else:
                    # Safe action: Direct execution without human gate
                    self.transition(workflow, WorkflowState.EXECUTING, actor="agent:executor")
                    exec_result = registry.execute(tool_name, **action_info.get("parameters", {}))
                    workflow.execution_result = exec_result
                    self.transition(workflow, WorkflowState.COMPLETED, actor="agent:observer")
                    return workflow

            return workflow

        except Exception as e:
            workflow.error_details = {"error": str(e), "failed_at": datetime.now(timezone.utc).isoformat()}
            self.db.commit()
            if StateMachine.can_transition(workflow.current_state, WorkflowState.FAILED):
                self.transition(
                    workflow,
                    WorkflowState.FAILED,
                    actor="system:engine",
                    event_type="workflow_failed",
                    metadata={"error": str(e)},
                )
            raise

    def approve(
        self,
        approval_id: str,
        actor: str = "human:reviewer",
        reason: Optional[str] = None,
    ) -> Workflow:
        """
        Approves an approval request and resumes execution of the approved action.
        """
        approval = self.db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
        if not approval:
            raise ApprovalNotFoundError(approval_id)

        workflow = approval.workflow
        if not workflow:
            raise WorkflowNotFoundError(approval.workflow_id)

        # Update approval record
        approval.status = ApprovalStatus.APPROVED.value
        approval.actor = actor
        approval.decision_reason = reason
        approval.decided_at = datetime.now(timezone.utc)
        self.db.commit()

        # Transition workflow to APPROVED
        self.transition(
            workflow,
            WorkflowState.APPROVED,
            actor=actor,
            event_type="approval_approved",
            metadata={"approval_id": approval.id, "reason": reason, "actor": actor},
        )

        # Resume execution
        return self.execute_approved_action(workflow, approval, actor=actor)

    def reject(
        self,
        approval_id: str,
        actor: str = "human:reviewer",
        reason: str = "Rejected by human reviewer",
    ) -> Workflow:
        """
        Rejects an approval request and terminates the workflow gracefully.
        """
        approval = self.db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
        if not approval:
            raise ApprovalNotFoundError(approval_id)

        workflow = approval.workflow
        if not workflow:
            raise WorkflowNotFoundError(approval.workflow_id)

        approval.status = ApprovalStatus.REJECTED.value
        approval.actor = actor
        approval.decision_reason = reason
        approval.decided_at = datetime.now(timezone.utc)
        self.db.commit()

        # Transition to REJECTED
        self.transition(
            workflow,
            WorkflowState.REJECTED,
            actor=actor,
            event_type="approval_rejected",
            metadata={"approval_id": approval.id, "reason": reason, "actor": actor},
        )

        # Gracefully terminate into COMPLETED (rejected termination)
        self.transition(
            workflow,
            WorkflowState.COMPLETED,
            actor="system:engine",
            event_type="workflow_completed_rejected",
            metadata={"final_status": "REJECTED", "reason": reason},
        )
        return workflow

    def edit(
        self,
        approval_id: str,
        edited_action: Dict[str, Any],
        actor: str = "human:reviewer",
        reason: Optional[str] = None,
        approve_immediately: bool = True,
    ) -> Workflow:
        """
        Allows human to modify the proposed action parameters.
        Preserves both the original proposal and the edited version.
        """
        approval = self.db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
        if not approval:
            raise ApprovalNotFoundError(approval_id)

        workflow = approval.workflow
        if not workflow:
            raise WorkflowNotFoundError(approval.workflow_id)

        # Store edited action
        approval.edited_action = edited_action
        self.db.commit()

        # Transition to EDIT_REQUIRED
        self.transition(
            workflow,
            WorkflowState.EDIT_REQUIRED,
            actor=actor,
            event_type="action_edited",
            metadata={
                "original_action": approval.proposed_action,
                "edited_action": edited_action,
                "edit_reason": reason,
                "actor": actor,
            },
        )

        if approve_immediately:
            # Mark approval status as EDITED and transition to APPROVED
            approval.status = ApprovalStatus.EDITED.value
            approval.actor = actor
            approval.decision_reason = reason or "Edited and approved by human reviewer"
            approval.decided_at = datetime.now(timezone.utc)
            self.db.commit()

            self.transition(
                workflow,
                WorkflowState.APPROVED,
                actor=actor,
                event_type="approval_approved_edited",
                metadata={"approval_id": approval.id, "edited": True, "actor": actor},
            )

            # Resume execution with edited action
            return self.execute_approved_action(workflow, approval, actor=actor)

        return workflow

    def execute_approved_action(
        self,
        workflow: Workflow,
        approval: ApprovalRequest,
        actor: str = "system:executor",
    ) -> Workflow:
        """
        Executes the approved (or human-edited) action with strict idempotency protection.
        """
        # 1. APPROVED -> EXECUTING
        self.transition(
            workflow,
            WorkflowState.EXECUTING,
            actor=actor,
            event_type="external_action_started",
        )

        # Determine final action parameters (edited take precedence over original)
        action_spec = approval.edited_action or approval.proposed_action
        tool_name = action_spec.get("tool", "send_email")
        params = dict(action_spec.get("parameters", {}))

        # Generate / verify idempotency key
        idempotency_key = workflow.idempotency_key or IdempotencyManager.generate_key(
            workflow_id=workflow.id,
            action_data=action_spec
        )
        workflow.idempotency_key = idempotency_key
        self.db.commit()

        # Inject workflow_id and idempotency_key into tool parameters
        params["workflow_id"] = workflow.id
        params["idempotency_key"] = idempotency_key
        params["db"] = self.db

        # Execute external action through registry
        try:
            result = registry.execute(tool_name, **params)
            workflow.execution_result = result
            self.db.commit()

            self.record_event(
                workflow_id=workflow.id,
                actor="system:executor",
                event_type="external_action_completed",
                metadata={"tool": tool_name, "execution_result": result, "idempotency_key": idempotency_key},
            )

            # 2. EXECUTING -> COMPLETED
            self.transition(
                workflow,
                WorkflowState.COMPLETED,
                actor="system:observer",
                event_type="workflow_completed",
                metadata={"final_result": result},
            )
            return workflow

        except Exception as e:
            workflow.error_details = {"error": str(e), "failed_at": datetime.now(timezone.utc).isoformat()}
            self.db.commit()
            self.transition(
                workflow,
                WorkflowState.FAILED,
                actor="system:executor",
                event_type="external_action_failed",
                metadata={"error": str(e)},
            )
            raise
