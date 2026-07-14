from __future__ import annotations

import asyncio
import os
from typing import Any

import aiohttp


class LLMConfigurationError(RuntimeError):
    pass


class OpenAICompatibleProvider:
    def __init__(self, config: dict[str, Any]) -> None:
        llm = config.get("llm", {})
        self.base_url = str(llm.get("baseUrl", "")).rstrip("/")
        self.api_key = os.getenv("LIVEYUKI_LLM_API_KEY", str(llm.get("apiKey", "")))
        self.model = str(llm.get("model", ""))
        self.timeout = float(llm.get("timeoutSeconds", 60))
        self.system_prompt = str(llm.get("systemPrompt", "你是 Yuki，一个友善、简洁的桌面 Live2D 助手。请用中文回答。"))

    async def complete(self, messages: list[dict[str, str]], cancel_event: asyncio.Event) -> str:
        if not self.base_url or not self.model:
            raise LLMConfigurationError("尚未配置 LLM。请在 config.json 的 llm.baseUrl 和 llm.model 中配置 OpenAI 兼容接口。")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {"model": self.model, "messages": messages, "stream": False}
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{self.base_url}/chat/completions", json=payload, headers=headers) as response:
                if cancel_event.is_set():
                    raise asyncio.CancelledError
                data = await response.json(content_type=None)
                if response.status >= 400:
                    detail = data.get("error", data) if isinstance(data, dict) else data
                    raise RuntimeError(f"LLM 请求失败（{response.status}）：{detail}")
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("LLM 返回格式无效。") from exc
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("LLM 返回了空文本。")
        return text.strip()
