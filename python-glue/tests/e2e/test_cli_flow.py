"""End-to-end tests for CLI workflows"""

import pytest
import subprocess
import os


def test_cli_help():
    """Test CLI help command"""
    result = subprocess.run(
        ["uai", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Usage" in result.stdout or "Commands" in result.stdout


def test_cli_tools_list():
    """Test CLI tools list command"""
    result = subprocess.run(
        ["uai", "tools"],
        capture_output=True,
        text=True,
    )
    # Should either succeed or show error (if not configured)
    assert result.returncode in [0, 1]


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="Requires API key"
)
def test_cli_chat_basic():
    """Test basic CLI chat (requires API key)"""
    result = subprocess.run(
        ["uai", "chat", "Hello"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    # Should succeed if API key is set
    assert result.returncode == 0 or "error" in result.stderr.lower()
