import json
import subprocess

import pytest

from speech_to_speech.tools.custom_tools import CustomTool, CustomToolError, CustomToolHandler, CustomToolRegistry


def _tool(entry: str = "tools/demo.py", *, enabled: bool = True) -> CustomTool:
    return CustomTool(
        name="demo_tool",
        description="Demo tool.",
        parameters={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
        enabled=enabled,
        handler=CustomToolHandler(type="script", entry=entry, runtime="python"),
    )


def test_custom_tool_registry_loads_enabled_python_tools(tmp_path):
    script_dir = tmp_path / "tools"
    script_dir.mkdir()
    (script_dir / "demo.py").write_text("print('{\"ok\": true}')\n", encoding="utf-8")
    config = tmp_path / "custom-tools.json"
    config.write_text(
        json.dumps(
            [
                {
                    "name": "demo_tool",
                    "description": "Demo tool.",
                    "parameters": {"type": "object", "properties": {}},
                    "enabled": True,
                    "handler": {"type": "script", "entry": "tools/demo.py", "runtime": "python"},
                },
                {
                    "name": "disabled_tool",
                    "enabled": False,
                    "handler": {"type": "script", "entry": "missing.py", "runtime": "python"},
                },
            ]
        ),
        encoding="utf-8",
    )

    registry = CustomToolRegistry.from_file(config)

    assert registry.enabled_names == {"demo_tool"}
    assert registry.tool_specs()[0]["name"] == "demo_tool"


def test_custom_tool_registry_rejects_paths_outside_root(tmp_path):
    config = tmp_path / "custom-tools.json"
    config.write_text(
        json.dumps(
            [
                {
                    "name": "bad_tool",
                    "enabled": True,
                    "handler": {"type": "script", "entry": "../bad.py", "runtime": "python"},
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(CustomToolError, match="inside"):
        CustomToolRegistry.from_file(config)


def test_custom_tool_registry_executes_script_with_json_stdin(tmp_path):
    script = tmp_path / "demo.py"
    script.write_text(
        "import json, sys\n"
        "payload = json.loads(sys.stdin.read())\n"
        "print(json.dumps({'hello': payload['args']['name']}))\n",
        encoding="utf-8",
    )
    registry = CustomToolRegistry(root=tmp_path, tools=[_tool("demo.py")])

    output = registry.execute("demo_tool", '{"name": "Ada"}')

    assert json.loads(output) == {"hello": "Ada"}


def test_custom_tool_registry_surfaces_script_failure(tmp_path):
    script = tmp_path / "demo.py"
    script.write_text("import sys\nprint('nope', file=sys.stderr)\nsys.exit(2)\n", encoding="utf-8")
    registry = CustomToolRegistry(root=tmp_path, tools=[_tool("demo.py")])

    with pytest.raises(CustomToolError, match="failed"):
        registry.execute("demo_tool", "{}")


def test_custom_tool_registry_uses_runner_for_unit_tests(tmp_path):
    script = tmp_path / "demo.py"
    script.write_text("print('{}')\n", encoding="utf-8")
    calls = []

    def fake_runner(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}', stderr="")

    registry = CustomToolRegistry(root=tmp_path, tools=[_tool("demo.py")], runner=fake_runner)

    assert json.loads(registry.execute("demo_tool", "{}")) == {"ok": True}
    assert calls[0][1]["input"] == '{"args": {}, "tool": {"name": "demo_tool"}}'
