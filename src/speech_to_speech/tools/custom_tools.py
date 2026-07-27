from __future__ import annotations

import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CustomToolError(RuntimeError):
    """Raised when custom tool loading or execution fails safely."""


@dataclass(frozen=True)
class CustomToolHandler:
    type: str
    entry: str
    runtime: str = "python"
    timeout_s: float | None = None


@dataclass(frozen=True)
class CustomTool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: CustomToolHandler
    enabled: bool = False
    strict: bool = False
    id: str | None = None

    def to_realtime_tool(self) -> dict[str, Any]:
        tool: dict[str, Any] = {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
        if self.strict:
            tool["strict"] = True
        return tool


def _normalize_parameters(value: Any) -> dict[str, Any]:
    params = dict(value) if isinstance(value, dict) else {}
    if params.get("type") != "object":
        params["type"] = "object"
    if not isinstance(params.get("properties"), dict):
        params["properties"] = {}
    params.setdefault("additionalProperties", False)
    return params


def _load_tool(raw: Any, index: int) -> CustomTool:
    if not isinstance(raw, dict):
        raise CustomToolError(f"Tool entry {index} must be an object.")
    name = str(raw.get("name") or "").strip()
    if not name:
        raise CustomToolError(f"Tool entry {index} is missing a name.")
    handler_raw = raw.get("handler")
    if not isinstance(handler_raw, dict):
        raise CustomToolError(f"Tool {name!r} is missing a handler object.")
    return CustomTool(
        id=str(raw["id"]).strip() if raw.get("id") else None,
        name=name,
        description=str(raw.get("description") or "User-provided local tool.").strip(),
        parameters=_normalize_parameters(raw.get("parameters")),
        strict=bool(raw.get("strict", False)),
        enabled=bool(raw.get("enabled", False)),
        handler=CustomToolHandler(
            type=str(handler_raw.get("type") or "script"),
            entry=str(handler_raw.get("entry") or "").strip(),
            runtime=str(handler_raw.get("runtime") or "python"),
            timeout_s=float(handler_raw["timeout_s"]) if handler_raw.get("timeout_s") is not None else None,
        ),
    )


class CustomToolRegistry:
    def __init__(
        self,
        *,
        root: Path,
        tools: list[CustomTool],
        default_timeout_s: float = 10.0,
        runner: Any = subprocess.run,
    ) -> None:
        self.root = root.resolve()
        self.default_timeout_s = default_timeout_s
        self.runner = runner
        self._tools = {tool.name: tool for tool in tools if tool.enabled}

    @classmethod
    def from_file(
        cls,
        file_path: str | Path,
        *,
        default_timeout_s: float = 10.0,
        runner: Any = subprocess.run,
    ) -> "CustomToolRegistry":
        path = Path(file_path).expanduser()
        root = path.parent.resolve()
        if not path.exists():
            logger.info("Custom tools file does not exist: %s", path)
            return cls(root=root, tools=[], default_timeout_s=default_timeout_s, runner=runner)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CustomToolError(f"Invalid custom tools JSON: {exc}") from exc
        if not isinstance(raw, list):
            raise CustomToolError("Custom tools file must contain a JSON array.")

        tools: list[CustomTool] = []
        for index, entry in enumerate(raw):
            tool = _load_tool(entry, index)
            if tool.enabled:
                cls._validate_tool(root, tool)
            tools.append(tool)
        return cls(root=root, tools=tools, default_timeout_s=default_timeout_s, runner=runner)

    @staticmethod
    def _validate_tool(root: Path, tool: CustomTool) -> None:
        if tool.handler.type != "script":
            raise CustomToolError(f"Tool {tool.name!r} uses unsupported handler type {tool.handler.type!r}.")
        if tool.handler.runtime != "python":
            raise CustomToolError(f"Tool {tool.name!r} uses unsupported runtime {tool.handler.runtime!r}.")
        entry = tool.handler.entry
        if not entry:
            raise CustomToolError(f"Tool {tool.name!r} is missing handler.entry.")
        if Path(entry).is_absolute():
            raise CustomToolError(f"Tool {tool.name!r} handler.entry must be relative.")
        resolved = (root / entry).resolve()
        if root not in resolved.parents and resolved != root:
            raise CustomToolError(f"Tool {tool.name!r} handler.entry must stay inside {root}.")
        if resolved.suffix != ".py":
            raise CustomToolError(f"Tool {tool.name!r} handler.entry must be a .py file.")
        if not resolved.exists():
            raise CustomToolError(f"Tool {tool.name!r} handler script does not exist: {entry}")

    @property
    def enabled_names(self) -> set[str]:
        return set(self._tools)

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def tool_specs(self) -> list[dict[str, Any]]:
        return [tool.to_realtime_tool() for tool in self._tools.values()]

    def execute(self, name: str, arguments_json: str) -> str:
        tool = self._tools.get(name)
        if tool is None:
            raise CustomToolError(f"Unknown custom tool: {name}")
        try:
            args = json.loads(arguments_json or "{}")
        except json.JSONDecodeError as exc:
            raise CustomToolError(f"Invalid JSON arguments for {name}: {exc}") from exc
        if not isinstance(args, dict):
            raise CustomToolError(f"Arguments for {name} must be a JSON object.")

        script = (self.root / tool.handler.entry).resolve()
        payload = json.dumps({"args": args, "tool": {"name": name}}, ensure_ascii=False)
        timeout = tool.handler.timeout_s if tool.handler.timeout_s is not None else self.default_timeout_s
        try:
            completed = self.runner(
                [sys.executable, str(script)],
                input=payload,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise CustomToolError(f"Tool {name} timed out after {timeout:.1f}s.") from exc

        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        if completed.returncode != 0:
            detail = stderr or stdout or f"exit code {completed.returncode}"
            raise CustomToolError(f"Tool {name} failed: {detail[:500]}")
        if not stdout:
            return json.dumps({"success": True}, ensure_ascii=False)
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            return stdout
        return json.dumps(parsed, ensure_ascii=False)


def merge_tool_specs(existing: Any, custom_specs: list[dict[str, Any]]) -> list[Any] | None:
    if not custom_specs and not existing:
        return None
    merged: list[Any] = []
    seen: set[str] = set()
    for tool in list(existing or []):
        name = _tool_name(tool)
        if name:
            seen.add(name)
        merged.append(tool)
    for spec in custom_specs:
        name = _tool_name(spec)
        if name and name in seen:
            continue
        merged.append(spec)
    return merged


def _tool_name(tool: Any) -> str | None:
    if isinstance(tool, dict):
        return tool.get("name") or (tool.get("function") or {}).get("name")
    return getattr(tool, "name", None)
