from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from .events import error_event, say_event, state_event
from .llm import OpenAICompatibleProvider
from .state import RuntimeState


class RuntimePipeline:
    def __init__(self, state: RuntimeState, provider: OpenAICompatibleProvider, emit: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        self.state = state
        self.provider = provider
        self.emit = emit

    async def submit(self, text: str) -> str:
        if self.state.current_task and not self.state.current_task.done():
            raise RuntimeError("Yuki 正在处理上一条消息，请稍候或先中断当前回复。")
        task_id = self.state.new_task_id()
        self.state.cancel_event = asyncio.Event()
        task = asyncio.create_task(self._run(task_id, text))
        self.state.current_task_id = task_id
        self.state.current_task = task
        return task_id

    async def cancel(self) -> bool:
        task = self.state.current_task
        if not task or task.done():
            return False
        self.state.cancel_event.set()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return True

    async def clear_history(self) -> None:
        await self.cancel()
        async with self.state.pipeline_lock:
            await self.state.clear()
            await self.emit(state_event("idle"))

    async def _run(self, task_id: str, text: str) -> None:
        async with self.state.pipeline_lock:
            try:
                await self.emit(state_event("thinking", task_id))
                await self.state.append("user", text)
                reply = await self.provider.complete(self.state.llm_messages(self.provider.system_prompt), self.state.cancel_event)
                if self.state.cancel_event.is_set():
                    raise asyncio.CancelledError
                await self.state.append("assistant", reply)
                await self.emit(state_event("speaking", task_id))
                await self.emit(say_event(reply))
                await self.emit(state_event("idle", task_id))
            except asyncio.CancelledError:
                await self.emit(state_event("idle", task_id))
            except Exception as exc:
                await self.emit(error_event(str(exc), task_id))
                await self.emit(state_event("idle", task_id))
            finally:
                self.state.current_task_id = None
                self.state.current_task = None
