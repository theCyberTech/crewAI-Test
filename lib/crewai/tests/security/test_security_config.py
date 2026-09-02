"""Test for the SecurityConfig class."""

from datetime import datetime
import json

from crewai.security import Fingerprint, SecurityConfig
import pytest


def test_security_config_creation_with_defaults():
    """Test creating a SecurityConfig with default values."""
    config = SecurityConfig()

    assert config.fingerprint is not None
    assert isinstance(config.fingerprint, Fingerprint)
    assert config.fingerprint.uuid_str is not None


def test_security_config_fingerprint_generation():
    """Test that SecurityConfig automatically generates fingerprints."""
    config = SecurityConfig()

    assert config.fingerprint is not None
    assert isinstance(config.fingerprint, Fingerprint)
    assert isinstance(config.fingerprint.uuid_str, str)
    assert len(config.fingerprint.uuid_str) > 0


def test_security_config_init_params():
    """Test that SecurityConfig can be initialized and modified."""
    config = SecurityConfig()

    fingerprint = Fingerprint(metadata={"version": "1.0"})

    config.fingerprint = fingerprint

    assert config.fingerprint is fingerprint
    assert config.fingerprint.metadata == {"version": "1.0"}


def test_security_config_to_dict():
    """Test converting SecurityConfig to dictionary."""
    config = SecurityConfig()
    config.fingerprint.metadata = {"version": "1.0"}

    config_dict = config.to_dict()

    assert "fingerprint" in config_dict
    assert isinstance(config_dict["fingerprint"], dict)
    assert config_dict["fingerprint"]["metadata"] == {"version": "1.0"}
    assert config_dict["allowed_tools"] is None
    assert config_dict["blocked_tools"] is None
    assert config_dict["require_approval_tools"] is None


def test_security_config_tool_lists_default_to_none():
    """Unconfigured tool lists are None so existing agents stay unrestricted."""
    config = SecurityConfig()

    assert config.allowed_tools is None
    assert config.blocked_tools is None
    assert config.require_approval_tools is None


def test_security_config_sanitizes_tool_list_names():
    """Tool lists are sanitized so they match hook tool_name values."""
    config = SecurityConfig(
        allowed_tools=["File Writer Tool", "file_writer_tool"],
        blocked_tools=["NL2SQLTool"],
        require_approval_tools=["filesystem_write_file"],
    )

    assert config.allowed_tools == ["file_writer_tool"]
    assert config.blocked_tools == ["nl2sql_tool"]
    assert config.require_approval_tools == ["filesystem_write_file"]


def test_security_config_rejects_string_tool_list():
    """A bare string is not a tool list."""
    with pytest.raises(ValueError, match="sequence of strings"):
        SecurityConfig(allowed_tools="read_file")


def test_security_config_tool_lists_round_trip():
    """to_dict / from_dict preserve sanitized tool lists."""
    config = SecurityConfig(
        allowed_tools=["read_file"],
        blocked_tools=["file_writer_tool"],
        require_approval_tools=["nl2sql_tool"],
    )

    restored = SecurityConfig.from_dict(config.to_dict())

    assert restored.allowed_tools == ["read_file"]
    assert restored.blocked_tools == ["file_writer_tool"]
    assert restored.require_approval_tools == ["nl2sql_tool"]
    assert restored.fingerprint.uuid_str == config.fingerprint.uuid_str


def test_security_config_from_dict():
    """Test creating SecurityConfig from dictionary."""
    fingerprint_dict = {
        "uuid_str": "b723c6ff-95de-5e87-860b-467b72282bd8",
        "created_at": datetime.now().isoformat(),
        "metadata": {"version": "1.0"},
    }

    config_dict = {"fingerprint": fingerprint_dict}

    config = SecurityConfig()

    fingerprint = Fingerprint.from_dict(fingerprint_dict)
    config.fingerprint = fingerprint

    assert config.fingerprint is not None
    assert isinstance(config.fingerprint, Fingerprint)
    assert config.fingerprint.uuid_str == fingerprint_dict["uuid_str"]
    assert config.fingerprint.metadata == fingerprint_dict["metadata"]


def test_security_config_json_serialization():
    """Test that SecurityConfig can be JSON serialized and deserialized."""
    config = SecurityConfig()
    config.fingerprint.metadata = {"version": "1.0"}

    config_dict = config.to_dict()

    assert isinstance(config_dict["fingerprint"], dict)

    json_str = json.dumps(config_dict)

    parsed_dict = json.loads(json_str)

    assert parsed_dict["fingerprint"]["metadata"] == {"version": "1.0"}

    new_config = SecurityConfig()

    fingerprint_data = parsed_dict["fingerprint"]
    new_fingerprint = Fingerprint.from_dict(fingerprint_data)
    new_config.fingerprint = new_fingerprint

    assert new_config.fingerprint.metadata == {"version": "1.0"}
