"""Tests for SecurityConfig tool-access evaluation."""

from unittest.mock import Mock

import pytest

from crewai.security import SecurityConfig
from crewai.security.tool_policy import (
    PolicyDecision,
    collect_security_configs,
    evaluate_tool_policy,
    is_approval_response,
)


def test_no_policy_allows_any_tool():
    decision = evaluate_tool_policy("file_writer_tool", [SecurityConfig()])

    assert decision == PolicyDecision(denied=False, require_approval=False)


def test_none_configs_are_ignored():
    decision = evaluate_tool_policy("file_writer_tool", [None, SecurityConfig(), None])

    assert decision.denied is False


def test_allowlist_admits_listed_and_sanitized_aliases():
    config = SecurityConfig(allowed_tools=["File Writer Tool"])

    allowed = evaluate_tool_policy("file_writer_tool", [config])
    also_allowed = evaluate_tool_policy("File Writer Tool", [config])
    denied = evaluate_tool_policy("nl2sql_tool", [config])

    assert allowed.denied is False
    assert also_allowed.denied is False
    assert denied.denied is True
    assert denied.reason is not None
    assert "allowed_tools" in denied.reason


def test_empty_allowlist_denies_everything():
    config = SecurityConfig(allowed_tools=[])

    decision = evaluate_tool_policy("read_file", [config])

    assert decision.denied is True


def test_blocked_tools_win_over_allowed_tools():
    config = SecurityConfig(
        allowed_tools=["file_writer_tool"],
        blocked_tools=["file_writer_tool"],
    )

    decision = evaluate_tool_policy("file_writer_tool", [config])

    assert decision.denied is True
    assert decision.reason is not None
    assert "blocked" in decision.reason


def test_blocked_tools_deny_without_allowlist():
    config = SecurityConfig(blocked_tools=["nl2sql_tool"])

    assert evaluate_tool_policy("nl2sql_tool", [config]).denied is True
    assert evaluate_tool_policy("read_file", [config]).denied is False


def test_require_approval_after_allow_pass():
    config = SecurityConfig(
        allowed_tools=["nl2sql_tool", "read_file"],
        require_approval_tools=["nl2sql_tool"],
    )

    sql = evaluate_tool_policy("nl2sql_tool", [config])
    read = evaluate_tool_policy("read_file", [config])

    assert sql.denied is False
    assert sql.require_approval is True
    assert read.denied is False
    assert read.require_approval is False


def test_blocked_tool_does_not_request_approval():
    config = SecurityConfig(
        blocked_tools=["nl2sql_tool"],
        require_approval_tools=["nl2sql_tool"],
    )

    decision = evaluate_tool_policy("nl2sql_tool", [config])

    assert decision.denied is True
    assert decision.require_approval is False


def test_agent_and_crew_merge_is_most_restrictive():
    agent_config = SecurityConfig(allowed_tools=["read_file", "file_writer_tool"])
    crew_config = SecurityConfig(blocked_tools=["file_writer_tool"])

    writer = evaluate_tool_policy("file_writer_tool", [agent_config, crew_config])
    reader = evaluate_tool_policy("read_file", [agent_config, crew_config])
    sql = evaluate_tool_policy("nl2sql_tool", [agent_config, crew_config])

    assert writer.denied is True
    assert reader.denied is False
    assert sql.denied is True


def test_task_allowlist_restricts_agent_without_lists():
    agent_config = SecurityConfig()
    task_config = SecurityConfig(allowed_tools=["read_file"])

    assert evaluate_tool_policy("read_file", [agent_config, task_config]).denied is False
    assert (
        evaluate_tool_policy("file_writer_tool", [agent_config, task_config]).denied
        is True
    )


def test_missing_tool_name_denies_when_policy_is_active():
    config = SecurityConfig(allowed_tools=["read_file"])

    decision = evaluate_tool_policy("", [config])

    assert decision.denied is True
    assert decision.reason is not None
    assert "missing" in decision.reason


def test_missing_tool_name_allows_when_no_policy():
    decision = evaluate_tool_policy("", [SecurityConfig()])

    assert decision.denied is False


def test_collect_security_configs_skips_mocks_and_missing():
    agent = Mock()
    agent.security_config = SecurityConfig(allowed_tools=["read_file"])
    task = Mock()
    crew = Mock()
    crew.security_config = "not-a-config"

    configs = collect_security_configs(agent, task, crew, None)

    assert len(configs) == 1
    assert configs[0].allowed_tools == ["read_file"]


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ("yes", True),
        ("YES", True),
        (" y ", True),
        ("approve", True),
        ("Approve", True),
        ("no", False),
        ("", False),
        ("later", False),
    ],
)
def test_is_approval_response(response: str, expected: bool):
    assert is_approval_response(response) is expected
