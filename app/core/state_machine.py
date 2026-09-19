from typing import Dict, Set, List
from app.models.workflow import WorkflowState
from app.core.exceptions import InvalidStateTransitionError


class StateMachine:
    """
    Explicit, deterministic state machine governing all workflow transitions.
    
    Guarantees:
    - Zero undefined transitions
    - Strict validation with informative errors
    - Immutable transition graph
    """

    # Allowed transitions map: CurrentState -> Set of valid next states
    TRANSITIONS: Dict[WorkflowState, Set[WorkflowState]] = {
        WorkflowState.CREATED: {
            WorkflowState.PLANNING,
            WorkflowState.FAILED,
        },
        WorkflowState.PLANNING: {
            WorkflowState.RESEARCHING,
            WorkflowState.FAILED,
        },
        WorkflowState.RESEARCHING: {
            WorkflowState.DRAFTING,
            WorkflowState.FAILED,
        },
        WorkflowState.DRAFTING: {
            WorkflowState.WAITING_FOR_APPROVAL,
            WorkflowState.EXECUTING,  # Direct execution only allowed for completely safe actions
            WorkflowState.FAILED,
        },
        WorkflowState.WAITING_FOR_APPROVAL: {
            WorkflowState.APPROVED,
            WorkflowState.REJECTED,
            WorkflowState.EDIT_REQUIRED,
            WorkflowState.FAILED,
        },
        WorkflowState.EDIT_REQUIRED: {
            WorkflowState.APPROVED,
            WorkflowState.REJECTED,
            WorkflowState.WAITING_FOR_APPROVAL,
            WorkflowState.FAILED,
        },
        WorkflowState.APPROVED: {
            WorkflowState.EXECUTING,
            WorkflowState.FAILED,
        },
        WorkflowState.REJECTED: {
            WorkflowState.COMPLETED,  # Graceful termination
            WorkflowState.PLANNING,   # Re-planning loop if configured
            WorkflowState.FAILED,
        },
        WorkflowState.EXECUTING: {
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
        },
        WorkflowState.COMPLETED: set(),  # Terminal state
        WorkflowState.FAILED: {
            WorkflowState.PLANNING,   # Allow retry from failure
        },
    }

    @classmethod
    def can_transition(cls, from_state: WorkflowState | str, to_state: WorkflowState | str) -> bool:
        """Check if a transition is valid without raising an exception."""
        from_st = WorkflowState(from_state) if isinstance(from_state, str) else from_state
        to_st = WorkflowState(to_state) if isinstance(to_state, str) else to_state
        allowed = cls.TRANSITIONS.get(from_st, set())
        return to_st in allowed

    @classmethod
    def validate_transition(
        cls,
        from_state: WorkflowState | str,
        to_state: WorkflowState | str
    ) -> None:
        """
        Validate transition. Raises InvalidStateTransitionError if illegal.
        """
        from_st = WorkflowState(from_state) if isinstance(from_state, str) else from_state
        to_st = WorkflowState(to_state) if isinstance(to_state, str) else to_state

        allowed = cls.TRANSITIONS.get(from_st, set())
        if to_st not in allowed:
            allowed_names = [s.value for s in allowed]
            raise InvalidStateTransitionError(
                from_state=from_st.value,
                to_state=to_st.value,
                allowed=allowed_names
            )

    @classmethod
    def is_terminal(cls, state: WorkflowState | str) -> bool:
        """Return True if state is terminal (e.g. COMPLETED)."""
        st = WorkflowState(state) if isinstance(state, str) else state
        return st == WorkflowState.COMPLETED

    @classmethod
    def get_allowed_transitions(cls, state: WorkflowState | str) -> List[str]:
        """Return list of allowed target state names from the given state."""
        st = WorkflowState(state) if isinstance(state, str) else state
        return [s.value for s in cls.TRANSITIONS.get(st, set())]
