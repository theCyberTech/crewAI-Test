"""Security Configuration Module

This module provides configuration for CrewAI security features, including:
- Authentication settings
- Scoping rules
- Fingerprinting
- Tool access lists

The SecurityConfig class is the primary interface for managing security settings
in CrewAI applications.
"""

from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing_extensions import Self

from crewai.security.fingerprint import Fingerprint
from crewai.utilities.string_utils import sanitize_tool_name


def _sanitize_tool_list(names: Iterable[Any] | None) -> list[str] | None:
    """Normalize a tool-name list. ``None`` means no rule; ``[]`` is an empty rule."""
    if names is None:
        return None
    sanitized: list[str] = []
    seen: set[str] = set()
    for name in names:
        if not isinstance(name, str):
            raise ValueError(f"Tool names must be strings, got {type(name)}")
        normalized = sanitize_tool_name(name)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        sanitized.append(normalized)
    return sanitized


class SecurityConfig(BaseModel):
    """
    Configuration for CrewAI security features.

    This class manages security settings for CrewAI agents, including:
    - Authentication credentials *TODO*
    - Identity information (agent fingerprints)
    - Tool access lists (allowed, blocked, require-approval)
    - Impersonation/delegation tokens *TODO*

    Attributes:
        fingerprint: The unique fingerprint automatically generated for the
            component.
        allowed_tools: If set, only these tool names may run. An empty list
            denies every tool. ``None`` means no allowlist.
        blocked_tools: Tool names that must never run. Blocked names win over
            ``allowed_tools``. ``None`` means no blocklist.
        require_approval_tools: Tool names that pause for operator approval
            after allow/block checks pass. ``None`` means no approval gate.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True
        # Note: Cannot use frozen=True as existing tests modify the fingerprint property
    )

    fingerprint: Fingerprint = Field(
        default_factory=Fingerprint, description="Unique identifier for the component"
    )
    allowed_tools: list[str] | None = Field(
        default=None,
        description=(
            "If set, only these sanitized tool names may run. An empty list "
            "denies every tool."
        ),
    )
    blocked_tools: list[str] | None = Field(
        default=None,
        description="Sanitized tool names that must never run. Block wins over allow.",
    )
    require_approval_tools: list[str] | None = Field(
        default=None,
        description=(
            "Sanitized tool names that require operator approval after "
            "allow/block checks pass."
        ),
    )

    @field_validator("fingerprint", mode="before")
    @classmethod
    def validate_fingerprint(cls, v: Any) -> Fingerprint:
        """Ensure fingerprint is properly initialized."""
        if v is None:
            return Fingerprint()
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("Fingerprint seed cannot be empty")
            return Fingerprint.generate(seed=v)
        if isinstance(v, dict):
            return Fingerprint.from_dict(v)
        if isinstance(v, Fingerprint):
            return v

        raise ValueError(f"Invalid fingerprint type: {type(v)}")

    @field_validator(
        "allowed_tools", "blocked_tools", "require_approval_tools", mode="before"
    )
    @classmethod
    def validate_tool_lists(cls, v: Any) -> list[str] | None:
        """Sanitize tool names so they match hook ``tool_name`` values."""
        if v is None:
            return None
        if isinstance(v, str):
            raise ValueError("Tool lists must be a sequence of strings, not a string")
        if not isinstance(v, (list, tuple, set)):
            raise ValueError(f"Invalid tool list type: {type(v)}")
        return _sanitize_tool_list(v)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the security config to a dictionary.

        Returns:
            Dictionary representation of the security config
        """
        return {
            "fingerprint": self.fingerprint.to_dict(),
            "allowed_tools": self.allowed_tools,
            "blocked_tools": self.blocked_tools,
            "require_approval_tools": self.require_approval_tools,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create a SecurityConfig from a dictionary.

        Args:
            data: Dictionary representation of a security config

        Returns:
            A new SecurityConfig instance
        """
        fingerprint_data = data.get("fingerprint")
        fingerprint = (
            Fingerprint.from_dict(fingerprint_data)
            if fingerprint_data
            else Fingerprint()
        )

        return cls(
            fingerprint=fingerprint,
            allowed_tools=data.get("allowed_tools"),
            blocked_tools=data.get("blocked_tools"),
            require_approval_tools=data.get("require_approval_tools"),
        )
