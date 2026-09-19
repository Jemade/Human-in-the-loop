# ApprovalFlow Architecture Document

This document provides the technical design decisions, engineering rationale, and safety foundations underlying the **ApprovalFlow Agent** system.

---

## 1. Why State Is Persisted to the Database

In autonomous AI systems, treating workflow state as ephemeral Python memory is an anti-pattern that creates severe operational vulnerabilities:

1. **Surviving Process Restarts & Crashes**: Network interruptions, server reboots, worker restarts, or deployment rolling updates must never destroy a workflow mid-execution or discard a human's pending approval checkpoint.
2. **Deterministic Checkpointing**: By serializing intermediate artifacts (`plan`, `research_data`, `draft_action`, `execution_result`) into persistent storage (PostgreSQL/SQLite), the system establishes immutable checkpoints.
3. **Auditability & Regulatory Compliance**: Consequential actions require verifiable proofs of what the model observed before it requested authorization. Database persistence guarantees that prompt hallucinations or transient states can be audited post hoc.

```
[Client] ──> [Engine] ──> [DB: Workflows & Checkpoints]
                              │
                    (Server Reboot Occurs)
                              │
[Human Reviewer] ──> [Engine] ──> [DB: Resumes from Checkpoint]
```

---

## 2. Why Approvals Are Explicit

Many naive AI systems attempt to enforce safety through prompt engineering (e.g., instructing the LLM: *"Ask the user before taking action"*). This approach is fundamentally flawed:

- **Prompt Injections & Drift**: LLMs can be tricked into ignoring conversational instructions or bypassing soft guardrails.
- **Unbounded Execution**: A model executing in an unconstrained loop can invoke destructive tools without the host application knowing until after the fact.
- **Ambiguous Checkpoints**: Prompts cannot provide a reliable HTTP contract for enterprise approval dashboards.

**The ApprovalFlow Solution**:
Approvals are **hard mechanical boundaries** governed by an explicit state machine. When an agent proposes a high-risk tool (`send_email`, `make_purchase`, `delete_record`), the workflow engine halts execution, transitions the workflow state to `WAITING_FOR_APPROVAL`, commits the checkpoint to the database, and exposes an approval resource via `POST /v1/approvals/{id}/approve`. Execution cannot proceed until a valid human authorization token is received.

---

## 3. Why Risk Is Defined as Tool Metadata

Rather than hardcoding tool permissions or embedding policy logic inside individual agents, ApprovalFlow uses a **Tool Safety Registry**:

```python
class RiskLevel(str, enum.Enum):
    SAFE = "SAFE"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"

class ToolDefinition:
    name: str
    description: str
    risk_level: RiskLevel
    requires_approval: bool
    input_schema: Type[BaseModel]
    handler: Callable
```

### Key Advantages:
1. **Decoupled Governance**: Policy is centralized in code, independent of LLM prompts.
2. **Runtime Policy Enforcement**: The workflow engine inspects `tool.requires_approval` before dispatching any tool. If `True`, the engine halts and routes to the approval gate automatically.
3. **Pluggable Tools**: Adding new tools (e.g., `execute_sql_query`, `issue_refund`) requires declaring their safety metadata upfront, preventing accidental exposure of ungated destructive tools.

---

## 4. Why External Actions Require Idempotency

When an action crosses the boundary from the agent into the external world (e.g., dispatching an email, transferring funds, updating a remote CRM), **network retries, concurrent approvals, and UI double-clicks** can trigger catastrophic duplicate operations.

### The Idempotency Mechanism:
1. **Deterministic Key Generation**: An idempotency key is derived deterministically from the workflow ID and the action payload:
   $$\text{Key} = \text{SHA256}(\text{WorkflowID} + \text{SerializedAction})[:16]$$
2. **Database-Level Unique Constraint**: The `outbox_messages` table enforces a `UNIQUE` constraint on `idempotency_key`.
3. **Pre-Execution Check**: Before executing the external action, the engine queries the outbox for an existing execution matching the key. If present, the existing execution receipt is returned immediately with `status: ALREADY_SENT`, preventing duplicate transmission.

---

## 5. How the Workflow Resumes

When a human reviewer approves or edits an action via the API or UI:

1. **State Transition**: The workflow transitions from `WAITING_FOR_APPROVAL` to `APPROVED` (or `EDIT_REQUIRED` $\rightarrow$ `APPROVED`).
2. **No Re-Planning**: The engine does not restart the workflow from `CREATED` or re-execute planning or research. It loads the persisted `draft_action` (or human-modified `edited_action`) directly from the database.
3. **Execution**: The approved parameters are passed to `registry.execute(tool_name, **params)`.
4. **Observation & Completion**: The execution receipt is recorded in `workflow.execution_result`, an audit event is logged, and the workflow transitions to `COMPLETED`.

---

## 6. State Transition Matrix

| Current State | Allowed Next States | Trigger / Description |
|---|---|---|
| `CREATED` | `PLANNING`, `FAILED` | Workflow initiated |
| `PLANNING` | `RESEARCHING`, `FAILED` | Plan generated by LLM |
| `RESEARCHING` | `DRAFTING`, `FAILED` | Safe research tools executed |
| `DRAFTING` | `WAITING_FOR_APPROVAL`, `EXECUTING`, `FAILED` | Action proposed; halted if high-risk |
| `WAITING_FOR_APPROVAL` | `APPROVED`, `REJECTED`, `EDIT_REQUIRED`, `FAILED` | Human decision gate |
| `EDIT_REQUIRED` | `APPROVED`, `REJECTED`, `WAITING_FOR_APPROVAL`, `FAILED` | Action modified by human |
| `APPROVED` | `EXECUTING`, `FAILED` | Resumed for execution |
| `REJECTED` | `COMPLETED`, `PLANNING`, `FAILED` | Graceful termination or re-plan |
| `EXECUTING` | `COMPLETED`, `FAILED` | External action executed |
| `COMPLETED` | *(None - Terminal)* | Final state |
| `FAILED` | `PLANNING` | Retry state |
