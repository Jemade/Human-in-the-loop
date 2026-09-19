class ApprovalFlowException(Exception):
    """Base exception for ApprovalFlow system."""
    pass


class InvalidStateTransitionError(ApprovalFlowException):
    """Raised when an invalid state transition is attempted."""
    def __init__(self, from_state: str, to_state: str, allowed: list[str]):
        self.from_state = from_state
        self.to_state = to_state
        self.allowed = allowed
        super().__init__(
            f"Invalid transition from '{from_state}' to '{to_state}'. "
            f"Allowed target states: {allowed}"
        )


class WorkflowNotFoundError(ApprovalFlowException):
    """Raised when a workflow cannot be found."""
    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        super().__init__(f"Workflow with ID '{workflow_id}' not found.")


class ApprovalNotFoundError(ApprovalFlowException):
    """Raised when an approval request cannot be found."""
    def __init__(self, approval_id: str):
        self.approval_id = approval_id
        super().__init__(f"Approval request with ID '{approval_id}' not found.")


class DuplicateExecutionError(ApprovalFlowException):
    """Raised when an action is triggered with an already executed idempotency key."""
    def __init__(self, idempotency_key: str):
        self.idempotency_key = idempotency_key
        super().__init__(
            f"Action with idempotency key '{idempotency_key}' has already been executed."
        )


class UnauthorizedError(ApprovalFlowException):
    """Raised when an unauthorized actor attempts a protected operation."""
    def __init__(self, message: str = "Unauthorized operation."):
        super().__init__(message)


class ToolExecutionError(ApprovalFlowException):
    """Raised when a tool fails during execution."""
    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' failed: {message}")
