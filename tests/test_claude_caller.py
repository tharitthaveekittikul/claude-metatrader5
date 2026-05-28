# tests/test_claude_caller.py
import pytest
from unittest.mock import patch, MagicMock
from src.claude_caller import call_claude


def test_call_claude_returns_stdout():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "ORDER_TYPE: HOLD\nREASON: test"
    mock_result.stderr = ""

    with patch('src.claude_caller.subprocess.run', return_value=mock_result):
        with patch('src.claude_caller.shutil.which', return_value='/usr/bin/claude'):
            result = call_claude('test prompt', 'claude-sonnet-4-6', 60)

    assert result == "ORDER_TYPE: HOLD\nREASON: test"


def test_call_claude_passes_model_flag():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "response"
    mock_result.stderr = ""

    with patch('src.claude_caller.subprocess.run', return_value=mock_result) as mock_run:
        with patch('src.claude_caller.shutil.which', return_value='/usr/bin/claude'):
            call_claude('prompt', 'claude-sonnet-4-6', 60)

    call_args = mock_run.call_args[0][0]
    assert '--model' in call_args
    assert 'claude-sonnet-4-6' in call_args


def test_call_claude_raises_if_cli_not_found():
    with patch('src.claude_caller.shutil.which', return_value=None):
        with pytest.raises(RuntimeError, match='claude CLI not found'):
            call_claude('prompt', 'claude-sonnet-4-6', 60)


def test_call_claude_raises_on_nonzero_exit():
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "error message"

    with patch('src.claude_caller.subprocess.run', return_value=mock_result):
        with patch('src.claude_caller.shutil.which', return_value='/usr/bin/claude'):
            with pytest.raises(RuntimeError, match='claude CLI failed'):
                call_claude('prompt', 'claude-sonnet-4-6', 60)
