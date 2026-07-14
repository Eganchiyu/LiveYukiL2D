from __future__ import annotations

from typing import Any


def state_event(state: str, task_id: str | None = None) -> dict[str, Any]:
    event: dict[str, Any] = {"type": "state", "state": state}
    if task_id:
        event["task_id"] = task_id
    return event


def say_event(text: str, expression: int | str | None = None) -> dict[str, Any]:
    event: dict[str, Any] = {"type": "say", "text": text}
    if expression is not None:
        event["expression"] = expression
    return event


def error_event(message: str, task_id: str | None = None) -> dict[str, Any]:
    event: dict[str, Any] = {"type": "error", "message": message}
    if task_id:
        event["task_id"] = task_id
    return event
