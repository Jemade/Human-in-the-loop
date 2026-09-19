from typing import Callable, Dict, Any, Type, Optional, List
import enum
from pydantic import BaseModel
from app.core.exceptions import ToolExecutionError


class RiskLevel(str, enum.Enum):
    SAFE = "SAFE"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"


class ToolDefinition:
    def __init__(
        self,
        name: str,
        description: str,
        risk_level: RiskLevel,
        input_schema: Type[BaseModel],
        handler: Callable[..., Any],
        requires_approval: Optional[bool] = None,
    ):
        self.name = name
        self.description = description
        self.risk_level = risk_level
        # If requires_approval not explicitly given, derive from risk_level
        self.requires_approval = (
            requires_approval if requires_approval is not None else (risk_level == RiskLevel.REQUIRES_APPROVAL)
        )
        self.input_schema = input_schema
        self.handler = handler

    def execute(self, **kwargs) -> Any:
        try:
            # Validate against input schema
            validated_args = self.input_schema(**kwargs)
            return self.handler(**validated_args.model_dump())
        except Exception as e:
            if isinstance(e, ToolExecutionError):
                raise
            raise ToolExecutionError(self.name, str(e)) from e

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "risk_level": self.risk_level.value,
            "requires_approval": self.requires_approval,
            "input_schema": self.input_schema.model_json_schema() if hasattr(self.input_schema, "model_json_schema") else str(self.input_schema),
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered.")
        return self._tools[name]

    def requires_approval(self, name: str) -> bool:
        tool = self.get(name)
        return tool.requires_approval

    def is_safe(self, name: str) -> bool:
        return not self.requires_approval(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [tool.to_dict() for tool in self._tools.values()]

    def execute(self, name: str, **kwargs) -> Any:
        tool = self.get(name)
        return tool.execute(**kwargs)


# Global default tool registry
registry = ToolRegistry()
