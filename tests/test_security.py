import pytest
from app.config import get_settings


def test_unauthorized_approval_rejected_when_auth_required(client, monkeypatch):
    """Verify that approval endpoints return 401 when REQUIRE_AUTH is enabled."""
    settings = get_settings()
    monkeypatch.setattr(settings, "REQUIRE_AUTH", True)
    monkeypatch.setattr(settings, "API_KEY", "secret-test-key")

    # Create workflow
    res_create = client.post("/v1/workflows", json={"task": "Research Acme and outreach"})
    assert res_create.status_code == 201
    wf_id = res_create.json()["id"]

    # Get approval ID
    res_appr = client.get(f"/v1/approvals?status=PENDING")
    assert res_appr.status_code == 200
    approval_id = res_appr.json()[0]["id"]

    # Attempt to approve without auth header
    res_unauth = client.post(f"/v1/approvals/{approval_id}/approve", json={})
    assert res_unauth.status_code == 401
    assert "Invalid or missing API key" in res_unauth.json()["detail"]

    # Attempt with wrong API key
    res_bad_key = client.post(
        f"/v1/approvals/{approval_id}/approve",
        headers={"X-API-Key": "wrong-key"},
        json={},
    )
    assert res_bad_key.status_code == 401

    # Attempt with correct API key
    res_auth = client.post(
        f"/v1/approvals/{approval_id}/approve",
        headers={"X-API-Key": "secret-test-key", "X-Actor-Id": "human:security_director"},
        json={"reason": "Security director authorized"},
    )
    assert res_auth.status_code == 200
    assert res_auth.json()["current_state"] == "COMPLETED"


def test_actor_resolution(client, monkeypatch):
    """Verify actor is correctly extracted from X-Actor-Id header."""
    settings = get_settings()
    monkeypatch.setattr(settings, "REQUIRE_AUTH", False)

    res_create = client.post("/v1/workflows", json={"task": "Research Acme and outreach"})
    approval_id = client.get("/v1/approvals?status=PENDING").json()[0]["id"]

    # Approve with explicit X-Actor-Id
    res = client.post(
        f"/v1/approvals/{approval_id}/approve",
        headers={"X-Actor-Id": "human:compliance_auditor"},
        json={"reason": "Approved by auditor"},
    )
    assert res.status_code == 200

    # Verify actor in approval record
    res_detail = client.get(f"/v1/approvals/{approval_id}")
    assert res_detail.json()["actor"] == "human:compliance_auditor"
