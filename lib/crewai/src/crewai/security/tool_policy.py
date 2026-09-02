"""Fail-closed tool-access evaluation for :class:`SecurityConfig`.

The evaluator is a pure function so security tests can exercise it without
importing the hook dispatcher. The first-party ``PRE_TOOL_CALL`` hook in
``crewai.hooks.tool_hooks`` applies the decision at invocation time.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from crewai.security.security_config import SecurityConfig
from crewai.utilities.string_utils import sanitize_tool_name


POLICY_SOURCE = "security-config"

_APPROVAL_ANSWERS = frozenset({"yes", "y", "approve"})


@dataclass(frozen=True)
class PolicyDecision:
    """Outcome of evaluating tool-access lists against a tool name."""

    denied: bool
    require_approval: bool = False
    reason: str | None = None


def _config_has_policy(config: SecurityConfig) -> bool:
    return (
        config.allowed_tools is not None
        or config.blocked_tools is not None
        or config.require_approval_tools is not None
    )


def _as_security_config(value: object) -> SecurityConfig | None:
    if isinstance(value, SecurityConfig):
        return value
    return None


def collect_security_configs(*owners: object | None) -> list[SecurityConfig]:
    """Return ``SecurityConfig`` instances attached to agent/task/crew owners."""
    configs: list[SecurityConfig] = []
    for owner in owners:
        if owner is None:
            continue
        config = _as_security_config(getattr(owner, "security_config", None))
        if config is not None:
            configs.append(config)
    return configs


def is_approval_response(response: str) -> bool:
    """Whether an operator reply counts as approval."""
    return response.strip().lower() in _APPROVAL_ANSWERS


def evaluate_tool_policy(
    tool_name: str,
    configs: Iterable[SecurityConfig | None],
) -> PolicyDecision:
    """Evaluate allow/block/approval lists across one or more configs.

    Most-restrictive wins: a tool is denied if any config denies it, and
    requires approval if any remaining config lists it for approval. Blocked
    names win over allowed names. ``None`` on a list means no rule; an empty
    ``allowed_tools`` list denies every tool.

    Args:
        tool_name: Tool name as seen at the hook seam (already sanitized or not).
        configs: Agent, task, and/or crew security configs. ``None`` entries
            are ignored.

    Returns:
        A :class:`PolicyDecision` describing deny / allow / require-approval.
    """
    active = [config for config in configs if isinstance(config, SecurityConfig)]
    has_any_policy = any(_config_has_policy(config) for config in active)
    sanitized = sanitize_tool_name(tool_name) if tool_name else ""

    if has_any_policy and not sanitized:
        return PolicyDecision(
            denied=True,
            reason="tool name is missing while a security_config tool policy is active",
        )

    if not has_any_policy:
        return PolicyDecision(denied=False)

    require_approval = False
    for config in active:
        blocked = (
            {sanitize_tool_name(name) for name in config.blocked_tools}
            if config.blocked_tools is not None
            else None
        )
        if blocked is not None and sanitized in blocked:
            return PolicyDecision(
                denied=True,
                reason=f"{sanitized} is blocked by security_config",
            )

        allowed = (
            {sanitize_tool_name(name) for name in config.allowed_tools}
            if config.allowed_tools is not None
            else None
        )
        if allowed is not None and sanitized not in allowed:
            return PolicyDecision(
                denied=True,
                reason=f"{sanitized} is not in allowed_tools",
            )

        approval = (
            {sanitize_tool_name(name) for name in config.require_approval_tools}
            if config.require_approval_tools is not None
            else None
        )
        if approval is not None and sanitized in approval:
            require_approval = True

    return PolicyDecision(denied=False, require_approval=require_approval)
