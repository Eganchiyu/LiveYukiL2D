from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ConversationMessage:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    source: str = "text"

    def as_llm_message(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}

    def as_dict(self) -> dict[str, Any]:
        return {"role": self.role, "content": self.content, "timestamp": self.timestamp, "source": self.source}


class RuntimeState:
    def __init__(self, history_path: Path, max_history: int = 40) -> None:
        self.history_path = history_path
        self.max_history = max_history
        self.messages: list[ConversationMessage] = []
        self.status = "idle"
        self.current_task_id: str | None = None
        self.current_task: asyncio.Task[Any] | None = None
        self.cancel_event = asyncio.Event()
        self.pipeline_lock = asyncio.Lock()
        self._history_lock = asyncio.Lock()
        self.load_history()

    def load_history(self) -> None:
        if not self.history_path.exists():
            return
        try:
            data = json.loads(self.history_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(data, list):
            return
        self.messages = [
            ConversationMessage(
                role=item.get("role", "user"),
                content=item.get("content", ""),
                timestamp=float(item.get("timestamp", time.time())),
                source=item.get("source", "text"),
            )
            for item in data[-self.max_history:]
            if isinstance(item, dict) and isinstance(item.get("content"), str)
        ]

    async def append(self, role: str, content: str, source: str = "text") -> None:
        self.messages.append(ConversationMessage(role, content, source=source))
        self.messages = self.messages[-self.max_history:]
        await self.save_history()

    async def save_history(self) -> None:
        async with self._history_lock:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.history_path.with_suffix(".tmp")
            payload = [message.as_dict() for message in self.messages]
            temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temp_path.replace(self.history_path)

    async def clear(self) -> None:
        self.messages.clear()
        await self.save_history()

    def new_task_id(self) -> str:
        return uuid.uuid4().hex

    def llm_messages(self, system_prompt: str) -> list[dict[str, str]]:
        return [{"role": "system", "content": system_prompt}] + [message.as_llm_message() for message in self.messages]
