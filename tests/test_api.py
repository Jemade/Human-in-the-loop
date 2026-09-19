def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True


def test_workflows_api_crud_and_events(client):
    # 1. Create workflow
    res_create = client.post(
        "/v1/workflows",
        json={"task": "Research Stripe and prepare an outreach email.", "title": "Stripe Campaign"}
    )
    assert res_create.status_code == 201
    wf = res_create.json()
    wf_id = wf["id"]
    assert wf["current_state"] == "WAITING_FOR_APPROVAL"
    assert wf["title"] == "Stripe Campaign"

    # 2. List workflows
    res_list = client.get("/v1/workflows")
    assert res_list.status_code == 200
    workflows = res_list.json()
    assert len(workflows) >= 1
    assert any(w["id"] == wf_id for w in workflows)

    # 3. Get specific workflow
    res_get = client.get(f"/v1/workflows/{wf_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == wf_id

    # 4. Get events
    res_events = client.get(f"/v1/workflows/{wf_id}/events")
    assert res_events.status_code == 200
    events = res_events.json()
    assert len(events) >= 5
    assert events[0]["event_type"] == "workflow_created"


def test_approvals_api_endpoints(client):
    # Create workflow to get an approval
    res_create = client.post(
        "/v1/workflows",
        json={"task": "Research Acme Corp and prepare an outreach email."}
    )
    wf_id = res_create.json()["id"]

    # 1. List approvals
    res_approvals = client.get("/v1/approvals?status=PENDING")
    assert res_approvals.status_code == 200
    approvals = res_approvals.json()
    assert len(approvals) >= 1
    approval = approvals[0]
    appr_id = approval["id"]
    assert approval["workflow_id"] == wf_id

    # 2. Get specific approval
    res_single = client.get(f"/v1/approvals/{appr_id}")
    assert res_single.status_code == 200
    assert res_single.json()["id"] == appr_id

    # 3. Approve
    res_approve = client.post(
        f"/v1/approvals/{appr_id}/approve",
        json={"actor": "human:manager", "reason": "Looks good"}
    )
    assert res_approve.status_code == 200
    assert res_approve.json()["current_state"] == "COMPLETED"

    # 4. Verify outbox message
    res_outbox = client.get("/v1/outbox")
    assert res_outbox.status_code == 200
    outbox_msgs = res_outbox.json()
    assert len(outbox_msgs) >= 1
    assert outbox_msgs[0]["workflow_id"] == wf_id


def test_approvals_api_rejection(client):
    res_create = client.post(
        "/v1/workflows",
        json={"task": "Research Acme and prepare outreach"}
    )
    wf_id = res_create.json()["id"]
    approval_id = client.get("/v1/approvals?status=PENDING").json()[0]["id"]

    res_reject = client.post(
        f"/v1/approvals/{approval_id}/reject",
        json={"actor": "human:reviewer", "reason": "Not appropriate at this time"}
    )
    assert res_reject.status_code == 200
    assert res_reject.json()["current_state"] == "COMPLETED"

    # Check approval status
    res_appr = client.get(f"/v1/approvals/{approval_id}")
    assert res_appr.json()["status"] == "REJECTED"


def test_approvals_api_edit(client):
    res_create = client.post(
        "/v1/workflows",
        json={"task": "Research Acme and prepare outreach"}
    )
    wf_id = res_create.json()["id"]
    approval_id = client.get("/v1/approvals?status=PENDING").json()[0]["id"]

    edited_action = {
        "tool": "send_email",
        "parameters": {
            "recipient": "new.recipient@acme.com",
            "subject": "Edited Subject Line",
            "body": "Edited Body Content",
        }
    }

    res_edit = client.post(
        f"/v1/approvals/{approval_id}/edit",
        json={
            "actor": "human:editor",
            "edited_action": edited_action,
            "reason": "Updated copy",
            "approve_immediately": True
        }
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["current_state"] == "COMPLETED"

    # Check outbox
    res_outbox = client.get("/v1/outbox")
    assert any(m["recipient"] == "new.recipient@acme.com" for m in res_outbox.json())
