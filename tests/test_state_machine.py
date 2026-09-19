import pytest
from app.core.state_machine import StateMachine
from app.models.workflow import WorkflowState
from app.core.exceptions import InvalidStateTransitionError


def test_valid_transitions():
    """Verify that expected transitions succeed without raising errors."""
    valid_pairs = [
        (WorkflowState.CREATED, WorkflowState.PLANNING),
        (WorkflowState.CREATED, WorkflowState.FAILED),
        (WorkflowState.PLANNING, WorkflowState.RESEARCHING),
        (WorkflowState.PLANNING, WorkflowState.FAILED),
        (WorkflowState.RESEARCHING, WorkflowState.DRAFTING),
        (WorkflowState.RESEARCHING, WorkflowState.FAILED),
        (WorkflowState.DRAFTING, WorkflowState.WAITING_FOR_APPROVAL),
        (WorkflowState.DRAFTING, WorkflowState.EXECUTING),
        (WorkflowState.DRAFTING, WorkflowState.FAILED),
        (WorkflowState.WAITING_FOR_APPROVAL, WorkflowState.APPROVED),
        (WorkflowState.WAITING_FOR_APPROVAL, WorkflowState.REJECTED),
        (WorkflowState.WAITING_FOR_APPROVAL, WorkflowState.EDIT_REQUIRED),
        (WorkflowState.WAITING_FOR_APPROVAL, WorkflowState.FAILED),
        (WorkflowState.EDIT_REQUIRED, WorkflowState.APPROVED),
        (WorkflowState.EDIT_REQUIRED, WorkflowState.REJECTED),
        (WorkflowState.APPROVED, WorkflowState.EXECUTING),
        (WorkflowState.APPROVED, WorkflowState.FAILED),
        (WorkflowState.REJECTED, WorkflowState.COMPLETED),
        (WorkflowState.EXECUTING, WorkflowState.COMPLETED),
        (WorkflowState.EXECUTING, WorkflowState.FAILED),
        (WorkflowState.FAILED, WorkflowState.PLANNING),
    ]

    for from_st, to_st in valid_pairs:
        assert StateMachine.can_transition(from_st, to_st) is True
        StateMachine.validate_transition(from_st, to_st)


def test_invalid_transitions():
    """Verify that illegal transitions raise InvalidStateTransitionError."""
    invalid_pairs = [
        (WorkflowState.CREATED, WorkflowState.EXECUTING),
        (WorkflowState.CREATED, WorkflowState.COMPLETED),
        (WorkflowState.PLANNING, WorkflowState.COMPLETED),
        (WorkflowState.RESEARCHING, WorkflowState.EXECUTING),
        (WorkflowState.WAITING_FOR_APPROVAL, WorkflowState.COMPLETED),
        (WorkflowState.COMPLETED, WorkflowState.PLANNING),
        (WorkflowState.COMPLETED, WorkflowState.EXECUTING),
        (WorkflowState.COMPLETED, WorkflowState.CREATED),
        (WorkflowState.APPROVED, WorkflowState.PLANNING),
    ]

    for from_st, to_st in invalid_pairs:
        assert StateMachine.can_transition(from_st, to_st) is False
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            StateMachine.validate_transition(from_st, to_st)
        assert exc_info.value.from_state == from_st.value
        assert exc_info.value.to_state == to_st.value


def test_terminal_state():
    """Verify COMPLETED is recognized as terminal with no allowed transitions."""
    assert StateMachine.is_terminal(WorkflowState.COMPLETED) is True
    assert StateMachine.is_terminal(WorkflowState.PLANNING) is False
    assert StateMachine.get_allowed_transitions(WorkflowState.COMPLETED) == []


def test_allowed_transitions_query():
    """Verify querying allowed transitions for states."""
    allowed = StateMachine.get_allowed_transitions(WorkflowState.WAITING_FOR_APPROVAL)
    assert set(allowed) == {"APPROVED", "REJECTED", "EDIT_REQUIRED", "FAILED"}
