// ApprovalFlow Agent - Frontend Logic

const API_BASE = window.location.origin;

// State Cache
let activeApprovals = [];
let allWorkflows = [];
let outboxMessages = [];
let selectedWorkflowId = null;

// DOM Elements
const approvalsList = document.getElementById("approvals-list");
const approvalsCount = document.getElementById("approvals-count");
const workflowsTableBody = document.getElementById("workflows-table-body");
const auditTimeline = document.getElementById("audit-timeline");
const outboxTableBody = document.getElementById("outbox-table-body");
const createWorkflowForm = document.getElementById("create-workflow-form");
const loadingIndicator = document.getElementById("workflow-loading-indicator");
const refreshBtn = document.getElementById("refresh-btn");

// Modals
const editDialog = document.getElementById("edit-dialog");
const editForm = document.getElementById("edit-form");
const closeEditBtn = document.getElementById("close-edit-dialog");
const cancelEditBtn = document.getElementById("cancel-edit-btn");

const rejectDialog = document.getElementById("reject-dialog");
const rejectForm = document.getElementById("reject-form");
const closeRejectBtn = document.getElementById("close-reject-dialog");
const cancelRejectBtn = document.getElementById("cancel-reject-btn");

// Tab Switching
document.querySelectorAll(".tab-btn").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    
    button.classList.add("active");
    const targetTabId = button.getAttribute("data-tab");
    document.getElementById(targetTabId).classList.add("active");

    if (targetTabId === "tab-audit" && selectedWorkflowId) {
      loadAuditEvents(selectedWorkflowId);
    }
  });
});

// --- API Helpers ---

async function fetchApprovals() {
  try {
    const res = await fetch(`${API_BASE}/v1/approvals?status=PENDING`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    activeApprovals = await res.json();
    renderApprovals();
  } catch (err) {
    console.error("Failed to load approvals:", err);
  }
}

async function fetchWorkflows() {
  try {
    const res = await fetch(`${API_BASE}/v1/workflows`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    allWorkflows = await res.json();
    renderWorkflows();
    
    // Auto-select latest workflow for audit tab if none selected
    if (!selectedWorkflowId && allWorkflows.length > 0) {
      selectedWorkflowId = allWorkflows[0].id;
      loadAuditEvents(selectedWorkflowId);
    }
  } catch (err) {
    console.error("Failed to load workflows:", err);
  }
}

async function fetchOutbox() {
  try {
    const res = await fetch(`${API_BASE}/v1/outbox`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    outboxMessages = await res.json();
    renderOutbox();
  } catch (err) {
    console.error("Failed to load outbox:", err);
  }
}

async function loadAuditEvents(workflowId) {
  selectedWorkflowId = workflowId;
  try {
    const res = await fetch(`${API_BASE}/v1/workflows/${workflowId}/events`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const events = await res.json();
    renderAuditTimeline(events, workflowId);
  } catch (err) {
    console.error(`Failed to load audit events for ${workflowId}:`, err);
  }
}

// --- Render Functions ---

function renderApprovals() {
  approvalsCount.textContent = activeApprovals.length;
  
  if (activeApprovals.length === 0) {
    approvalsList.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">✅</div>
        <p>No pending approvals. Launch a workflow to see the agent pause at an approval gate.</p>
      </div>
    `;
    return;
  }

  approvalsList.innerHTML = activeApprovals.map(approval => {
    const action = approval.proposed_action || {};
    const params = action.parameters || {};
    const createdDate = new Date(approval.requested_at).toLocaleString();

    return `
      <div class="approval-card" data-id="${approval.id}">
        <div class="card-top">
          <div class="card-title-group">
            <h3>Approval Required for Action: <code style="color: var(--accent-amber);">${action.tool || "external_action"}</code></h3>
            <div class="card-meta">Workflow ID: <code>${approval.workflow_id}</code> | Requested: ${createdDate}</div>
          </div>
          <span class="badge-risk">${approval.risk_level || "REQUIRES_APPROVAL"}</span>
        </div>

        <div class="detail-box">
          <h4>Proposed Action Parameters</h4>
          <pre>${JSON.stringify(params, null, 2)}</pre>
        </div>

        <div class="detail-box">
          <h4>Reasoning (Why the agent wants to do this)</h4>
          <p>${escapeHtml(approval.reason)}</p>
        </div>

        <div class="detail-box">
          <h4>Evidence / Findings Used</h4>
          <pre>${JSON.stringify(approval.evidence || {}, null, 2)}</pre>
        </div>

        <div class="detail-box" style="border-left: 3px solid var(--accent-red);">
          <h4>Consequences if Approved</h4>
          <p style="color: #fca5a5;">${escapeHtml(approval.consequences)}</p>
        </div>

        <div class="card-actions">
          <button class="btn btn-success" onclick="handleApprove('${approval.id}')">
            ✅ Approve & Execute
          </button>
          <button class="btn btn-warning" onclick="openEditModal('${approval.id}')">
            ✏️ Edit & Approve
          </button>
          <button class="btn btn-danger" onclick="openRejectModal('${approval.id}')">
            🚫 Reject Action
          </button>
          <button class="btn btn-secondary" onclick="viewWorkflowAudit('${approval.workflow_id}')">
            📜 View Audit Log
          </button>
        </div>
      </div>
    `;
  }).join("");
}

function renderWorkflows() {
  if (allWorkflows.length === 0) {
    workflowsTableBody.innerHTML = `<tr><td colspan="5" class="empty-state">No workflows created yet.</td></tr>`;
    return;
  }

  workflowsTableBody.innerHTML = allWorkflows.map(wf => {
    const created = new Date(wf.created_at).toLocaleString();
    return `
      <tr>
        <td><code>${wf.id.substring(0, 8)}...</code></td>
        <td><strong>${escapeHtml(wf.task)}</strong></td>
        <td><span class="badge-state badge-${wf.current_state}">${wf.current_state}</span></td>
        <td>${created}</td>
        <td>
          <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.75rem;" onclick="viewWorkflowAudit('${wf.id}')">
            Audit Trail
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

function renderAuditTimeline(events, workflowId) {
  if (!events || events.length === 0) {
    auditTimeline.innerHTML = `<div class="empty-state"><p>No audit events recorded for workflow ${workflowId}.</p></div>`;
    return;
  }

  auditTimeline.innerHTML = `
    <div style="margin-bottom: 12px; font-weight: 600; color: var(--text-secondary);">
      Audit Log for Workflow: <code>${workflowId}</code> (${events.length} events recorded)
    </div>
  ` + events.map(evt => {
    const time = new Date(evt.timestamp).toLocaleTimeString();
    const metaStr = evt.metadata ? `<pre style="margin-top: 6px; font-size: 0.75rem; background:#090d16; padding:8px; border-radius:4px; overflow-x:auto;">${JSON.stringify(evt.metadata, null, 2)}</pre>` : "";
    const stateTransition = (evt.from_state || evt.to_state) ? ` [${evt.from_state || "*"} ➔ ${evt.to_state || "*"}]` : "";

    return `
      <div class="timeline-item">
        <div class="timeline-time">${time}</div>
        <div class="timeline-content">
          <div class="timeline-title">
            <span style="color: var(--accent-blue);">${escapeHtml(evt.event_type)}</span>
            <span style="color: var(--accent-amber);">${stateTransition}</span>
          </div>
          <div class="timeline-meta">Actor: <strong>${escapeHtml(evt.actor)}</strong></div>
          ${metaStr}
        </div>
      </div>
    `;
  }).join("");
}

function renderOutbox() {
  if (outboxMessages.length === 0) {
    outboxTableBody.innerHTML = `<tr><td colspan="5" class="empty-state">No messages sent to sandbox outbox yet.</td></tr>`;
    return;
  }

  outboxTableBody.innerHTML = outboxMessages.map(msg => {
    const time = new Date(msg.sent_at).toLocaleString();
    return `
      <tr>
        <td>${time}</td>
        <td><strong>${escapeHtml(msg.recipient)}</strong></td>
        <td>${escapeHtml(msg.subject)}</td>
        <td><code>${escapeHtml(msg.idempotency_key)}</code></td>
        <td><span class="badge-state badge-APPROVED">${msg.status}</span></td>
      </tr>
    `;
  }).join("");
}

// --- Action Handlers ---

window.handleApprove = async function(approvalId) {
  try {
    const res = await fetch(`${API_BASE}/v1/approvals/${approvalId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor: "human:reviewer", reason: "Approved via Approval UI dashboard" })
    });
    if (!res.ok) {
      const err = await res.json();
      alert(`Approval failed: ${err.detail || "Unknown error"}`);
      return;
    }
    await refreshAll();
  } catch (err) {
    console.error("Approval error:", err);
    alert("Failed to submit approval.");
  }
};

window.openEditModal = function(approvalId) {
  const approval = activeApprovals.find(a => a.id === approvalId);
  if (!approval) return;

  const action = approval.proposed_action || {};
  const params = action.parameters || {};

  document.getElementById("edit-approval-id").value = approvalId;
  document.getElementById("edit-recipient").value = params.recipient || "";
  document.getElementById("edit-subject").value = params.subject || "";
  document.getElementById("edit-body").value = params.body || "";
  document.getElementById("edit-reason").value = "";

  editDialog.showModal();
};

window.openRejectModal = function(approvalId) {
  document.getElementById("reject-approval-id").value = approvalId;
  document.getElementById("reject-reason").value = "";
  rejectDialog.showModal();
};

window.viewWorkflowAudit = function(workflowId) {
  // Switch to audit tab
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
  
  const auditBtn = document.querySelector('[data-tab="tab-audit"]');
  if (auditBtn) auditBtn.classList.add("active");
  document.getElementById("tab-audit").classList.add("active");

  loadAuditEvents(workflowId);
};

// --- Form Submissions ---

createWorkflowForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const taskInput = document.getElementById("workflow-task");
  const task = taskInput.value.trim();
  if (!task) return;

  loadingIndicator.style.display = "inline";
  const submitBtn = document.getElementById("start-workflow-btn");
  submitBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/v1/workflows`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task })
    });
    if (!res.ok) {
      const err = await res.json();
      alert(`Workflow initiation failed: ${err.detail || "Unknown error"}`);
      return;
    }
    const createdWorkflow = await res.json();
    selectedWorkflowId = createdWorkflow.id;
    await refreshAll();
  } catch (err) {
    console.error("Create workflow error:", err);
    alert("Failed to create workflow.");
  } finally {
    loadingIndicator.style.display = "none";
    submitBtn.disabled = false;
  }
});

editForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const approvalId = document.getElementById("edit-approval-id").value;
  const recipient = document.getElementById("edit-recipient").value.trim();
  const subject = document.getElementById("edit-subject").value.trim();
  const body = document.getElementById("edit-body").value.trim();
  const reason = document.getElementById("edit-reason").value.trim();

  try {
    const res = await fetch(`${API_BASE}/v1/approvals/${approvalId}/edit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        actor: "human:reviewer",
        reason: reason || "Action parameters customized by human reviewer",
        edited_action: {
          tool: "send_email",
          parameters: { recipient, subject, body }
        },
        approve_immediately: true
      })
    });
    if (!res.ok) {
      const err = await res.json();
      alert(`Edit submission failed: ${err.detail || "Unknown error"}`);
      return;
    }
    editDialog.close();
    await refreshAll();
  } catch (err) {
    console.error("Edit error:", err);
    alert("Failed to submit edited action.");
  }
});

rejectForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const approvalId = document.getElementById("reject-approval-id").value;
  const reason = document.getElementById("reject-reason").value.trim();

  try {
    const res = await fetch(`${API_BASE}/v1/approvals/${approvalId}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        actor: "human:reviewer",
        reason
      })
    });
    if (!res.ok) {
      const err = await res.json();
      alert(`Rejection failed: ${err.detail || "Unknown error"}`);
      return;
    }
    rejectDialog.close();
    await refreshAll();
  } catch (err) {
    console.error("Reject error:", err);
    alert("Failed to submit rejection.");
  }
});

// Modal close button event listeners
closeEditBtn.addEventListener("click", () => editDialog.close());
cancelEditBtn.addEventListener("click", () => editDialog.close());
closeRejectBtn.addEventListener("click", () => rejectDialog.close());
cancelRejectBtn.addEventListener("click", () => rejectDialog.close());

// Refresh all data
async function refreshAll() {
  await Promise.all([fetchApprovals(), fetchWorkflows(), fetchOutbox()]);
  if (selectedWorkflowId) {
    await loadAuditEvents(selectedWorkflowId);
  }
}

refreshBtn.addEventListener("click", refreshAll);

// Helper to escape HTML and avoid XSS
function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Initial load & periodic polling (every 4 seconds)
refreshAll();
setInterval(refreshAll, 4000);
