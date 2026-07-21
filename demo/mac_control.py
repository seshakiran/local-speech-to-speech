"""Strict, local-only macOS automation primitives for the demo server.

The language model never supplies AppleScript or shell source. It may only
select one of the actions below and provide validated data arguments.
"""

from __future__ import annotations

import platform
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import quote_plus, urlsplit, urlunsplit


class ControlError(RuntimeError):
    """A safe, user-facing machine-control failure."""


Runner = Callable[..., subprocess.CompletedProcess]


KEY_CODES = {
    "enter": 36,
    "return": 36,
    "tab": 48,
    "space": 49,
    "backspace": 51,
    "delete": 51,
    "escape": 53,
    "left": 123,
    "right": 124,
    "down": 125,
    "up": 126,
}
MODIFIERS = {
    "command": "command down",
    "control": "control down",
    "option": "option down",
    "shift": "shift down",
}
MAX_TEXT_LENGTH = 20_000
CONFIRM_ACTIONS = {"type_text", "replace_selected_text"}


@dataclass
class MacController:
    runner: Runner = subprocess.run

    @property
    def available(self) -> bool:
        return platform.system() == "Darwin"

    def execute(self, action: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self.available:
            raise ControlError("Machine control is available only on macOS.")
        handlers = {
            "get_active_app": self.get_active_app,
            "activate_app": self.activate_app,
            "type_text": self.type_text,
            "press_key": self.press_key,
            "get_selected_text": self.get_selected_text,
            "replace_selected_text": self.replace_selected_text,
            "open_url": self.open_url,
            "search_in_browser": self.search_in_browser,
        }
        handler = handlers.get(action)
        if handler is None:
            raise ControlError(f"Unsupported action: {action}")
        try:
            return handler(**arguments)
        except TypeError as exc:
            raise ControlError("Invalid arguments for that action.") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "macOS denied the action").strip()
            raise ControlError(detail[:300]) from exc

    def execute_user_action(self, action: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute an action, showing a native confirmation when consequential.

        The target application is captured before the dialog appears and
        reactivated afterward, so approving the action does not redirect typing
        into the browser or confirmation dialog.
        """
        needs_confirmation = action in CONFIRM_ACTIONS
        if action == "press_key":
            needs_confirmation = str(arguments.get("key", "")).lower() in {
                "enter", "return", "backspace", "delete"
            }
        if not needs_confirmation:
            return self.execute(action, arguments)

        target = self.get_active_app().get("activeApp", "")
        if not target:
            raise ControlError("Could not determine the target application.")
        detail = self._confirmation_detail(action, arguments)
        try:
            answer = self._osascript([
                "on run argv",
                'display dialog (item 1 of argv) with title "Local Speech-to-Speech" '
                'buttons {"Cancel", "Allow"} default button "Cancel" cancel button "Cancel"',
                "end run",
            ], f"Target: {target}\n\n{detail}")
        except subprocess.CalledProcessError as exc:
            raise ControlError("Action cancelled.") from exc
        if "Allow" not in answer:
            raise ControlError("Action cancelled.")
        self.activate_app(target)
        time.sleep(0.25)
        result = self.execute(action, arguments)
        result["targetApp"] = target
        return result

    def _confirmation_detail(self, action: str, arguments: dict[str, Any]) -> str:
        if action in {"type_text", "replace_selected_text"}:
            text = self._text(arguments.get("text"))
            preview = text if len(text) <= 500 else text[:497] + "…"
            verb = "Replace the selection with" if action == "replace_selected_text" else "Type"
            return f'{verb}:\n\n“{preview}”'
        key = str(arguments.get("key", "")).lower()
        return f"Press the {key} key?"

    def _osascript(self, lines: list[str], *args: str) -> str:
        command = ["osascript"]
        for line in lines:
            command.extend(["-e", line])
        command.extend(["--", *args])
        result = self.runner(command, check=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip()

    @staticmethod
    def _text(value: Any) -> str:
        if not isinstance(value, str) or not value:
            raise ControlError("Text cannot be empty.")
        if len(value) > MAX_TEXT_LENGTH:
            raise ControlError(f"Text is limited to {MAX_TEXT_LENGTH:,} characters.")
        return value

    def get_active_app(self) -> dict[str, Any]:
        output = self._osascript([
            'tell application "System Events"',
            'set frontApp to first application process whose frontmost is true',
            'return (name of frontApp) & "\t" & (bundle identifier of frontApp)',
            'end tell',
        ])
        name, _, bundle_id = output.partition("\t")
        return {"ok": True, "activeApp": name, "bundleId": bundle_id}

    def activate_app(self, app: str) -> dict[str, Any]:
        app = self._text(app).strip()
        if len(app) > 120 or any(ch in app for ch in "\r\n\0"):
            raise ControlError("Invalid application name.")
        self.runner(["open", "-a", app], check=True, capture_output=True, text=True, timeout=10)
        return {"ok": True, "message": f"Activated {app}."}

    @staticmethod
    def _url(value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ControlError("URL cannot be empty.")
        raw = value.strip()
        initial = urlsplit(raw)
        if initial.scheme and initial.scheme not in {"http", "https"}:
            raise ControlError("Only public-style HTTP and HTTPS URLs are allowed.")
        if not initial.scheme:
            raw = "https://" + raw
        if len(raw) > 2_048:
            raise ControlError("URL is too long.")
        parts = urlsplit(raw)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            raise ControlError("Only public-style HTTP and HTTPS URLs are allowed.")
        return urlunsplit(parts)

    def open_url(self, url: str, app: str | None = None) -> dict[str, Any]:
        """Open a URL through Launch Services, which gives browsers a real tab.

        This intentionally does not fake navigation by typing into whichever UI
        control happens to have focus.
        """
        url = self._url(url)
        command = ["open"]
        target = "the default browser"
        if app:
            app = self._text(app).strip()
            if len(app) > 120 or any(ch in app for ch in "\r\n\0"):
                raise ControlError("Invalid application name.")
            command.extend(["-a", app])
            target = app
        command.append(url)
        self.runner(command, check=True, capture_output=True, text=True, timeout=10)
        return {"ok": True, "message": f"Opened {url} in {target}.", "url": url, "app": target}

    def search_in_browser(self, query: str, app: str | None = None) -> dict[str, Any]:
        query = self._text(query).strip()
        if len(query) > 1_000:
            raise ControlError("Search query is too long.")
        result = self.open_url(f"https://www.google.com/search?q={quote_plus(query)}", app)
        result["message"] = f"Opened a browser search for: {query}"
        result["query"] = query
        return result

    def type_text(self, text: str) -> dict[str, Any]:
        text = self._text(text)
        self._osascript([
            "on run argv",
            'tell application "System Events" to keystroke (item 1 of argv)',
            "end run",
        ], text)
        return {"ok": True, "message": f"Typed {len(text)} characters."}

    def press_key(self, key: str, modifiers: list[str] | None = None) -> dict[str, Any]:
        key = str(key).lower().strip()
        if key not in KEY_CODES:
            raise ControlError(f"Key is not allowed: {key}")
        requested = [str(m).lower().strip() for m in (modifiers or [])]
        if len(requested) != len(set(requested)) or any(m not in MODIFIERS for m in requested):
            raise ControlError("One or more modifiers are not allowed.")
        using = ""
        if requested:
            using = " using {" + ", ".join(MODIFIERS[m] for m in requested) + "}"
        self._osascript([
            f'tell application "System Events" to key code {KEY_CODES[key]}{using}',
        ])
        return {"ok": True, "message": f"Pressed {key}."}

    def get_selected_text(self) -> dict[str, Any]:
        original = self.runner(["pbpaste"], check=True, capture_output=True).stdout
        try:
            # Clear text first so an application with no selection cannot leave
            # the previous clipboard value looking like newly copied content.
            self.runner(["pbcopy"], input=b"", check=True, capture_output=True)
            self._osascript(['tell application "System Events" to keystroke "c" using command down'])
            time.sleep(0.15)
            selected = self.runner(["pbpaste"], check=True, capture_output=True).stdout
        finally:
            self.runner(["pbcopy"], input=original, check=True, capture_output=True)
        text = selected.decode("utf-8", errors="replace")
        return {"ok": True, "text": text, "empty": not bool(text)}

    def replace_selected_text(self, text: str) -> dict[str, Any]:
        text = self._text(text)
        self.type_text(text)
        return {"ok": True, "message": f"Replaced the selection with {len(text)} characters."}


controller = MacController()
