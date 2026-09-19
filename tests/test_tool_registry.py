import pytest
from pydantic import BaseModel, Field
from app.tools.base import ToolRegistry, ToolDefinition, RiskLevel, registry
from app.core.exceptions import ToolExecutionError


class DummyInput(BaseModel):
    query: str = Field(..., min_length=2)
    count: int = 10


def test_tool_registration_and_retrieval():
    reg = ToolRegistry()
    dummy_tool = ToolDefinition(
        name="dummy_safe_search",
        description="A safe test search tool",
        risk_level=RiskLevel.SAFE,
        input_schema=DummyInput,
        handler=lambda query, count: f"Found {count} results for {query}",
    )
    reg.register(dummy_tool)

    assert reg.get("dummy_safe_search") == dummy_tool
    assert reg.is_safe("dummy_safe_search") is True
    assert reg.requires_approval("dummy_safe_search") is False

    result = reg.execute("dummy_safe_search", query="hello", count=5)
    assert result == "Found 5 results for hello"


def test_high_risk_tool_classification():
    reg = ToolRegistry()
    dummy_dangerous = ToolDefinition(
        name="dummy_delete_account",
        description="A dangerous action",
        risk_level=RiskLevel.REQUIRES_APPROVAL,
        input_schema=DummyInput,
        handler=lambda query, count: "deleted",
    )
    reg.register(dummy_dangerous)

    assert reg.is_safe("dummy_delete_account") is False
    assert reg.requires_approval("dummy_delete_account") is True


def test_tool_input_validation_failure():
    reg = ToolRegistry()
    tool = ToolDefinition(
        name="dummy_strict",
        description="Strict input tool",
        risk_level=RiskLevel.SAFE,
        input_schema=DummyInput,
        handler=lambda query, count: "ok",
    )
    reg.register(tool)

    # query min_length is 2, single char should fail
    with pytest.raises(ToolExecutionError):
        reg.execute("dummy_strict", query="a")


def test_global_registry_builtins():
    """Verify built-in tools are registered properly in the global registry."""
    assert registry.is_safe("search_company_web") is True
    assert registry.requires_approval("search_company_web") is False

    assert registry.is_safe("extract_company_profile") is True
    assert registry.requires_approval("extract_company_profile") is False

    assert registry.is_safe("send_email") is False
    assert registry.requires_approval("send_email") is True
