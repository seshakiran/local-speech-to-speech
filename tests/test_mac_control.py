import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


MODULE_PATH = Path(__file__).parents[1] / "demo" / "mac_control.py"
SPEC = importlib.util.spec_from_file_location("mac_control_test", MODULE_PATH)
mac_control = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = mac_control
SPEC.loader.exec_module(mac_control)


class FakeRunner:
    def __init__(self, stdout=""):
        self.calls = []
        self.stdout = stdout

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        output = self.stdout
        if not kwargs.get("text", False) and isinstance(output, str):
            output = output.encode()
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")


def controller(runner=None):
    value = mac_control.MacController(runner=runner or FakeRunner())
    with patch.object(mac_control.platform, "system", return_value="Darwin"):
        assert value.available
    return value


def run(value, action, arguments):
    with patch.object(mac_control.platform, "system", return_value="Darwin"):
        return value.execute(action, arguments)


def test_unknown_actions_are_rejected():
    with pytest.raises(mac_control.ControlError, match="Unsupported action"):
        run(controller(), "run_shell", {"command": "rm -rf /"})


def test_type_text_is_passed_as_an_argument_not_script_source():
    runner = FakeRunner()
    text = 'hello "world"; do shell script "unsafe"'
    result = run(controller(runner), "type_text", {"text": text})
    command = runner.calls[0][0]
    assert command[-1] == text
    assert text not in command[:-1]
    assert result["ok"] is True


def test_activate_app_uses_argument_vector():
    runner = FakeRunner()
    run(controller(runner), "activate_app", {"app": "Notes"})
    assert runner.calls[0][0] == ["open", "-a", "Notes"]


@pytest.mark.parametrize("key", ["enter", "tab", "escape", "left", "right", "up", "down"])
def test_allowed_keys(key):
    result = run(controller(), "press_key", {"key": key})
    assert result["ok"] is True


def test_unlisted_key_is_rejected():
    with pytest.raises(mac_control.ControlError, match="not allowed"):
        run(controller(), "press_key", {"key": "f12"})


def test_text_size_is_bounded():
    with pytest.raises(mac_control.ControlError, match="limited"):
        run(controller(), "type_text", {"text": "x" * (mac_control.MAX_TEXT_LENGTH + 1)})


def test_selection_capture_clears_then_restores_clipboard():
    runner = FakeRunner(stdout="previous clipboard")
    with patch.object(mac_control.time, "sleep"):
        run(controller(runner), "get_selected_text", {})
    commands = [call[0] for call in runner.calls]
    assert commands[0] == ["pbpaste"]
    assert commands[1] == ["pbcopy"]
    assert runner.calls[1][1]["input"] == b""
    assert commands[-1] == ["pbcopy"]
    assert runner.calls[-1][1]["input"] == b"previous clipboard"
